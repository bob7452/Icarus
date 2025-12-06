from option.save_option_snapshot import save_option_snap,DataNotUpdatedError
from option.ansys_skew import process_snapshot_analysis
from datetime import timedelta, datetime
from pandas_market_calendars import get_calendar
from pathlib import Path
import sys
import json
import traceback
import time
import yfinance as yf
from update_news import chat
from option_skew_plot import run_skew_plot

CACHE_FILE = Path("option_task_cache.json")
MAX_RETRIES = 12 
RETRY_INTERVAL = 300 #seconds


def is_holiday(date: datetime) -> bool:
    nyse = get_calendar('NYSE')
    valid_days = nyse.valid_days(start_date=date, end_date=date)
    return valid_days.empty

def load_cached_day():
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
            return datetime.strptime(data["expected_next_day"], "%Y-%m-%d %H:%M:%S")
    return None

def save_next_expected_day(trading_day: datetime):
    data = {
        "expected_next_day": trading_day.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

def delete_cache():
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()
        print("Deleted processed task cache")

def get_latest_trading_day(before: datetime) -> datetime:
    today = datetime.today().replace(hour=16,minute=0,second=0,microsecond=0)
    if today.weekday() == 0:
        return today - timedelta(days=3)
    else:
        return today - timedelta(days=1)
    
    
def get_spy_price_at(date_str: str) -> float:
    """
    取得指定日期 SPY 收盤價
    :param date_str: 格式為 'YYYY-MM-DD'
    :return: float 收盤價
    """
    date = datetime.strptime(date_str, "%Y-%m-%d")
    next_day = date + timedelta(days=1)

    ticker = yf.Ticker("SPY")
    df = ticker.history(start=date_str, end=next_day.strftime("%Y-%m-%d"))
    
    if df.empty:
        raise ValueError(f"No data found for {date_str}")

    return df['Close'].iloc[0]


if __name__ == "__main__":
    today_dt = datetime.today()
    cached_day = load_cached_day()

    if cached_day:
        process_day = cached_day
    else:
        process_day = get_latest_trading_day(today_dt)
	
    
    # Skip if the day to process is a holiday (safety check)
    if is_holiday(process_day):
        print(f"[{process_day}] is a holiday. Skipping.")
        sys.exit(1)

    # If today is a holiday, store the process day and exit
    if is_holiday(today_dt):
        print(f"[{today_dt}] is a holiday. Caching process_day for later.")
        save_next_expected_day(process_day)
        sys.exit(1)

    # Run the task
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"[Attempt {attempt}] Executing snapshot task...")
            save_option_snap(today=process_day)
            delete_cache()
            break
        except DataNotUpdatedError as e:
            print(f"Data not ready: {e}")
            if attempt < MAX_RETRIES:
                print(f"Will retry in {RETRY_INTERVAL} seconds...\n")
                time.sleep(RETRY_INTERVAL)
            else:
                print("Max retries reached. Giving up.")
                sys.exit(2)
        except Exception:
            print("Save Snapshot Task execution failed with unexpected error:")
            traceback.print_exc()
            sys.exit(1)

    try:
        process_snapshot_analysis(today=process_day,
                                symbol="SPY",
                                underlying_price=get_spy_price_at(process_day.strftime("%Y-%m-%d")))
        run_skew_plot()
        chat(contents=["!TodaySkew"])
    except Exception as e:
            print("Process Skew Task execution failed with unexpected error:")
            traceback.print_exc()
            sys.exit(1)
    
