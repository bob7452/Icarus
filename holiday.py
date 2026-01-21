import sys
from datetime import datetime , timedelta
from pandas_market_calendars import get_calendar


def isholidays(start_date):

    nyse = get_calendar('NYSE')
    
    is_holidays = nyse.valid_days(start_date=start_date, end_date=start_date)

    if is_holidays.empty:
        print('plz enjoy ur holidays')
        return 1
    else:
        print('Fighting')
        return 0

if __name__ == "__main__":

    yy,mm,dd  = map(int,(datetime.today()-timedelta(days=1)).strftime("%Y-%m-%d").split('-'))
    START = datetime(year=yy, month=mm, day=dd,hour=8)
    END = datetime(year=yy, month=mm, day=dd,hour=8)

    if isholidays(start_date=START):
        sys.exit(1)

    sys.exit(0)