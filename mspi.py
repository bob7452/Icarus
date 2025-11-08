import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
import statsmodels.api as sm

# ---------------------------
# Parameters (you can change)
# ---------------------------
INPUT_CSV = "datasheet.csv"
WINDOW_DAYS = 252       # recent window in days to analyze
ROLL_WINDOW = 5          # smoothing for ATH/ATL counts (applied after Z-score)
W_SEARCH = (0.01, 5.0, 0.05) # (start, end, step) grid for weight w (調整為更寬範圍，適應標準化後的指標)
EMA_SPAN = 7             # EMA span for MSPI smoothing used in regression/plot
FUTURE_DAYS = 5          # NEW: Prediction horizon for future returns (e.g., 5 days)
ATL_PEAK_Q = 0.95        # quantile for ATL peak event (based on raw daily counts)
ATH_OVERHEAT_Q = 0.95    # quantile for ATH overheat event (based on raw daily counts)
# ---------------------------

# Step 1: load datasheet
# 假設 datasheet.csv 包含 start_date, ath_count, atl_count 欄位
try:
    df = pd.read_csv(INPUT_CSV)
except FileNotFoundError:
    raise SystemExit(f"Error: {INPUT_CSV} not found. Please upload the data file.")

df["start_date"] = pd.to_datetime(df["start_date"])
df = df.sort_values("start_date").reset_index(drop=True)

# Step 2: time window
cutoff_date = df["start_date"].max() - pd.Timedelta(days=WINDOW_DAYS)
df = df[df["start_date"] >= cutoff_date].reset_index(drop=True)
if df.empty:
    raise SystemExit("No data in chosen time window. Increase WINDOW_DAYS or check datasheet.csv")

# Step 3: fetch SPY from yfinance and merge
start = df["start_date"].min() - pd.Timedelta(days=1)
end = df["start_date"].max() + pd.Timedelta(days=FUTURE_DAYS + 1) # Fetch enough data for future return calc
spy = yf.download("SPY", start=start, end=end, progress=False)

# --- 修正新版本 yfinance 結構 ---
if isinstance(spy.columns, pd.MultiIndex):
    spy.columns = [col[0] if isinstance(col, tuple) else col for col in spy.columns]

spy = spy.reset_index().rename(columns={"Date": "start_date", "Close": "spy_close"})
spy["spy_return"] = spy["spy_close"].pct_change()

# === 計算未來報酬率 (Future Return) ===
# 計算未來 N 日的報酬率，並向前移動 N 天，使其對應到當前日期
spy["future_return"] = spy["spy_close"].pct_change(periods=-FUTURE_DAYS).shift(-FUTURE_DAYS)

# === 合併到 MSPI DataFrame ===
df = pd.merge(df, spy[["start_date", "spy_close", "spy_return", "future_return"]], on="start_date", how="inner")
# 由於需要 future_return，因此最後 FUTURE_DAYS 筆數據會是 NaN，會在迴歸時自動刪除

# =======================================================
# Step 4 & 5 (修正): 先 Z-score 標準化，後平滑 (Standardize then Smooth)
# 目的：解決原始數值量級問題，使 Z-score 更穩定
# =======================================================

# Step 4-A: Z-score normalization on RAW counts (based on windowed data)
df["ath_z_raw"] = (df["ath_count"] - df["ath_count"].mean()) / (df["ath_count"].std() + 1e-12)
df["atl_z_raw"] = (df["atl_count"] - df["atl_count"].mean()) / (df["atl_count"].std() + 1e-12)

# Step 5-A: Smoothing the Z-scores (new definition of ath_z, atl_z)
df["ath_z"] = df["ath_z_raw"].rolling(window=ROLL_WINDOW, min_periods=1).mean()
df["atl_z"] = df["atl_z_raw"].rolling(window=ROLL_WINDOW, min_periods=1).mean()


# Step 6: event marking using raw daily counts (no smoothing) per your requirement
atl_threshold_raw = df["atl_count"].quantile(ATL_PEAK_Q)
ath_threshold_raw = df["ath_count"].quantile(ATH_OVERHEAT_Q)
df["atl_event"] = df["atl_count"] > atl_threshold_raw
df["ath_event"] = df["ath_count"] > ath_threshold_raw


