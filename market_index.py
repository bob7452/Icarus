import os
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import numpy as np
from matplotlib.dates import MonthLocator, DateFormatter


def plot_ath_atl_data(df):
    # 轉換日期欄位
    df["start_date"] = pd.to_datetime(df["start_date"])

    # 繪製雙軸圖
    fig, ax1 = plt.subplots(figsize=(12, 6))

    color_ath = 'tab:blue'
    color_atl = 'tab:red'

    # 主軸: ath_count
    ax1.set_xlabel('Date')
    ax1.set_ylabel('ATH Count', color=color_ath)
    ax1.plot(df["start_date"], df["ath_count"], color=color_ath, label='ATH Count')
    ax1.tick_params(axis='y', labelcolor=color_ath)

    # 副軸: atl_count
    ax2 = ax1.twinx()
    ax2.set_ylabel('ATL Count', color=color_atl)
    ax2.plot(df["start_date"], df["atl_count"], color=color_atl, label='ATL Count')
    ax2.tick_params(axis='y', labelcolor=color_atl)

    # --- 新增：取得最新數據並繪製在左上角 ---
    # 1. 取得 Dataframe 最後一列（最新的資料）
    latest_row = df.iloc[-1]
    latest_date = latest_row["start_date"].strftime("%Y-%m-%d")
    latest_ath = latest_row["ath_count"]
    latest_atl = latest_row["atl_count"]

    # 2. 設定要顯示的文字格式
    text_str = f"Latest ({latest_date})\nATH: {latest_ath} | ATL: {latest_atl}"

    # 3. 將文字放置於左上角
    # x=0.02, y=0.95 代表圖表 X 軸 2%、Y 軸 95% 的相對位置
    ax1.text(0.02, 0.95, text_str, 
             transform=ax1.transAxes, 
             fontsize=12, 
             fontweight='bold',
             verticalalignment='top', 
             bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='gray', alpha=0.8))
    # ----------------------------------------

    plt.title('ATH vs ATL Count Over Time')
    plt.grid(True)
    
    # 建議保留 tight_layout 避免雙軸標籤被截斷
    plt.tight_layout()
    plt.savefig("ath_atl_data.png")

