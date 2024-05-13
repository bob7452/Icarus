from get_component import load_component
from download_data import load_prices_from_yahoo, history_price_search,candles_info
from ath_model import market_group, industry_group
import pandas as pd
from datetime import datetime , timedelta
import sys
import json


RANGE = 10

def load_candles(tickets_info : dict) -> dict:

    total_stocks = len(tickets_info.keys())

    all_candles = {}
    start_date = datetime(year=2020,month=1,day=3)
    end_date = datetime(year=2020,month=5,day=10)

    for idx,name in enumerate(tickets_info.keys()):
        print(f"load candles ({idx+1}/{total_stocks})")
        all_candles[name] = load_prices_from_yahoo(ticket_name=name,start_date=start_date,end_date=end_date)._asdict()

    json_data = json.dumps(all_candles)

    file_path = 'candles.json'

    with open(file_path, 'w') as file:
        file.write(json_data)

    return all_candles

def cal_data(tickets_info:dict,
             start_date : datetime, 
             all_data : dict):
    
    total_stocks = len(tickets_info.keys())

    market_result = market_group()
    for idx, ticket_name in enumerate(tickets_info.keys()):
        print(f"cal process ({idx+1}/{total_stocks})")

        candles = slice_data(start_date=start_date,
                             ticket_candles=all_data[ticket_name])
        his_data = history_price_search(candles=candles)

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

        if abs(his_data.gap_from_the_last_high) < RANGE:
            market_result.industry[industry].approach_high.append(ticket_name)

    # class market_group:
    #     industry:dict = {}
    #     max_ath:str ="n/a"
    #     max_atl:str ="n/a"
    #     ath_count:int = 0
    #     atl_count:int = 0

    # atl_list = {}
    # ath_list = {}
    ath_count = 0
    atl_count = 0

    # allDF = pd.DataFrame()
    # dfs = []

    for industry_name, industry_data in market_result.industry.items():
        # data = {}
        # data["industry_name"] = industry_name
        # data.update(
        #     {
        #         "break_high_group": " ,".join(industry_data.break_high_group),
        #         "break_low_group": " ,".join(industry_data.break_low_group),
        #         "approach_high": " ,".join(industry_data.approach_high),
        #         "ath_count": industry_data.ath_count,
        #         "atl_count": industry_data.atl_count,
        #     }
        # )

        # df = pd.DataFrame(data, index=[0])
        # dfs.append(df)

        # ath_list[industry_name] = industry_data.ath_count
        # atl_list[industry_name] = industry_data.atl_count

        ath_count += industry_data.ath_count
        atl_count += industry_data.atl_count

    # allDF = pd.concat(dfs, ignore_index=True)

    # now = datetime.now()
    # today = now.strftime("%Y-%m-%d")
    # file_name = "ath_model_" + today + ".csv"
    # print(today)
    # allDF.to_csv(file_name, index=False)

    # max_ath = max(ath_list, key=ath_list.get)
    # max_atl = max(atl_list, key=atl_list.get)

    # market_result.max_ath = max_ath
    # market_result.max_atl = max_atl
    market_result.ath_count = ath_count
    market_result.atl_count = atl_count

    date = start_date.strftime('%Y-%m-%d')
    print(f"{date} : {market_result}")

    return { "start_date": date,
             "ath_count" : ath_count,
             "atl_count" : atl_count,}


def slice_data(start_date : datetime , ticket_candles : dict):
    start_date_timestamp = start_date.timestamp()
    index = 0

    while True:

        if start_date_timestamp in ticket_candles['timestamps']:
            index = ticket_candles['timestamps'].index(start_date_timestamp)
            break
        else:
            start_date_timestamp -= 86400


    return candles_info(opens=ticket_candles['opens'][:index+1],
                 closes=ticket_candles['closes'][:index+1],
                 lows=ticket_candles['lows'][:index+1],
                 highs=ticket_candles['highs'][:index+1],
                 volumes=ticket_candles['volumes'][:index+1],
                 timestamps=[])

if __name__ == "__main__":

    tickets_info = load_component()
    all_data = load_candles(tickets_info=tickets_info)

    start_date = datetime(year=2020,month=1,day=3)
    offset = 0

    weekly = []

    while True:

        if start_date > datetime.today():
            break
 
        week_result = cal_data(tickets_info=tickets_info,start_date=start_date,all_data=all_data)

        weekly.append(pd.DataFrame(week_result,index=[0]))

        offset +=7
        start_date = start_date + timedelta(days=offset)

        
    file_name = "ath_model_" +"from 20200103 to 20240510" + ".csv"
    weekly.to_csv(file_name, index=False)
