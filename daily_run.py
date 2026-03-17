from data_analysis import Ath_model
from datetime import datetime , timedelta
from pandas_market_calendars import get_calendar
import sys
from get_stock_info import MARKET_CAP_10E

from pathlib import Path
import shutil

def restore():
    folders = ["rs_report", "report", "classic", "all"]
    
    for folder in folders:
        path = Path(folder)
        # 如果資料夾存在，就刪除它及其內容
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
        
        # 建立新資料夾，parents=True 確保父層存在，exist_ok=True 避免重複建立報錯
        path.mkdir(parents=True, exist_ok=True)
    
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

    ath_model = Ath_model(start_date=START,end_date=END,gap_to_high_range=RANGE,marketCap=MARKET_CAP_10E,reuse_data=False)
    ath_model.run()
