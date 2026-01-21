import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from sklearn.preprocessing import MinMaxScaler

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

    plt.title('ATH vs ATL Count Over Time')
    plt.grid(True)
    # plt.tight_layout()
    # plt.show()
    plt.savefig("ath_atl_data.png")

def plot_weekly_ath_atl_data():
    
    # --- 步驟 0: 資料載入與彙整 ---
    if os.path.exists("datasheet.csv"):
        print("正在載入日資料並彙整為週資料...")
        df = pd.read_csv("datasheet.csv")
        df["start_date"] = pd.to_datetime(df["start_date"])
        # 計算週起始日 (週一)
        df['week_start_date'] = df['start_date'] - pd.to_timedelta(df['start_date'].dt.weekday, unit='D')
        # 彙整並記錄當週天數 (用於鎖定邏輯)
        weekly_df = df.groupby('week_start_date').agg({
            'ath_count': 'sum', 
            'atl_count': 'sum', 
            'start_date': 'count'
        }).rename(columns={'start_date': 'days_in_week'}).reset_index()
        
        # 存檔供後續快速使用
        weekly_df.tail(52).to_csv("weekly_ath_atl.csv", encoding='utf-8-sig', index=False)
    elif os.path.exists("weekly_ath_atl.csv"):
        print("由 weekly_ath_atl.csv 直接載入週資料...")
        weekly_df = pd.read_csv("weekly_ath_atl.csv")
        weekly_df['week_start_date'] = pd.to_datetime(weekly_df['week_start_date'])
        if 'days_in_week' not in weekly_df.columns: weekly_df['days_in_week'] = 5
    else:
        print("錯誤：找不到資料源 (datasheet.csv 或 weekly_ath_atl.csv)")
        return

    # --- 步驟 1: 指標與動態門檻計算 (基於最後 52 週) ---
    weekly_df = weekly_df.sort_values('week_start_date')
    weekly_df['diff'] = weekly_df['ath_count'] - weekly_df['atl_count']
    weekly_df['ath_slope'] = weekly_df['ath_count'].diff()
    
    recent_52w = weekly_df.tail(52).copy()
    diff_q95 = recent_52w['diff'].quantile(0.95)   # 過熱星星門檻
    atl_q95  = recent_52w['atl_count'].quantile(0.95) # 恐慌門檻
    ath_median = recent_52w['ath_count'].median()
    atl_median = recent_52w['atl_count'].median()

    # 恐慌標記 (回溯 4 週)
    weekly_df['panic_trigger'] = weekly_df['atl_count'] > atl_q95
    weekly_df['recent_panic'] = weekly_df['panic_trigger'].rolling(window=4, min_periods=1).max().astype(bool)

    # --- 步驟 2: 市場結構定義 (SOP v4 優先級) ---
    def get_structure(row):
        ath, atl, diff_v, slope = row['ath_count'], row['atl_count'], row['diff'], row['ath_slope']
        if row['recent_panic'] and slope > 0: return 'Hunting'  # 🎯 狩獵
        if atl > atl_q95: return 'Panic'                       # 🟣 恐慌
        if diff_v > diff_q95: return 'Climax'                  # 🟡 過熱
        if ath > ath_median and atl < atl_median: return 'Bullish' # 🟢 強勢
        if ath > ath_median: return 'Neutral'                  # ⚪ 整理
        return 'Slumping'                                      # 🔴 陰跌

    weekly_df['structure'] = weekly_df.apply(get_structure, axis=1)

    # ⭐ 鎖定邏輯：未完週 (不足 5 天) 沿用前一週天氣
    if len(weekly_df) > 1 and weekly_df.iloc[-1]['days_in_week'] < 5:
        weekly_df.loc[weekly_df.index[-1], 'structure'] = weekly_df.iloc[-2]['structure']

    # --- 步驟 3: 繪製診斷圖表 ---
    plot_df = weekly_df.tail(52).copy()
    fig, ax1 = plt.subplots(figsize=(16, 9))
    color_map = {'Hunting':'#BA55D3', 'Panic':'#4B0082', 'Climax':'#FFD700', 'Bullish':'#90EE90', 'Neutral':'#D3D3D3', 'Slumping':'#FFB6C1'}

    # 背景繪製
    for i in range(len(plot_df)):
        start = plot_df.iloc[i]['week_start_date']
        end = start + pd.Timedelta(days=7)
        ax1.axvspan(start, end, color=color_map[plot_df.iloc[i]['structure']], alpha=0.3)

    # 曲線繪製
    ax1.plot(plot_df['week_start_date'], plot_df['ath_count'], color='blue', label='ATH (Oxygen)', marker='o', markersize=3)
    ax2 = ax1.twinx()
    ax2.plot(plot_df['week_start_date'], plot_df['atl_count'], color='red', label='ATL (Toxin)', marker='x', ls='--')

    # 標記訊號 (星星、箭頭)
    climax = plot_df[plot_df['structure'] == 'Climax']
    panic = plot_df[plot_df['structure'] == 'Panic']
    hunting = plot_df[plot_df['structure'] == 'Hunting']
    if not climax.empty: ax1.scatter(climax['week_start_date'], climax['ath_count']+100, marker='*', c='gold', s=200, edgecolors='black')
    if not panic.empty: ax2.scatter(panic['week_start_date'], panic['atl_count']+50, marker='v', c='indigo', s=100)
    if not hunting.empty: ax1.scatter(hunting['week_start_date'], hunting['ath_count']-50, marker='^', c='darkorchid', s=120)

    # 狀態看板
    latest = plot_df.iloc[-1]
    status_text = f"LATEST: {latest['structure']}\nATH: {int(latest['ath_count'])} | ATL: {int(latest['atl_count'])}\nDiff Q95: {int(diff_q95)}"
    plt.text(0.02, 0.96, status_text, transform=ax1.transAxes, fontsize=11, fontweight='bold', bbox=dict(facecolor='white', alpha=0.9))

    plt.title('Market Structure Diagnostic SOP v4 (Final Integration)', fontsize=16)
    plt.gcf().autofmt_xdate()
    
    # 圖例
    patches = [mpatches.Patch(color=color_map[k], alpha=0.3, label=k) for k in color_map]
    ax1.legend(handles=ax1.get_legend_handles_labels()[0] + ax2.get_legend_handles_labels()[0] + patches, loc='upper right', ncol=2, fontsize=8)

    plt.tight_layout()
    plt.savefig("weekly_ath_atl_data_last_52_weeks.png")
    print(f"\n報告已生成。最新狀態：{latest['structure']}，動態過熱門檻：{int(diff_q95)}")


if __name__ == "__main__":
    df = pd.read_csv("datasheet.csv")
    df_252day = df.tail(252)
    plot_ath_atl_data(df_252day)
    plot_weekly_ath_atl_data()

