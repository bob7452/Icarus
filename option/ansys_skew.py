import pandas as pd
import matplotlib.pyplot as plt
from .sql_lib import fetch_data_from_option_db , insert_skew_db
from datetime import datetime
from pathlib import Path
import seaborn as sns

import pandas as pd

def compute_skew_from_snapshot(
    df: pd.DataFrame,
    underlying_price: float,
    price_range_pct: float = 0.3
) -> pd.DataFrame:
    results = []

    # Limit strikes within ±30% of underlying
    lower_bound = underlying_price * (1 - price_range_pct)
    upper_bound = underlying_price * (1 + price_range_pct)

    df = df[df['dte'] <= 180].copy()
    df['strike'] = pd.to_numeric(df['strike'], errors='coerce')
    df = df.dropna(subset=['strike'])
    df = df[(df['strike'] >= lower_bound) & (df['strike'] <= upper_bound)]

    df_grouped = df.groupby('expiration')

    for expiration, group in df_grouped:
        puts = group[group['option_type'] == 'put'].copy()
        calls = group[group['option_type'] == 'call'].copy()

        def find_atm_put():
            candidates = puts[(puts['delta'] < -0.35) & (puts['delta'] > -0.65)].copy()
            if not candidates.empty:
                candidates['abs_diff'] = (candidates['strike'] - underlying_price).abs()
                candidates['delta_diff'] = (candidates['delta'] + 0.5).abs()
                return candidates.sort_values(['abs_diff', 'delta_diff']).head(1)
            return pd.DataFrame()

        def find_atm_call():
            candidates = calls[(calls['delta'] > 0.35) & (calls['delta'] < 0.65)].copy()
            if not candidates.empty:
                candidates['abs_diff'] = (candidates['strike'] - underlying_price).abs()
                candidates['delta_diff'] = (candidates['delta'] - 0.5).abs()
                return candidates.sort_values(['abs_diff', 'delta_diff']).head(1)
            return pd.DataFrame()

        def find_put_by_delta(target_delta: float, delta_range: tuple = (-0.20, -0.05)):
            candidates = puts[(puts['delta'] >= delta_range[0]) & (puts['delta'] <= delta_range[1])].copy()
            if not candidates.empty:
                candidates['delta_diff'] = (candidates['delta'] - target_delta).abs()
                candidates['abs_diff'] = (candidates['strike'] - underlying_price).abs()
                return candidates.sort_values(['delta_diff', 'abs_diff']).head(1)
            return pd.DataFrame()

        atm_put = find_atm_put()
        atm_call = find_atm_call()
        put10 = find_put_by_delta(-0.10)
        put25 = find_put_by_delta(-0.25,(-0.3,-0.2))

        print(f"\n🟡 {expiration}")
        print("ATM Put:", atm_put[['strike', 'delta', 'iv']].to_dict(orient='records'))
        print("Put10D :", put10[['strike', 'delta', 'iv']].to_dict(orient='records'))
        print("Put25D :", put25[['strike', 'delta', 'iv']].to_dict(orient='records'))

        row = {
            "expiration": expiration,
            "put_10delta_skew": float(put10['iv'].values[0] - atm_put['iv'].values[0]) if not put10.empty and not atm_put.empty else None,
            "put_25delta_skew": float(put25['iv'].values[0] - atm_put['iv'].values[0]) if not put25.empty and not atm_put.empty else None,
            "call_put_skew": float(atm_call['iv'].values[0] - atm_put['iv'].values[0]) if not atm_call.empty and not atm_put.empty else None
        }

        results.append(row)

    skew_df = pd.DataFrame(results).sort_values("expiration")
    return skew_df

