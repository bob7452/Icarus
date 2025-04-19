import pandas as pd
import matplotlib.pyplot as plt
from sql_lib import fetch_data_from_option_db

def compute_skew_from_snapshot(df: pd.DataFrame, underlying_price: float, price_range_pct: float = 0.1) -> pd.DataFrame:
    results = []

    # Strike 篩選上下限
    lower_bound = underlying_price * (1 - price_range_pct)
    upper_bound = underlying_price * (1 + price_range_pct)

    df = df[df['dte'] <= 180]
    df['strike'] = pd.to_numeric(df['strike'], errors='coerce')
    df = df.dropna(subset=['strike'])  # 清掉無效資料
    df = df[(df['strike'] >= lower_bound) & (df['strike'] <= upper_bound)]
    print(df)

    df_grouped = df.groupby('expiration')

    for expiration, group in df_grouped:
        puts = group[group['option_type'] == 'put']
        calls = group[group['option_type'] == 'call']

        if puts.empty or calls.empty:
            continue  # 避免出現空值問題

        # 找 ATM Put / Call（靠近 delta ±0.5）
        atm_put = puts.iloc[(puts['delta'] + 0.5).abs().argsort()[:1]]
        atm_call = calls.iloc[(calls['delta'] - 0.5).abs().argsort()[:1]]

        # 找 10 Delta Put（靠近 delta -0.1）
        put10 = puts.iloc[(puts['delta'] + 0.10).abs().argsort()[:1]]
        # 找 25 Delta Put（靠近 delta -0.25）
        put25 = puts.iloc[(puts['delta'] + 0.25).abs().argsort()[:1]]

        # --- DEBUG 印出資訊 ---
        print(f"\n🟡 {expiration}")
        print("ATM Put:", atm_put[['strike', 'delta', 'iv']].to_dict(orient='records'))
        print("Put10D :", put10[['strike', 'delta', 'iv']].to_dict(orient='records'))
        print("Put25D :", put25[['strike', 'delta', 'iv']].to_dict(orient='records'))

        row = {
            "expiration": expiration,
            "put_10delta_skew": float(put10['iv'].values[0] - atm_put['iv'].values[0]) if not put10.empty and not atm_put.empty else None,
            "put_25delta_skew": float(put25['iv'].values[0] - atm_put['iv'].values[0]) if not put25.empty and not atm_put.empty else None,
            "call_put_skew": float(atm_call['iv'].values[0] - atm_put['iv'].values[0]) if not atm_put.empty and not atm_call.empty else None
        }

        results.append(row)

    skew_df = pd.DataFrame(results).sort_values("expiration")
    
    # 計算與上一交易日的差異
    skew_df['put_10delta_skew_diff'] = skew_df['put_10delta_skew'].diff()
    skew_df['put_25delta_skew_diff'] = skew_df['put_25delta_skew'].diff()
    skew_df['call_put_skew_diff'] = skew_df['call_put_skew'].diff()

    return skew_df


def plot_skew_and_diff(skew_df: pd.DataFrame):
    # Create a figure with 2 subplots (one for today's skew, one for differences)
    fig, axs = plt.subplots(2, 1, figsize=(12, 12), sharex=True)  # Increased figsize for better spacing

    # Plot today's skew in the first subplot
    axs[0].plot(skew_df['expiration'], skew_df['put_10delta_skew'], label='Put 10 Delta Skew (Today)', marker='o', color='blue')
    axs[0].plot(skew_df['expiration'], skew_df['put_25delta_skew'], label='Put 25 Delta Skew (Today)', marker='s', color='green')
    axs[0].plot(skew_df['expiration'], skew_df['call_put_skew'], label='Call-Put Skew (Today)', marker='x', color='red')

    axs[0].set_ylabel('Skew')
    axs[0].set_title('Option Skew for Today')
    axs[0].legend(loc='best')
    axs[0].grid(True)

    # Plot the differences (diff from the previous day) in the second subplot
    axs[1].plot(skew_df['expiration'], skew_df['put_10delta_skew_diff'], label='Put 10 Delta Skew Diff', linestyle='--', color='blue')
    axs[1].plot(skew_df['expiration'], skew_df['put_25delta_skew_diff'], label='Put 25 Delta Skew Diff', linestyle='--', color='green')
    axs[1].plot(skew_df['expiration'], skew_df['call_put_skew_diff'], label='Call-Put Skew Diff', linestyle='--', color='red')

    axs[1].set_xlabel('Expiration Date')
    axs[1].set_ylabel('Difference')
    axs[1].set_title('Option Skew Difference from Previous Day')
    axs[1].legend(loc='best')
    axs[1].grid(True)

    # Adjust the layout with more spacing between the subplots
    plt.subplots_adjust(hspace=0.4)  # Adjust space between subplots

    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45, ha='right')


    from pathlib import Path
    file_path = Path(__file__).resolve().parents[1] / "option_skew.jpg"
    plt.savefig(file_path)
    
