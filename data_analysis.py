'''
File : data analysis.py
process data
'''

from common_data_type import industry_group,market_group,sliced_candle_info,history_price_group
from datetime import datetime , timedelta
from file_io import read_from_json
from get_stock_info import get_stock_history_price_data , get_total_stocks_basic_info , MARKET_CAP_100E , MARKET_CAP_10E , STOCK_INFO_JSON_PATH , STOCK_PRICE_JSON_FILE

import pandas as pd
import os


PERIOD = 1 * 365 + 183
WEEKLY_52_BAR = 252
LIMIT = datetime(year=2019,month=12,day=27,hour=8)
RANGE = 10

@staticmethod
def week_change(candles:sliced_candle_info) -> float:
    index = 0
    firday_last_week_timestamp = candles.this_week[1] - (86400 * 7)
    limit = datetime.fromtimestamp(candles.this_week[0] - (86400 * 7))
    
    while True:
        now_date = datetime.fromtimestamp(firday_last_week_timestamp)

        if now_date < limit:
            print("Noooooo Find")
            return 0

        if firday_last_week_timestamp in candles.timestamps:
            index = candles.timestamps.index(firday_last_week_timestamp)
            print(f"index = {index} , datetime = {datetime.fromtimestamp(firday_last_week_timestamp)}")
            break
        else:
            firday_last_week_timestamp -= 86400

    return round(( (candles.closes[-1] /candles.closes[index]) -1 ) * 100 ,2)

    

@staticmethod
def history_price_filter(candles: sliced_candle_info) -> history_price_group:
    """
    cal 52 weekly day high and low (210 kbars)
    """

    def is_high_low_between_this_week(day,start,end):
            return True if start <= day <= end else False

    bars_high : list  = candles.highs[-WEEKLY_52_BAR:]
    bars_low : list = candles.lows[-WEEKLY_52_BAR:]
    bars_close : list = candles.closes[-WEEKLY_52_BAR:]
    bars_open : list = candles.opens[-WEEKLY_52_BAR:]
    timestamp : list = candles.timestamps[-WEEKLY_52_BAR:]

    weekly_52_high = max(bars_high)
    weekly_52_low = min(bars_low)

    gap = round(((weekly_52_high - bars_close[-1]) / weekly_52_high) * 100, 2)

    break_high = is_high_low_between_this_week(timestamp[bars_high.index(weekly_52_high)], candles.this_week[0],candles.this_week[1])
    break_low =  is_high_low_between_this_week(timestamp[bars_low.index(weekly_52_low)], candles.this_week[0],candles.this_week[1])

    history = history_price_group(
        weekly_52_high=weekly_52_high,
        weekly_52_low=weekly_52_low,
        gap_from_the_last_high=gap,
        break_high=break_high,
        break_low=break_low,
        weekly_change=week_change(candles=candles),
    )

    if break_high and break_low:
        return None

    return history

@staticmethod
def cal_data(tickets_info: dict, start_date: datetime, all_data: dict , range = 10):

    total_stocks = len(tickets_info.keys())

    market_result = market_group()
    for idx, ticket_name in enumerate(tickets_info.keys()):
        print(f"cal process ({idx+1}/{total_stocks})")

        candles = slice_data(
            start_date=start_date, ticket_candles=all_data[ticket_name]
        )

        
        if candles == None:
            print("no slice")
            continue

        his_data = history_price_filter(candles=candles)

        if his_data is None:
            continue

        print("ticket name ", ticket_name)
        print(his_data)

        industry = tickets_info[ticket_name]["industry"]

        if industry not in market_result.industry:
            market_result.industry[industry] = industry_group()

        # class industry_group:
        #     stock:dict = {}
        #     ath_count :int = 0
        #     atl_count :int = 0
        #     break_high_group : list = []
        #     break_low_group : list = []
        #     approach_high : list = []

        market_result.industry[industry].stock[ticket_name] = his_data

        if his_data.break_high:
            market_result.industry[industry].ath_count += 1
            market_result.industry[industry].break_high_group.append(ticket_name)

        if his_data.break_low:
            market_result.industry[industry].atl_count += 1
            market_result.industry[industry].break_low_group.append(ticket_name)

        if abs(his_data.gap_from_the_last_high) < range:
            market_result.industry[industry].approach_high.append(ticket_name)

        market_result.industry[industry].week_change_avg += his_data.weekly_change

    # class market_group:
    #     industry:dict = {}
    #     max_ath:str ="n/a"
    #     max_atl:str ="n/a"
    #     ath_count:int = 0
    #     atl_count:int = 0

    atl_list = {}
    ath_list = {}
    ath_count = 0
    atl_count = 0

    allDF = pd.DataFrame()
    dfs = []

    for industry_name, industry_data in market_result.industry.items():
        data = {}
        data["industry_name"] = industry_name
        data.update(
            {
                "break_high_group": " ,".join(industry_data.break_high_group),
                "break_low_group": " ,".join(industry_data.break_low_group),
                "approach_high": " ,".join(industry_data.approach_high),
                "ath_count": industry_data.ath_count,
                "atl_count": industry_data.atl_count,
                "approach_count" : len(industry_data.approach_high),
                "ath_ratio": str(round(industry_data.ath_count / len(industry_data.stock.keys()),2)),
                "atl_ratio": str(round(industry_data.atl_count / len(industry_data.stock.keys()),2)),
                "approach_ratio": str(round( len(industry_data.approach_high) / len(industry_data.stock.keys()),2)), 
                "weekly_chagne" : str(round( industry_data.week_change_avg / len(industry_data.stock.keys()),2)), 
                "total_stocks" : len(industry_data.stock.keys()),
            }
        )

        df = pd.DataFrame(data, index=[0])
        dfs.append(df)

        ath_list[industry_name] = industry_data.ath_count
        atl_list[industry_name] = industry_data.atl_count

        ath_count += industry_data.ath_count
        atl_count += industry_data.atl_count

    allDF = pd.concat(dfs, ignore_index=True)

    today = start_date.strftime("%Y-%m-%d")
    file_name = "ath_model_" + today + ".csv"
    file_name = os.path.join("report",file_name)

    allDF.to_csv(file_name, index=False)

    max_ath = max(ath_list, key=ath_list.get)
    max_atl = max(atl_list, key=atl_list.get)

    market_result.max_ath = max_ath
    market_result.max_atl = max_atl
    market_result.ath_count = ath_count
    market_result.atl_count = atl_count

    date = start_date.strftime("%Y-%m-%d")
    print(f"{date} : {market_result}")

    return market_result



