'''
File : data analysis.py
process data
'''

from common_data_type import industry_group,market_group,sliced_candle_info,history_price_group
from datetime import datetime , timedelta
from get_stock_info import load_prices_from_yahoo , get_stock_history_price_data , get_total_stocks_basic_info , MARKET_CAP_100E
import pandas as pd
import numpy as np
import os


PERIOD = 1 * 365 + 183
WEEKLY_52_BAR = 252
SEASON_BAR = 63
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

def calculate_moving_average(data:list,moving_weight : int = 5) -> list:
    df = pd.DataFrame(data,columns=['Price'])
    df[f'MA{moving_weight}'] = df['Price'].rolling(window=moving_weight).mean().fillna(0)
    return df[f'MA{moving_weight}'].tolist()

def above_all_moving_avg_line(data):
    weights = [5, 10, 20, 50, 100, 150, 200]
    moving_averages = {weight: calculate_moving_average(data, weight)[-1] for weight in weights}
    last_price = data[-1]

    above_all = all(last_price >= moving_averages[weight] for weight in weights)
    
    specific_condition = (
        last_price > moving_averages[20] > moving_averages[50] > moving_averages[200]
    )

    return above_all and specific_condition

def cal_volatility(open_bars : list,close_bars : list):
    change = []

    days = len(open_bars)

    for idx in range(days-1):
        open_price = open_bars[idx]
        close_price = close_bars[idx+1]
        change.append((close_price-open_price)/open_price)

    std_dev = np.std(change)

    return "{:.2f}".format(std_dev * np.sqrt(WEEKLY_52_BAR) * 100)

def yearly_change(bars_cloes_start : int , weekly_52_low : int , bar_close_end : int):
    return round(((bar_close_end / bars_cloes_start) -1 ) * 100 ,2) if bars_cloes_start < weekly_52_low else round(((bar_close_end / weekly_52_low) -1 ) * 100 ,2) 

def seanson_change(bar_close : list) -> list:
    changes = []
    for i in range(4,0,-1):
        tmp = bar_close[-1 * SEASON_BAR * i :]
        if len(bar_close) < SEASON_BAR * i:
            changes.append(None)
        else:
            tmp = tmp[:SEASON_BAR]
            changes.append(round(((tmp[-1] / tmp[0]) - 1)* 100,2))
    return changes

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
    volume : list = candles.volumes[-WEEKLY_52_BAR:]
    timestamp : list = candles.timestamps[-WEEKLY_52_BAR:]

    weekly_52_high = max(bars_close)
    weekly_52_low = min(bars_close)

    gap = round(((weekly_52_high - bars_close[-1]) / weekly_52_high) * 100, 2)
    ma5 = calculate_moving_average(volume)
    ma20 = calculate_moving_average(volume,20)

    break_high = is_high_low_between_this_week(timestamp[bars_close.index(weekly_52_high)], candles.this_week[0],candles.this_week[1])
    break_low =  is_high_low_between_this_week(timestamp[bars_close.index(weekly_52_low)], candles.this_week[0],candles.this_week[1])
    break_high_today = timestamp[bars_close.index(weekly_52_high)] == candles.today
    big_volume = volume[-1] > ma5[-1] and volume[-1] > ma20[-1]

    history = history_price_group(
        weekly_52_high=weekly_52_high,
        weekly_52_low=weekly_52_low,
        gap_from_the_last_high=gap,
        break_high=break_high,
        break_low=break_low,
        break_high_today=break_high_today,
        big_volume = big_volume,
        above_all_moving_avg_line=above_all_moving_avg_line(bars_close),
        volatility = cal_volatility(bars_open[bars_close.index(weekly_52_low):],bars_close[bars_close.index(weekly_52_low):]),
        weekly_change=week_change(candles=candles),
        yearly_change=yearly_change(bars_cloes_start=bars_close[0],bar_close_end=bars_close[-1],weekly_52_low=weekly_52_low),
        seasons_change=seanson_change(bar_close=bars_close),
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

        if abs(his_data.gap_from_the_last_high) <= range:
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

def cal_spy(start_date: datetime) -> history_price_group:

    ticket_candles = load_prices_from_yahoo(ticket_name='SPY')._asdict()

    candles = slice_data(
        start_date=start_date, ticket_candles=ticket_candles
    )

    his_data = history_price_filter(candles=candles)

    return his_data

@staticmethod
def get_week_start_and_end(start_date_friday : datetime = None) -> tuple:

    if  start_date_friday is None or start_date_friday.weekday() != 4:
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
    monday_timestamp , _ = get_week_start_and_end(start_date_friday=start_date)
    monday_datetime = datetime.fromtimestamp(monday_timestamp)
    print(f"monday_datetime : {monday_datetime}")
    while True:
        
        now_date = datetime.fromtimestamp(start_date_timestamp)
        print(f"now_date : {now_date} , {start_date_timestamp}")
        if now_date < monday_datetime:
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
        today=start_date.timestamp(),
    )

