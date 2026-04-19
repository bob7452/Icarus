# 假設已存在的自定義模組
from stock_rules import rs_above_90
from file_io import read_stock_info_json

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

def get_stock_analysis_df():
    # --- 1. 自動日期區間計算 (考慮連假與週末) ---
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    
    # 抓取範圍：從本週一往前推 10 天，確保含括上週最後交易日
    yf_start_capture = (monday - timedelta(days=10)).strftime('%Y-%m-%d')
    yf_end_capture = (friday + timedelta(days=1)).strftime('%Y-%m-%d')
    this_week_start_str = monday.strftime('%Y-%m-%d')

    print(f"📅 報告生成日期: {today.strftime('%Y-%m-%d %H:%M')}")
    print(f"📊 分析週區間: {this_week_start_str} ~ {friday.strftime('%Y-%m-%d')}\n")

    # --- 2. 獲取股票清單 (請確保你的環境已有這些函數) ---
    try:
        stocks = rs_above_90()['name'].to_list()
        info = read_stock_info_json()
    except Exception as e:
        print(f"❌ 讀取配置失敗: {e}")
        return None, None

    # --- 3. 抓取數據 ---
    data_raw = yf.download(stocks, start=yf_start_capture, end=yf_end_capture, auto_adjust=True, group_by='ticker')

    stock_results = []

    for s in stocks:
        try:
            df = data_raw[s].dropna()
            if df.empty: continue

            # 定義本週資料與基準日
            this_week_df = df.loc[this_week_start_str:]
            if len(this_week_df) < 1: continue

            # 找到上一個有效交易日的收盤價
            first_day_idx = df.index.get_loc(this_week_df.index[0])
            prev_close = df.iloc[first_day_idx - 1]['Close'] if first_day_idx > 0 else this_week_df.iloc[0]['Open']

            # 本週數據
            curr_open = this_week_df.iloc[0]['Open']
            curr_close = this_week_df.iloc[-1]['Close']
            hi = this_week_df['High'].max()
            lo = this_week_df['Low'].min()

            # 指標計算
            body_move = curr_close - curr_open
            total_range = hi - lo
            er = body_move / total_range if total_range > 0 else 0
            weekly_return = (curr_close - prev_close) / prev_close

            # 僅保留「大陽線」邏輯：實體為正且總漲幅為正
            if body_move > 0 and weekly_return > 0:
                stock_results.append({
                    'Stock': s,
                    'Industry': info.get(s, {}).get("industry", "Unknown"),
                    'Weekly_Return_%': round(weekly_return * 100, 2),
                    'K_Efficiency': round(er, 3),
                    'Strength_Score': round(weekly_return * er * 100, 4)
                })
        except:
            continue

    # --- 4. 建立個股明細 DataFrame ---
    df_stocks = pd.DataFrame(stock_results)
    if df_stocks.empty:
        print("⚠️ 本週無符合大陽線條件之股票。")
        return None, None
    
    df_stocks = df_stocks.sort_values(by='Strength_Score', ascending=False).reset_index(drop=True)

    # --- 5. 建立產業匯總 DataFrame ---
    # 計算各產業的平均分、股票數量，並彙整領頭羊
    df_industry = df_stocks.groupby('Industry').agg(
        Avg_Score=('Strength_Score', 'mean'),
        Stock_Count=('Stock', 'count'),
        Top_Stocks=('Stock', lambda x: ", ".join(list(x)[:3])) # 取評分前三名
    ).sort_values(by='Avg_Score', ascending=False).reset_index()

    return df_stocks, df_industry

# --- 執行並顯示結果 ---
df_individual, df_sector = get_stock_analysis_df()

if df_sector is not None:
    print("=== 產業強度排行榜 ===")
    print(df_sector) # 如果在 Jupyter/Colab 中，請用 display()，否則用 print()
    
    print("\n=== 個股強勢大陽線明細 (Top 15) ===")
    print(df_individual.head(15))