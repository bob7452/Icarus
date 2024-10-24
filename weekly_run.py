from data_analysis import Ath_model
from datetime import datetime

if __name__ == "__main__":

    yy,mm,dd  = map(int,datetime.today().strftime("%Y-%m-%d").split('-'))

    RANGE = 10
    START = datetime(year=2020, month=1, day=3,hour=8)
    END = datetime(year=yy, month=mm, day=dd-1,hour=8)
    ath_model = Ath_model(start_date=START,end_date=END,gap_to_high_range=RANGE,reuse_data=False)
    ath_model.run()