def relative_strength(season_change :list , season_weight , season_min):
    none_count = season_change.count(None)

    if none_count == 4:
        return -1
    elif none_count == 3:
        return (season_change[-1] - season_min[-1]) / season_weight[-1]
    elif none_count == 2:
        return (season_change[-1] - season_min[-1]) / season_weight[-1] * 0.6 \
                + (season_change[-2] - season_min[-2]) / season_weight[-2] * 0.4
    elif none_count == 1:
        return (season_change[-1] - season_min[-1]) / season_weight[-1] * 0.6 \
                + (season_change[-2] - season_min[-2]) / season_weight[-2] * 0.2 \
                + (season_change[-3] - season_min[-3]) / season_weight[-3] * 0.2
    else:
        return (season_change[-1] - season_min[-1]) / season_weight[-1] * 0.6 \
                + (season_change[-2] - season_min[-2]) / season_weight[-2] * 0.2 \
                + (season_change[-3] - season_min[-3]) / season_weight[-3] * 0.1 \
                + (season_change[-4] - season_min[-4]) / season_weight[-4] * 0.1

def gen_rs_report(start_date,weekly_result:market_group,gap_range = 10):
    spy_data = cal_spy(start_date=start_date)

    rs_list = {}
    season_total = {i : [] for i in range(4)}

    for industry_name, industry_data in weekly_result.industry.items():

        for stock_name , stock_history_data in industry_data.stock.items():
            
            close_to_high = False
            powerful_than_spy = False
            group_powerful_than_spy = False
            breakout_with_big_volume = False
            above_all_moving_avg_line = False
            volatility= stock_history_data.volatility

            if stock_history_data.yearly_change < spy_data.yearly_change:
                continue
            
            if stock_history_data.weekly_change > spy_data.weekly_change:
                powerful_than_spy = True

            if industry_data.week_change_avg > spy_data.weekly_change:
                group_powerful_than_spy = True

            if stock_history_data.gap_from_the_last_high < gap_range:
                close_to_high = True
                
            if stock_history_data.big_volume and stock_history_data.break_high_today:
                breakout_with_big_volume = True

            if stock_history_data.above_all_moving_avg_line:
                above_all_moving_avg_line = True
                
            for idx,season_change  in enumerate(stock_history_data.seasons_change):
                if season_change:
                    season_total[idx].append(season_change)

            rs = abs(stock_history_data.yearly_change - spy_data.yearly_change)
            rs_list[stock_name] = (rs,
                                   volatility,
                                   close_to_high,
                                   powerful_than_spy,
                                   group_powerful_than_spy,
                                   breakout_with_big_volume,
                                   above_all_moving_avg_line,
                                   industry_name,
                                   stock_history_data.seasons_change)

    rs_dataframe = []

    season_weight = []
    season_min = []

    for i in range(4):
        season_min.append(min(season_total[i]))
        season_weight.append(abs(max(season_total[i])-min(season_total[i])))

    
    for name , data in rs_list.items():
        tmp = {"name" : name,
               "yearly_change" : data[0],
               "current_season_change" : data[8][-1],
               "volatility(%)":data[1],
               f"close_to_high_{gap_range}%" : data[2],
               "powerful_than_spy" : data[3],
               "group_powerful_than_spy" : data[4],
               "breakout_with_big_volume" : data[5],
               "above_all_moving_avg_line" : data[6],
               "industry_name" : data[7],
               "relative_strength" : relative_strength(season_change=data[8],season_weight=season_weight,season_min=season_min),
               }
        df = pd.DataFrame(tmp, index=[0])
        rs_dataframe.append(df)

    ALLDF = pd.concat(rs_dataframe, ignore_index=True)
    ALLDF = ALLDF.sort_values(by='relative_strength',ascending=False)
    
    total_count = len(rs_list.keys())
    avg = 100 / (total_count -1)
    ranklist = [100 - avg * i for i in range(total_count)]
    ranklist[-1] = 0
    
    ALLDF['rank'] = ranklist

    daystring = start_date.strftime("%Y-%m-%d")
    file_name = os.path.join("rs_report","rs_model_" + daystring + ".csv")
    ALLDF.to_csv(file_name,index=False)

class Ath_model:
    
    '''
    This class will categorize stocks that meet the marketCap criteria
    within the period from start_date to end_date.
    '''

    def __init__(self,start_date : datetime , end_date : datetime , marketCap = MARKET_CAP_100E ,gap_to_high_range = 10 , reuse_data = False) -> None:
        self.stocks_info : dict = get_total_stocks_basic_info(marketCap=marketCap,reuse_data=reuse_data)
        self.stocks_price_data : dict = get_stock_history_price_data(self.stocks_info,reuse_data=reuse_data)
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
            gen_rs_report(start_date=day,weekly_result=weekly_result,gap_range=self.range)

            tmp = {
                "start_date": day.strftime("%Y-%m-%d"),
                "ath_count": weekly_result.ath_count,
                "atl_count": weekly_result.atl_count,
            }


            df = pd.DataFrame(tmp, index=[0])
            history.append(df)


            day = day + timedelta(days=7)

        allDF = pd.concat(history, ignore_index=True)
        file_name  = "datasheet.csv"
        exist_data = pd.read_csv(file_name)
        allDF = pd.concat([exist_data,allDF],ignore_index=True)
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


