from data_analysis import Ath_model
from datetime import datetime
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
    

if __name__ == "__main__":

    restore()

    RANGE = 10
    START = datetime(year=2015, month=1, day=2,hour=8)
    END   = datetime(year=2025, month=11, day=14,hour=8)

    ath_model = Ath_model(start_date=START,end_date=END,gap_to_high_range=RANGE,marketCap=MARKET_CAP_10E,reuse_data=True)
    ath_model.run()