def find_oi_changes(today: str, symbol: str, volume_threshold: int = 1000, oi_change_threshold: float = 0.30, oi_decrease_threshold: float = -0.30) -> pd.DataFrame:
    # 查詢最新交易日和上一個交易日的 OI 和成交量數據
    query = f"""
    SELECT expiration, strike, option_type, oi, volume, date
    FROM option_snapshot
    WHERE date IN ('{today}', (SELECT MAX(date) FROM option_snapshot WHERE date < '{today}' AND symbol = '{symbol}')) 
    AND symbol = '{symbol}' AND oi IS NOT NULL AND volume IS NOT NULL
    """
    
    # 抓取今天和前一個交易日的數據
    df = fetch_data_from_option_db(query=query)
    
    # 確保日期是對的
    df['date'] = pd.to_datetime(df['date'])
    
    # 按日期分組，分成今天和上一交易日的數據
    df_today = df[df['date'] == today]
    df_previous = df[df['date'] != today]
    
    # 將今天的數據和上一交易日的數據合併，根據 expiration 和 strike 匹配
    df_merged = pd.merge(df_today, df_previous, on=['expiration', 'strike', 'option_type'], suffixes=('_today', '_previous'))
    
    # 計算 OI 變動百分比
    df_merged['oi_change_pct'] = (df_merged['oi_today'] - df_merged['oi_previous']) / df_merged['oi_previous']
    
    # 計算 OI 變動絕對數值（用於識別大量平倉）
    df_merged['oi_abs_change'] = df_merged['oi_today'] - df_merged['oi_previous']
    
    # 篩選出 OI 變動超過 30% 且成交量超過指定閾值的行
    df_oi_changes = df_merged[
        (df_merged['oi_change_pct'] >= oi_change_threshold) & 
        (df_merged['volume_today'] >= volume_threshold)
    ]
    
    # 篩選出 OI 顯著減少的行，代表大量平倉
    df_oi_decrease = df_merged[
        (df_merged['oi_change_pct'] <= oi_decrease_threshold) & 
        (df_merged['volume_today'] >= volume_threshold)
    ]
    
    # 合併兩個結果，將有 OI 變動的選擇權和大量平倉的選擇權結果都返回
    result_df = pd.concat([df_oi_changes, df_oi_decrease], axis=0).drop_duplicates()
    
    return result_df[['expiration', 'strike', 'option_type', 'oi_today', 'oi_previous', 'oi_change_pct', 'oi_abs_change', 'volume_today']]
    
def plot_skew(skew_df: pd.DataFrame):
    plt.figure(figsize=(10, 6))

    # Plot Skew for Put 10 Delta, Put 25 Delta, and Call-Put Skew
    plt.plot(skew_df['expiration'], skew_df['put_10delta_skew'], label='Put 10 Delta Skew', marker='o')
    plt.plot(skew_df['expiration'], skew_df['put_25delta_skew'], label='Put 25 Delta Skew', marker='s')
    plt.plot(skew_df['expiration'], skew_df['call_put_skew'], label='Call-Put Skew', marker='x')

    plt.xlabel('Expiration Date')
    plt.ylabel('Skew')
    plt.title('Option Skew Analysis Over Time')
    plt.legend(loc='best')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()

    # Show the plot
    from pathlib import Path
    file_path = Path(__file__).resolve().parents[1] / "option_skew.jpg"
    plt.savefig(file_path)

if __name__ == "__main__":
    today = "2025-04-16 16:00:00"
    symbol = "^VIX"

    query = f"""
    SELECT expiration, dte, strike, option_type, delta, iv
    FROM option_snapshot
    WHERE date = '{today}' AND symbol = '{symbol}' AND iv IS NOT NULL AND delta IS NOT NULL
    """
    df = fetch_data_from_option_db(query=query)
    print(df)
    skew_df = compute_skew_from_snapshot(df=df, underlying_price=30)
    print(skew_df)

    # 繪製當天的 Skew 和與前一交易日的差異圖（上下兩圖）
    plot_skew(skew_df)
    plot_skew_and_diff(skew_df)
    df= find_oi_changes(today=today,symbol=symbol)
    df.to_csv("123.csv",index=False)

