from data_analysis import Ath_model
from datetime import datetime , timedelta
from shutil import rmtree
import os
from pandas_market_calendars import get_calendar
import sys

def restore():
    rmtree(path="rs_report")
    rmtree(path="report")
    rmtree(path="classic")
    rmtree(path="all")

    os.mkdir("rs_report")
    os.mkdir("report")
    os.mkdir("classic")
    os.mkdir("all")
    
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

    RANGE = 10
    yy,mm,dd  = map(int,(datetime.today()-timedelta(days=1)).strftime("%Y-%m-%d").split('-'))
    START = datetime(year=yy, month=mm, day=dd,hour=8)
    END = datetime(year=yy, month=mm, day=dd,hour=8)

    if isholidays(start_date=START):
        sys.exit(1)

    restore()

    ath_model = Ath_model(start_date=START,end_date=END,gap_to_high_range=RANGE,reuse_data=False)
    ath_model.run()
