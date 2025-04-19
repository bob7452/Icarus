from option.save_option_snapshot import save_option_snap
from datetime import timedelta, datetime
from pandas_market_calendars import get_calendar
from pathlib import Path
import sys
import json
import traceback

CACHE_FILE = Path("option_task_cache.json")

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
    nyse = get_calendar('NYSE')
    valid_days = nyse.valid_days(end_date=before, start_date=before - timedelta(days=10))
    if valid_days.empty:
        raise ValueError("No valid trading day found")
    return valid_days[-1].to_pydatetime().replace(hour=16, minute=0, second=0, microsecond=0)

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
    try:
        save_option_snap(today=process_day)
        delete_cache()
    except Exception:
        print("Task execution failed")
        traceback.print_exc()
        sys.exit(1)
