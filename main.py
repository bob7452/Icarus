from data_analysis import Ath_model
from datetime import datetime
from shutil import rmtree
import os
from get_stock_info import MARKET_CAP_10E

def restore():
    rmtree(path="rs_report")
    rmtree(path="report")
    rmtree(path="classic")
    rmtree(path="all")

    os.mkdir("rs_report")
    os.mkdir("report")
    os.mkdir("classic")
    os.mkdir("all")

if __name__ == "__main__":

    restore()

    RANGE = 10
    START = datetime(year=2015, month=1, day=2,hour=8)
    END   = datetime(year=2025, month=11, day=14,hour=8)

    ath_model = Ath_model(start_date=START,end_date=END,gap_to_high_range=RANGE,marketCap=MARKET_CAP_10E,reuse_data=True)
    ath_model.run()