def plot_weekly_ath_atl_data(plot_days=252):
    print(f"\n{'='*30}")
    print(f"開始執行市場結構診斷 (SOP v5) - {datetime.date.today()}")
    print(f"{'='*30}")
    
    # --- 步驟 0: 資料載入與彙整 ---
    if os.path.exists("datasheet.csv"):
        print("[Log] 偵測到 datasheet.csv，正在進行日轉週彙整...")
        df = pd.read_csv("datasheet.csv")
        df["start_date"] = pd.to_datetime(df["start_date"])
        df['week_start_date'] = df['start_date'] - pd.to_timedelta(df['start_date'].dt.weekday, unit='D')
        
        weekly_df = df.groupby('week_start_date').agg({
            'ath_count': 'sum', 
            'atl_count': 'sum', 
            'start_date': 'count'
        }).rename(columns={'start_date': 'days_in_week'}).reset_index()
        
        weekly_df.to_csv("weekly_ath_atl.csv", encoding='utf-8-sig', index=False)
        print(f"[Log] 彙整完成，共 {len(weekly_df)} 週數據，已存至 weekly_ath_atl.csv")
    elif os.path.exists("weekly_ath_atl.csv"):
        print("[Log] datasheet.csv 不存在，由 weekly_ath_atl.csv 直接載入...")
        weekly_df = pd.read_csv("weekly_ath_atl.csv")
        weekly_df['week_start_date'] = pd.to_datetime(weekly_df['week_start_date'])
        if 'days_in_week' not in weekly_df.columns: weekly_df['days_in_week'] = 5
    else:
        print("[Error] 找不到任何資料源！請檢查檔案路徑。")
        return

    print("--- 執行 SOP v7.5：官方正式版 (平滑轉場) ---")
    
    # 1. 載入數據 (優先使用含價格的 mspi 檔案)
    file_path = "mspi_v4.5_optimized_result.csv"
    if not os.path.exists(file_path):
        print(f"錯誤：找不到數據文件 {file_path}")
        return
        
    df = pd.read_csv(file_path)
    df["start_date"] = pd.to_datetime(df["start_date"])
    df = df.sort_values("start_date").reset_index(drop=True)

    # 2. 核心指標與 3 日平滑 (v7.5 靈魂)
    df["net_breadth"] = df["ath_z"] - df["atl_z"]
    df["nb_smooth"] = df["net_breadth"].rolling(window=3, min_periods=1).mean()
    
    # 統計門檻 (延續 v7 統計回報邏輯)
    q_high = df["net_breadth"].quantile(0.90)
    q_low = df["net_breadth"].quantile(0.15)

    # 3. 狀態分類 (SOP v7.5)
    def classify_v7_5(row):
        nb = row["nb_smooth"]
        if nb > q_high: return 'Climax'
        if nb < q_low: return 'Panic'
        # 穩定多頭：氧氣正向且毒素低
        if row['ath_z'] > 0.2 and row['atl_z'] < 0: return 'Bullish'
        # 結構受損：毒素顯著增加
        if row['atl_z'] > 0.6: return 'Slumping'
        return 'Neutral'

    df["structure"] = df.apply(classify_v7_5, axis=1)

    # 4. 儀表板視覺化 (三層看板)
    plot_df = df.tail(plot_days).copy()
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 18), gridspec_kw={'height_ratios': [3, 1.2, 1.2]})
    
    colors = {
        'Panic': '#4B0082',    # 深紫
        'Climax': '#FFD700',   # 金色
        'Bullish': '#228B22',  # 森林綠
        'Slumping': '#DC143C', # 緋紅
        'Neutral': '#D3D3D3'   # 淺灰
    }

    # 上圖：價格與絲滑轉場背景
    dates = plot_df["start_date"].values
    
    # 修改點：迴圈跑好跑滿 len(plot_df)，不再 -1
    for i in range(len(plot_df)):
        start_d = dates[i]
        
        # 修改點：如果是最後一天，色塊的終點往右推遲 1 天
        if i < len(plot_df) - 1:
            end_d = dates[i+1]
        else:
            end_d = dates[i] + np.timedelta64(1, 'D') 
            
        ax1.axvspan(start_d, end_d, color=colors[plot_df.iloc[i]['structure']], alpha=0.3)

    #ax1.plot(plot_df["start_date"], plot_df["spy_close"], color='black', lw=2.5, label="SPY Price")
    ax1.set_title(f"Market Structure Diagnostic SOP v7.5 (Official Refined Edition)", fontsize=22, fontweight='bold', pad=20)
    ax1.legend(loc="upper left", fontsize=12)
    for i in range(len(plot_df)-1):
        ax1.axvspan(dates[i], dates[i+1], color=colors[plot_df.iloc[i]['structure']], alpha=0.3)
    ax1.plot(plot_df["start_date"], plot_df["spy_close"], color='black', lw=2.5, label="SPY Price")
    ax1.set_title(f"Market Structure Diagnostic SOP v7.5 (Official Refined Edition)", fontsize=22, fontweight='bold', pad=20)
    ax1.legend(loc="upper left", fontsize=12)

    # 中圖：淨廣度強度 (3D Smoothed)
    ax2.fill_between(plot_df["start_date"], 0, plot_df["nb_smooth"], color='blue', alpha=0.3, label="Smoothed Net Breadth")
    ax2.axhline(q_high, color='orange', ls='--', lw=1.5, label=f"Overheat ({q_high:.2f})")
    ax2.axhline(q_low, color='purple', ls='--', lw=1.5, label=f"Opportunity ({q_low:.2f})")
    ax2.set_ylabel("Net Strength", fontsize=14)
    ax2.legend(loc="upper left", ncol=3)

    # 下圖：氧氣 (ATH) vs 毒素 (ATL) 能量分布
    ax3.fill_between(plot_df["start_date"], 0, plot_df["ath_z"], color='green', alpha=0.3, label="Oxygen (ATH Strength)")
    ax3.fill_between(plot_df["start_date"], 0, -plot_df["atl_z"], color='red', alpha=0.3, label="Toxin (ATL Strength)")
    ax3.axhline(0, color='black', lw=1, alpha=0.5)
    ax3.set_ylabel("Z-Score Energy", fontsize=14)
    ax3.legend(loc="upper left", ncol=2)

    # 格式化
    for ax in [ax1, ax2, ax3]:
        ax.xaxis.set_major_locator(MonthLocator(interval=1))
        ax.xaxis.set_major_formatter(DateFormatter("%Y-%m"))
        ax.grid(axis='y', linestyle=':', alpha=0.5)

    # 狀態看板
    latest = plot_df.iloc[-1]
    status_text = (f"LATEST STATUS: {latest['structure']}\n"
                   f"DATE: {latest['start_date'].date()}\n"
                   f"ATH_Z: {latest['ath_z']:.2f} | ATL_Z: {latest['atl_z']:.2f}\n"
                   f"Net Strength: {latest['nb_smooth']:.2f}")
    ax1.text(0.02, 0.70, status_text, transform=ax1.transAxes, fontsize=14, fontweight='bold', 
             bbox=dict(facecolor='white', alpha=0.9, edgecolor='black', boxstyle='round,pad=0.5'))

    plt.tight_layout()
    plt.savefig("weekly_ath_atl_data_last_52_weeks.png", dpi=120)
    
    # 保存數據
    df.to_csv("sop_v7_5_final_data.csv", index=False)
    print("診斷完成！官方正式版報告已生成。")
    


if __name__ == "__main__":
    df = pd.read_csv("datasheet.csv")
    df_252day = df.tail(252)
    plot_ath_atl_data(df_252day)
    plot_weekly_ath_atl_data(252)