@staticmethod
def get_week_start_and_end(start_date_friday : datetime = None) -> tuple:

    if  start_date_friday is None:
        today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        monday = today - timedelta(days=today.weekday())  # Monday
        friday = monday + timedelta(days=4)  # Friday

        monday = monday + timedelta(hours=8)
        friday = friday + timedelta(hours=8)
    else:
        monday = start_date_friday - timedelta(days=4) + timedelta(hours=8)
        friday = start_date_friday

    return (monday.timestamp(), friday.timestamp())

@staticmethod
def slice_data(start_date: datetime, ticket_candles: dict):

    index = 0
    start_date_timestamp = start_date.timestamp()
    while True:
        
        now_date = datetime.fromtimestamp(start_date_timestamp)
        if now_date < LIMIT:
            return None

        if start_date_timestamp in ticket_candles["timestamps"]:
            index = ticket_candles["timestamps"].index(start_date_timestamp)
            print(f"index = {index} , day = {datetime.fromtimestamp(start_date_timestamp)}")
            break
        else:
            start_date_timestamp -= 86400

    return sliced_candle_info(
        opens=ticket_candles["opens"][: index + 1],
        closes=ticket_candles["closes"][: index + 1],
        lows=ticket_candles["lows"][: index + 1],
        highs=ticket_candles["highs"][: index + 1],
        volumes=ticket_candles["volumes"][: index + 1],
        timestamps=ticket_candles["timestamps"][: index + 1],
        this_week=get_week_start_and_end(start_date_friday=start_date),
    )

class Ath_model:
    
    '''
    This class will categorize stocks that meet the marketCap criteria
    within the period from start_date to end_date.
    '''

    def __init__(self,start_date : datetime , end_date : datetime , marketCap = MARKET_CAP_100E ,gap_to_high_range = 10 , reuse_data = False) -> None:
        self.stocks_info : dict = read_from_json(STOCK_INFO_JSON_PATH) if reuse_data else get_total_stocks_basic_info(marketCap=marketCap)
        self.stocks_price_data : dict = read_from_json(STOCK_PRICE_JSON_FILE) if reuse_data else get_stock_history_price_data(self.stocks_info)
        self.start_date = start_date
        self.end_date = end_date    
        self.range = gap_to_high_range
        self.marketCap = marketCap

        
    def run(self):

        day = self.start_date
        history = []
        weekly_list = []
        while True:
            if day > self.end_date:
                break
            weekly_result = cal_data(tickets_info=self.stocks_info,
                                     start_date=day,
                                     all_data=self.stocks_price_data,
                                     range=self.range)
            
            weekly_list.append((day.strftime("%Y-%m-%d"),weekly_result))
                    
            tmp = {
                "start_date": day.strftime("%Y-%m-%d"),
                "ath_count": weekly_result.ath_count,
                "atl_count": weekly_result.atl_count,
            }


            df = pd.DataFrame(tmp, index=[0])
            history.append(df)


            day = day + timedelta(days=7)

        allDF = pd.concat(history, ignore_index=True)
        name  = self.start_date.strftime("%Y-%m-%d") + '_' + self.end_date.strftime("%Y-%m-%d") 
        file_name = "ath_model_" + name + ".csv"
        allDF.to_csv(file_name, index=False)


        classic = {}
        for daystring , weekly_result in weekly_list:
            
            for industry_name, industry_data in weekly_result.industry.items():
                
                if industry_name not in classic:
                    classic[industry_name] = []
            

                tmp = {
                    "datetime" : daystring,
                    "break_high_group": " ,".join(industry_data.break_high_group),
                    "break_low_group": " ,".join(industry_data.break_low_group),
                    "approach_high": " ,".join(industry_data.approach_high),
                    "ath_count": industry_data.ath_count,
                    "atl_count": industry_data.atl_count,
                    "approach_count" : len(industry_data.approach_high),
                    "ath_ratio": str(round(industry_data.ath_count / len(industry_data.stock.keys()),2)),
                    "atl_ratio": str(round(industry_data.atl_count / len(industry_data.stock.keys()),2)),
                    "approach_ratio": str(round( len(industry_data.approach_high) / len(industry_data.stock.keys()),2)), 
                    "weekly_chagne" : str(round( industry_data.week_change_avg / len(industry_data.stock.keys()),2)), 
                    "total_stocks" : len(industry_data.stock.keys()),
                }
                
                df = pd.DataFrame(tmp, index=[0])
                classic[industry_name].append(df)

        for industry_name, data in classic.items():
            print(data)
            ALLDF = pd.concat(data, ignore_index=True)
            name  = industry_name
            file_name = "ath_model_" + name + ".csv"
            file_name = os.path.join("classic",file_name)
            ALLDF.to_csv(file_name, index=False)