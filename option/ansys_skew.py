import pandas as pd
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

    return pd.DataFrame(results).sort_values("expiration")



if __name__ == "__main__":
    today = "2025-04-11 16:00:00"
    symbol = "SPY"

    query = f"""
    SELECT expiration, dte, strike, option_type, delta, iv
    FROM option_snapshot
    WHERE date = '{today}' AND symbol = '{symbol}' AND iv IS NOT NULL AND delta IS NOT NULL
    """
    df = fetch_data_from_option_db(query=query)
    print(df)
    skew_df = compute_skew_from_snapshot(df=df,underlying_price=533.94)
    print(skew_df)