# =======================================================
# Step 7 (修正): Grid search best weight w by maximizing POSITIVE correlation with FUTURE returns
# 目的：使 MSPI 具備領先預測未來市場的能力
# =======================================================
w_start, w_end, w_step = W_SEARCH
w_values = np.arange(w_start, w_end + 1e-9, w_step)
best_w = None
best_corr = -np.inf # 尋找最大的正相關
# 這裡使用 future_return 且避免 NaN
reg_data = df[["ath_z", "atl_z", "future_return"]].dropna()

if reg_data.empty:
    raise SystemExit("Data too short or missing future returns. Check WINDOW_DAYS and FUTURE_DAYS.")

for w in w_values:
    mspi_tmp = reg_data["ath_z"] - w * reg_data["atl_z"]
    corr = mspi_tmp.corr(reg_data["future_return"])
    if corr is None:
        continue
    # 這裡只找正相關性最大的 w
    if corr > best_corr:
        best_corr = corr
        best_w = float(w)

if best_w is None:
    raise SystemExit("Failed to find best weight. Check data or W_SEARCH range.")

print(f"Auto-calibrated weight w = {best_w:.2f}, max corr(MSPI, Future_{FUTURE_DAYS}d_return) = {best_corr:.3f}")

# Step 8: compute final MSPI and smooth with EMA for trend/regression
df["mspi_raw"] = df["ath_z"] - best_w * df["atl_z"]
# Keep a filled version for plotting (interpolate small gaps if any)
df["mspi_filled"] = df["mspi_raw"].interpolate(method="linear", limit_direction="both")
df["mspi_ema"] = df["mspi_filled"].ewm(span=EMA_SPAN, adjust=False).mean()

# =======================================================
# Step 9 (修正): 根據 MSPI (EMA) 的分佈百分位數來動態分類階段 (Phase)
# 目的：讓階段劃分更適應於當前的市場週期
# =======================================================
# 計算 MSPI EMA 在當前窗口內的分位數 (範例：10%, 40%, 60%, 90% 劃分)
mspi_q = df["mspi_ema"].quantile([0.10, 0.40, 0.60, 0.90])

def classify_phase_dynamic(val):
    if val < mspi_q[0.10]:
        return "Capitulation (Extreme Low)"
    elif mspi_q[0.10] <= val < mspi_q[0.40]:
        return "Contraction (Low)"
    elif mspi_q[0.40] <= val < mspi_q[0.60]:
        return "Neutral (Mid)"
    elif mspi_q[0.60] <= val < mspi_q[0.90]:
        return "Expansion (High)"
    else:
        return "Overheat (Extreme High)"
df["phase"] = df["mspi_ema"].apply(classify_phase_dynamic)

# Step 10: turning points (cross neutral line Q0.5) on EMA
neutral_q = df["mspi_ema"].quantile(0.5) # 使用中位數作為中軸線
df["turning_up"] = (df["mspi_ema"].shift(1) < neutral_q) & (df["mspi_ema"] >= neutral_q)
df["turning_down"] = (df["mspi_ema"].shift(1) > neutral_q) & (df["mspi_ema"] <= neutral_q)

# Step 11: prepare plot - MSPI (EMA) main line, background by phase, inline event markers

# **優化 1: 增加圖表尺寸 (更寬)**
plt.figure(figsize=(18, 8)) # 顯著增加寬度 (18)
ax = plt.gca()
ax.grid(axis='y', linestyle='--', alpha=0.5)

# **修正 1: EMA 線條改回紫色**
plt.plot(df["start_date"], df["mspi_ema"], color="purple", linewidth=2.5, label=f"MSPI (EMA{EMA_SPAN})")

# background by phase groups
phase_colors = {
    "Capitulation (Extreme Low)": "#E74C3C",  # Red
    "Contraction (Low)":          "#F39C12",  # Orange
    "Neutral (Mid)":              "#ECF0F1",  # Light Gray
    "Expansion (High)":           "#2ECC71",  # Green
    "Overheat (Extreme High)":    "#9B59B6"   # Purple
}
current_phase = None
start_date = None
for i, row in df.reset_index().iterrows():
    if current_phase is None or row["phase"] != current_phase:
        if current_phase is not None:
            end_date = df.iloc[i-1]["start_date"] if i > 0 else start_date
            plt.axvspan(start_date, end_date, facecolor=phase_colors.get(current_phase, "#f0f0f0"), alpha=0.15, zorder=0)

        current_phase = row["phase"]
        start_date = row["start_date"]
    
    if i == len(df)-1 and current_phase is not None:
        plt.axvspan(start_date, row["start_date"], facecolor=phase_colors.get(current_phase, "#f0f0f0"), alpha=0.15, zorder=0)


