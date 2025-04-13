from option.save_option_snapshot import save_option_snap
from datetime import timedelta , datetime

if __name__ == "__main__":
    today_dt = datetime.today()
    today_str = today_dt.strftime("%Y-%m-%d")

    if today_dt.weekday() == 0:
        last_trade_day = today_dt - timedelta(days=3)
    else:
        last_trade_day = today_dt - timedelta(days=1)

    last_trade_day = last_trade_day.replace(hour=16, minute=0, second=0, microsecond=0)

    save_option_snap(today=last_trade_day)