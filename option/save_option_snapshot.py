import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from .option_calculate import OptionInput, calculate_greeks, implied_volatility
from .sql_lib import insert_option_db, get_oi_snapshot_by_date, get_latest_available_date

class DataNotUpdatedError(Exception):
    """Raised when option data has not been updated on remote source."""
    pass

OPTION_LIST = ["SPY", "^VIX"]

def exdays(cur_date: datetime, exp_date: str):
    year, mom, day = map(int, exp_date.split("-"))
    exp = datetime(year, mom, day) + timedelta(hours=16)
    print(exp)
    return (exp - cur_date).days / 365.0

def fetch_option_snapshot(today: datetime) -> pd.DataFrame:
    option_snapshots = []

    for stock_name in OPTION_LIST:
        print(f"Fetching: {stock_name}")
        ticker = yf.Ticker(stock_name)
        options = ticker.options

        try:
            current_stock_price = ticker.history(period="1d")['Close'].iloc[0]
        except Exception as e:
            print(f"⚠️ Failed to fetch current price for {stock_name}: {e}")
            continue

        for exp_date in options:

            try:
                option_chain = ticker.option_chain(exp_date)
            except Exception:
                print(f"⚠️ Failed to fetch chain for {exp_date}, skipping.")
                continue

            for opt_type, chain in [("call", option_chain.calls), ("put", option_chain.puts)]:
                for _, row in chain.iterrows():
                    k = row['strike']
                    oi = row['openInterest']
                    volume = row['volume']
                    market_price = row['lastPrice']
                    t = exdays(today, exp_date)

                    if t is None:
                        continue

                    opt = OptionInput(
                        option_type=opt_type,
                        S=current_stock_price,
                        K=k,
                        T=t,
                        r=0.04,
                        market_price=market_price
                    )

                    iv = implied_volatility(opt)
                    if not iv:
                        continue

                    greek = calculate_greeks(opt, iv)

                    option_snapshots.append({
                        "symbol": stock_name,
                        "date": today,
                        "dte": round(t * 365),
                        "expiration": exp_date,
                        "strike": k,
                        "option_type": opt_type,
                        "iv": iv,
                        "delta": float(greek.Delta),
                        "gamma": float(greek.Gamma),
                        "theta": float(greek.Theta),
                        "vega": float(greek.Vega),
                        "rho": float(greek.Rho),
                        "oi": oi,
                        "volume": volume,
                        "last_price": market_price,
                    })

    return pd.DataFrame(option_snapshots)

def is_oi_updated(today_df: pd.DataFrame, yesterday_df: pd.DataFrame) -> bool:
    # If there's no previous data, treat as updated (first-time run)
    if yesterday_df.empty:
        return True

    # Merge today's data with yesterday's data on key option attributes
    merged = today_df.merge(
        yesterday_df,
        on=["symbol", "strike", "option_type", "expiration"],
        suffixes=('', '_y'),
        how="left"
    )

    # Check if any options exist in today's data but not in yesterday's (new contracts)
    if merged['oi_y'].isna().any():
        print("New option contracts detected (not present yesterday).")
        return True

    # If all contracts existed yesterday, check if any open interest (OI) has changed
    changed = (merged['oi'] != merged['oi_y']).any()
    if changed:
        print("OI values changed.")
    else:
        print("No OI changes detected. Data likely not updated yet.")

    return changed

def is_all_symbol_updated(today_df: pd.DataFrame, yesterday_df: pd.DataFrame) -> bool:
    symbols = today_df['symbol'].unique()
    for sym in symbols:
        today_sym_df = today_df[today_df['symbol'] == sym]
        yest_sym_df = yesterday_df[yesterday_df['symbol'] == sym]
        if not is_oi_updated(today_sym_df, yest_sym_df):
            print(f"Symbol {sym} has not updated yet.")
            return False
    return True


def save_option_snap(today: datetime):
    print("Starting option snapshot")

    df_today = fetch_option_snapshot(today)
    if df_today.empty:
        print("No data fetched, skipping.")
        return

    # Step 1: find the actual last recorded day in DB
    symbol_ref = "SPY"  # Pick one to query for last available date
    prev_date = get_latest_available_date(symbol_ref)

    if not prev_date:
        print(f"No previous data found in DB for {symbol_ref}, assuming first-time run.")
        write_flag = True
    else:
        df_yesterday = get_oi_snapshot_by_date(symbols=OPTION_LIST, date=prev_date)
        write_flag = is_all_symbol_updated(df_today, df_yesterday)

    if not write_flag:
        print(f"OI not updated for {today.date()} (vs DB date {prev_date.date()}). Skipping DB write.")
        raise DataNotUpdatedError("Some symbols not updated yet.")

    try:
        insert_option_db(df_today)
        print(f"Option snapshot for {today.date()} saved successfully.")
    except Exception as e:
        print(f"Failed to insert snapshot: {e}")