# inline event markers
plt.scatter(df.loc[df["atl_event"], "start_date"], df.loc[df["atl_event"], "mspi_ema"],
            color="blue", s=60, zorder=6, label="ATL Event (Raw > q95)")
# **修正 2: ATH Overheat 點改回橙色**
plt.scatter(df.loc[df["ath_event"], "start_date"], df.loc[df["ath_event"], "mspi_ema"],
            color="orange", s=60, zorder=6, label="ATH Event (Raw > q95)") 

# turning markers
plt.scatter(df.loc[df["turning_up"], "start_date"], df.loc[df["turning_up"], "mspi_ema"],
            color="green", s=90, marker="^", zorder=7, label=f"Turning Up (Cross > Q50)")
plt.scatter(df.loc[df["turning_down"], "start_date"], df.loc[df["turning_down"], "mspi_ema"],
            color="red", s=90, marker="v", zorder=7, label=f"Turning Down (Cross < Q50)")

plt.axhline(neutral_q, color="gray", linestyle="--", linewidth=1, label="Neutral Line (Q50)")

plt.title(f"MSPI v4.5 (Auto-calibrated w={best_w:.2f}) — Last {WINDOW_DAYS} days | Max Corr: {best_corr:.3f}", fontsize=16)
plt.xlabel("Date", fontsize=12)
plt.ylabel("MSPI (EMA) - Z-Score Based", fontsize=12)

# **優化 2: 調整圖例位置和欄數**
plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=4, frameon=False, fontsize=10)

# **優化 3: X 軸標籤設置為水平，並減少標籤數量**
from matplotlib.dates import YearLocator, MonthLocator, DateFormatter
# 減少主要刻度的數量，例如每年或每季
ax.xaxis.set_major_locator(MonthLocator(interval=4)) # 每 4 個月標記一次
ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
# **設定 rotation=0 (水平)**
plt.xticks(rotation=0, ha='center') 

# 調整佈局以容納下方的圖例和水平的 X 軸標籤
plt.tight_layout(rect=[0, 0.15, 1, 1]) 
plt.savefig("mspi.png")

# =======================================================
# Step 12 (修正): OLS regression (Future Return ~ MSPI_ema)
# 目的：驗證 MSPI 對未來市場的領先預測能力
# =======================================================
reg_df = df[["start_date","mspi_ema","future_return"]].dropna()
if len(reg_df) < 30:
    print("Warning: too few observations for reliable regression.")
X = sm.add_constant(reg_df["mspi_ema"])
y = reg_df["future_return"]
model = sm.OLS(y, X).fit()
print("\n" + "="*50)
print(f"OLS Regression: Future {FUTURE_DAYS}d Return ~ MSPI_ema")
print("="*50)
print(model.summary())

beta = model.params.get("mspi_ema", np.nan)
r2 = model.rsquared
print(f"\nRegression Summary: MSPI_ema | beta = {beta:.4f}, R^2 = {r2:.3f}")

# Step 13: residual plot
plt.figure(figsize=(9,4))
plt.scatter(reg_df["mspi_ema"], model.resid, alpha=0.6, s=18, color="gray")
plt.axhline(0, color="red", linestyle="--", linewidth=1)
plt.title(f"OLS Residuals: Future {FUTURE_DAYS}d Return ~ MSPI_ema")
plt.xlabel("MSPI_ema")
plt.ylabel("Residuals (Future Return)")
plt.tight_layout()
#plt.show()

# Step 14: save results
out_path = "mspi_v4.5_optimized_result.csv"
df.to_csv(out_path, index=False)
print(f"Saved optimized results to {out_path}")

# Optional: print simple stats summary
print(f"\nSummary stats (window {WINDOW_DAYS} days):")
print(df[["mspi_raw","mspi_ema","atl_count","ath_count", "future_return"]].describe().T)
