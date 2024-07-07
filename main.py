from data_analysis import Ath_model
from datetime import datetime

if __name__ == "__main__":
    RANGE = 10
    START = datetime(year=2022, month=1, day=7,hour=8)
    END   = datetime(year=2024, month=7, day=5,hour=8)

    ath_model = Ath_model(start_date=START,end_date=END,gap_to_high_range=RANGE,reuse_data=True)
    ath_model.run()