def load_latest_skew_diff() -> pd.DataFrame:
    df = fetch_data_from_option_db("SELECT * FROM skew_snapshot")
    df['snapshot_date'] = pd.to_datetime(df['snapshot_date'])

    latest_dates = df['snapshot_date'].drop_duplicates().nlargest(2)
    if len(latest_dates) < 2:
        raise ValueError("Not enough data to compute diff")

    df_recent = df[df['snapshot_date'].isin(latest_dates)]
    df_recent = df_recent.sort_values(['expiration', 'snapshot_date'])

    valid_expirations = df_recent['expiration'].value_counts()
    valid_expirations = valid_expirations[valid_expirations >= 2].index
    df_recent = df_recent[df_recent['expiration'].isin(valid_expirations)]

    diff_df = df_recent.groupby('expiration').apply(lambda g: pd.Series({
        'put_10delta_skew_diff': g['put_10delta_skew'].iloc[-1] - g['put_10delta_skew'].iloc[-2],
        'put_25delta_skew_diff': g['put_25delta_skew'].iloc[-1] - g['put_25delta_skew'].iloc[-2],
        'call_put_skew_diff': g['call_put_skew'].iloc[-1] - g['call_put_skew'].iloc[-2],
        'latest_snapshot': g['snapshot_date'].iloc[-1]
    })).reset_index()

    return diff_df



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

def plot_skew_with_diff(today : datetime,skew_df: pd.DataFrame, skew_diff_df: pd.DataFrame):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    today_str = today.strftime('%Y-%m-%d %H:%M:%S')

    # 上圖：Skew 本體
    ax1.plot(skew_df['expiration'], skew_df['put_10delta_skew'], label='Put 10D Skew', marker='o')
    ax1.plot(skew_df['expiration'], skew_df['put_25delta_skew'], label='Put 25D Skew', marker='s')
    ax1.plot(skew_df['expiration'], skew_df['call_put_skew'], label='Call-Put Skew', marker='x')
    ax1.set_ylabel('Skew Level')
    ax1.set_title(f'Skew Structure ({today_str})')
    ax1.legend(loc='best')
    ax1.grid(True)

    # 下圖：Skew 差異
    ax2.plot(skew_diff_df['expiration'], skew_diff_df['put_10delta_skew_diff'], label='Put 10D ΔSkew', linestyle='--', marker='^', color='tab:blue')
    ax2.plot(skew_diff_df['expiration'], skew_diff_df['put_25delta_skew_diff'], label='Put 25D ΔSkew', linestyle='--', marker='v', color='tab:orange')
    ax2.plot(skew_diff_df['expiration'], skew_diff_df['call_put_skew_diff'], label='Call-Put ΔSkew', linestyle='--', marker='d', color='tab:green')
    ax2.set_ylabel('Skew Change')
    ax2.set_xlabel('Expiration Date')
    ax2.set_title(f'Skew Change (vs {skew_diff_df["latest_snapshot"].iloc[-1]})')
    ax2.legend(loc='best')
    ax2.grid(True)
    ax2.tick_params(axis='x', rotation=45)

    plt.tight_layout()
    file_path = Path(__file__).resolve().parents[1] / "option_skew_with_diff.png"
    plt.savefig(file_path)
    print(f"Saved skew comparison chart to: {file_path}")


def process_snapshot_analysis(today: datetime, symbol: str, underlying_price: float):
    print("calculate skew")
    skew_df = process_skew(today=today,symbol=symbol,underlying_price=underlying_price)

    print("calculate skew diff")
    skew_diff_df = load_latest_skew_diff()

    print("plot skew & skew diff")
    plot_skew_with_diff(today=today,skew_df=skew_df,skew_diff_df=skew_diff_df)

    

def process_skew(today: datetime, symbol: str, underlying_price: float) -> pd.DataFrame:
    query = f"""
    SELECT expiration, dte, strike, option_type, delta, iv
    FROM option_snapshot
    WHERE date = '{today.strftime('%Y-%m-%d %H:%M:%S')}'
    AND symbol = '{symbol}' AND iv IS NOT NULL AND delta IS NOT NULL
    """
    df = fetch_data_from_option_db(query=query)
    if df.empty:
        print(f"[{symbol}] No IV/Delta data to compute skew.")
        return

    skew_df = compute_skew_from_snapshot(df=df, underlying_price=underlying_price)
    print(skew_df)

    skew_df['snapshot_date'] = today.strftime('%Y-%m-%d %H:%M:%S')
    insert_skew_db(df=skew_df)
    return skew_df

if __name__ == "__main__":
    process_snapshot_analysis(datetime(2025,4,15,16,0,0),"SPY",537.61)
