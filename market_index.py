import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from sklearn.preprocessing import MinMaxScaler
import datetime

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

def plot_weekly_ath_atl_data(weeks=52):
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

    # --- 步驟 1: 指標計算 ---
    weekly_df = weekly_df.sort_values('week_start_date')
    weekly_df['diff'] = weekly_df['ath_count'] - weekly_df['atl_count']
    weekly_df['ath_slope'] = weekly_df['ath_count'].diff()
    
    # [擴充] 計算多頭純度 (Purity)
    weekly_df['total_signals'] = weekly_df['ath_count'] + weekly_df['atl_count']
    weekly_df['purity'] = weekly_df['ath_count'] / weekly_df['total_signals']
    
    # 計算動態門檻 (基於最後 N 週)
    recent_stats = weekly_df.tail(weeks).copy()
    diff_q95 = recent_stats['diff'].quantile(0.95)
    atl_q95 = recent_stats['atl_count'].quantile(0.90)
    ath_median = recent_stats['ath_count'].median()
    atl_median = recent_stats['atl_count'].median()
    
    # [擴充] 固定歷史門檻
    ATL_DANGER_THRESHOLD = 260
    PURITY_GOOD_THRESHOLD = 0.8

    print(f"[Log] 動態門檻計算完成 ({weeks}週基準):")
    print(f"      - 過熱門檻 (Diff Q95): {diff_q95:.2f}")
    print(f"      - 恐慌門檻 (ATL Q95): {atl_q95:.2f}")
    print(f"      - 中位數 (ATH/ATL): {ath_median:.1f} / {atl_median:.1f}")

    # 恐慌標記 (回溯 4 週)
    weekly_df['panic_trigger'] = weekly_df['atl_count'] > atl_q95
    weekly_df['recent_panic'] = weekly_df['panic_trigger'].rolling(window=4, min_periods=1).max().astype(bool)

    # --- 步驟 2: 市場結構定義 (導入 V5 邏輯) ---
    structure_logs = []

    def get_structure(row):
        date_str = row['week_start_date'].strftime('%Y-%m-%d')
        ath, atl, diff_v, slope, purity = row['ath_count'], row['atl_count'], row['diff'], row['ath_slope'], row['purity']
        recent_panic = row['recent_panic']
        
        # 邏輯判定優先級
        if atl > atl_q95:
            res = 'Panic'
            reason = f"ATL({atl}) > 恐慌門檻({atl_q95:.1f})"
        elif recent_panic and slope > 0:
            res = 'Hunting'
            reason = f"近期有恐慌 且 ATH斜率({slope:.1f}) > 0"
        elif diff_v > diff_q95:
            res = 'Climax'
            reason = f"Diff({diff_v}) > 過熱門檻({diff_q95:.1f})"
        
        # [擴充] 健康多頭：需滿足 ATH 高於中位數 且 純度 >= 0.8
        elif ath > ath_median and atl < atl_median and purity >= PURITY_GOOD_THRESHOLD:
            res = 'Bullish'
            reason = f"ATH強勢({ath}) 且 純度高({purity:.2f} >= 0.8)"
        
        # [擴充] 結構受損：ATL 超過 260
        elif atl > ATL_DANGER_THRESHOLD:
            res = 'Slumping'
            reason = f"ATL危險({atl} > 260) 市場結構受損"
            
        elif ath > ath_median:
            res = 'Neutral'
            reason = f"僅 ATH({ath}) > 中位數({ath_median:.1f})，純度不足或 ATL 偏高"
        else:
            res = 'Slumping'
            reason = f"所有看多條件皆不滿足 (ATH:{ath}, ATL:{atl})"
        
        structure_logs.append({
            'date': date_str, 'res': res, 'reason': reason,
            'ath': ath, 'atl': atl, 'purity': purity
        })
        return res

    # 執行計算
    weekly_df['structure'] = weekly_df.apply(get_structure, axis=1)

    # 打印診斷 Log
    print(f"\n[Diagnostic Log] 最近 {weeks} 週結構判斷明細:")
    print(f"{'週起始日期':<12} | {'判斷結果':<10} | {'判定原因'}")
    print("-" * 80)
    for log in structure_logs[-weeks:]:
        print(f"{log['date']:<12} | {log['res']:<10} | {log['reason']}")

    # ⭐ 鎖定邏輯
    if len(weekly_df) > 1:
        last_idx = weekly_df.index[-1]
        prev_idx = weekly_df.index[-2]
        latest_week_start = weekly_df.loc[last_idx, 'week_start_date']
        this_friday = latest_week_start + pd.Timedelta(days=4)
        if pd.Timestamp(datetime.date.today()) <= this_friday:
            weekly_df.loc[last_idx, 'structure'] = weekly_df.loc[prev_idx, 'structure']
            print(f"\n[Log] 本週尚未結束，將狀態鎖定為前週之 {weekly_df.loc[prev_idx, 'structure']}")

    # --- 步驟 3: 繪製診斷圖表 (V5 雙圖版) ---
    plot_df = weekly_df.tail(weeks).copy()
    fig, (ax1, ax3) = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [3, 1]})
    color_map = {'Hunting':'#BA55D3', 'Panic':'#4B0082', 'Climax':'#FFD700', 'Bullish':'#90EE90', 'Neutral':'#D3D3D3', 'Slumping':'#FFB6C1'}

    # 上圖背景與曲線
    for i in range(len(plot_df)):
        start = plot_df.iloc[i]['week_start_date']
        ax1.axvspan(start, start + pd.Timedelta(days=7), color=color_map[plot_df.iloc[i]['structure']], alpha=0.3)

    ax1.plot(plot_df['week_start_date'], plot_df['ath_count'], color='blue', label='ATH (Oxygen)', marker='o', markersize=3)
    ax2 = ax1.twinx()
    ax2.plot(plot_df['week_start_date'], plot_df['atl_count'], color='red', label='ATL (Toxin)', marker='x', ls='--')
    ax2.axhline(ATL_DANGER_THRESHOLD, color='darkred', linestyle=':', alpha=0.6, label=f'ATL Danger ({ATL_DANGER_THRESHOLD})')

    # [擴充] 下圖：多頭純度
    ax3.plot(plot_df['week_start_date'], plot_df['purity'], color='green', label='Bullish Purity', linewidth=2)
    ax3.axhline(0.8, color='darkgreen', linestyle='--', alpha=0.6, label='Bull 0.8')
    ax3.axhline(0.5, color='orange', linestyle='--', alpha=0.6, label='Neutral 0.5')
    ax3.fill_between(plot_df['week_start_date'], 0.8, 1.0, color='green', alpha=0.1)
    ax3.set_ylim(0, 1.05)
    ax3.set_ylabel("Purity Ratio")
    ax3.legend(loc='lower left')

    # 標記訊號
    for s, marker, c, ax_ref, offset in [('Climax', '*', 'gold', ax1, 100), ('Panic', 'v', 'indigo', ax2, 50), ('Hunting', '^', 'darkorchid', ax1, -50)]:
        pts = plot_df[plot_df['structure'] == s]
        if not pts.empty:
            y_val = pts['ath_count'] if ax_ref == ax1 else pts['atl_count']
            ax_ref.scatter(pts['week_start_date'], y_val + offset, marker=marker, c=c, s=150, edgecolors='black' if s=='Climax' else None)

    # 修改後的狀態看板代碼片段
    latest = plot_df.iloc[-1]
    status_text = (
        f"LATEST: {latest['structure']}\n"
        f"Purity: {latest['purity']:.1%}\n"
        f"ATH: {int(latest['ath_count'])}\n"
        f"ATL: {int(latest['atl_count'])}"
    )
    ax1.text(0.02, 0.96, status_text, transform=ax1.transAxes, fontsize=11, fontweight='bold', bbox=dict(facecolor='white', alpha=0.9))
    ax1.set_title(f'Market Structure Diagnostic SOP v5 (Integrated Purity & ATL Danger)', fontsize=16)
    fig.autofmt_xdate()
    
    patches = [mpatches.Patch(color=color_map[k], alpha=0.3, label=k) for k in color_map]
    ax1.legend(handles=ax1.get_legend_handles_labels()[0] + ax2.get_legend_handles_labels()[0] + patches, loc='upper right', ncol=2, fontsize=8)

    plt.tight_layout()
    plt.savefig("weekly_ath_atl_data_last_52_weeks.png")
    
    print(f"\n[Summary] 診斷完成，狀態：{latest['structure']}，純度：{latest['purity']:.1%}")
    return latest

if __name__ == "__main__":
    df = pd.read_csv("datasheet.csv")
    df_252day = df.tail(252)
    plot_ath_atl_data(df_252day)
    plot_weekly_ath_atl_data(52)

