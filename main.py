from get_component import load_component,MARKET_CAP_10E,MARKET_CAP_100E,MARKET_CAP_50E
from download_data import load_prices_from_yahoo, history_price_search, candles_info
from ath_model import market_group, industry_group
import pandas as pd
from datetime import datetime, timedelta
from file_io import read_from_json ,save_to_json
import os


RANGE = 20

START = datetime(year=2020, month=1, day=3,hour=8)
END   = datetime(year=2024, month=5, day=17,hour=8)
LIMIT = datetime(year=2020,month=1,day=1,hour=8)


def load_candles(tickets_info: dict) -> dict:

    total_stocks = len(tickets_info.keys())

    all_candles = {}
    start_date = START - timedelta(days=252)
    end_date = END

    for idx, name in enumerate(tickets_info.keys()):
        print(f"load candles ({idx+1}/{total_stocks})")
        all_candles[name] = load_prices_from_yahoo(
            ticket_name=name, start_date=start_date, end_date=end_date
        )._asdict()

    file_path = "candles.json"
    save_to_json(data=all_candles,json_file_path=file_path)
    return all_candles


def cal_data(tickets_info: dict, start_date: datetime, all_data: dict):

    total_stocks = len(tickets_info.keys())

    market_result = market_group()
    for idx, ticket_name in enumerate(tickets_info.keys()):
        print(f"cal process ({idx+1}/{total_stocks})")

        candles = slice_data(
            start_date=start_date, ticket_candles=all_data[ticket_name]
        )

        
        if candles == None:
            continue

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

    atl_list = {}
    ath_list = {}
    ath_count = 0
    atl_count = 0
    approach_high_count = 0

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
                "ath_ratio": str(round(industry_data.ath_count / len(industry_data.stock.keys()),2)),
                "atl_ratio": str(round(industry_data.atl_count / len(industry_data.stock.keys()),2)),
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

    return {
        "start_date": date,
        "ath_count": ath_count,
        "atl_count": atl_count,
    }


def slice_data(start_date: datetime, ticket_candles: dict):
    start_date_timestamp = start_date.timestamp()
    index = 0


    while True:
        
        now_time= datetime.fromtimestamp(start_date_timestamp)
        if now_time < LIMIT:
            print("here")
            return None

        if start_date_timestamp in ticket_candles["timestamps"]:
            index = ticket_candles["timestamps"].index(start_date_timestamp)
            print(f"index = {index} , day = {datetime.fromtimestamp(start_date_timestamp)}")
            break
        else:
            start_date_timestamp -= 86400

    return candles_info(
        opens=ticket_candles["opens"][: index + 1],
        closes=ticket_candles["closes"][: index + 1],
        lows=ticket_candles["lows"][: index + 1],
        highs=ticket_candles["highs"][: index + 1],
        volumes=ticket_candles["volumes"][: index + 1],
        timestamps=[],
    )

def cal_history_ath_model(load_new_data : bool = False , marketCap = MARKET_CAP_100E):


    tickets_info = read_from_json("stock_info.json") if load_new_data == False else load_component(marketCap=marketCap)
    all_data = read_from_json('candles.json') if load_new_data == False else load_candles(tickets_info=tickets_info)

    start_date = START
    offset = 7

    weekly = []

    while True:
        if start_date > datetime.today():
            break

        print(start_date)
        week_result = cal_data(
            tickets_info=tickets_info, start_date=start_date, all_data=all_data
        )

        weekly.append(pd.DataFrame(week_result, index=[0]))
        start_date = start_date + timedelta(days=offset)

    start_str = START.strftime('%Y-%m-%d')
    end_str = END.strftime('%Y-%m-%d')

    file_name = "ath_model_" + f"from {start_str} to {end_str}" + ".csv"
    weekly = pd.concat(weekly, ignore_index=True)
    weekly.to_csv(file_name, index=False)

def cal_this_weekly_ath_model(marketCap = MARKET_CAP_10E):

    tickets_info = load_component(marketCap=marketCap)
    total_stocks = len(tickets_info.keys())

    market_result = market_group()
    for idx, ticket_name in enumerate(tickets_info.keys()):
        print(f"cal process ({idx+1}/{total_stocks})")

        candles = load_prices_from_yahoo(ticket_name=ticket_name)
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
            }
        )

        df = pd.DataFrame(data, index=[0])
        dfs.append(df)

        ath_list[industry_name] = industry_data.ath_count
        atl_list[industry_name] = industry_data.atl_count

        ath_count += industry_data.ath_count
        atl_count += industry_data.atl_count

    allDF = pd.concat(dfs, ignore_index=True)

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    file_name = "ath_model_" + today + ".csv"
    print(today)
    allDF.to_csv(file_name, index=False)

    max_ath = max(ath_list, key=ath_list.get)
    max_atl = max(atl_list, key=atl_list.get)

    market_result.max_ath = max_ath
    market_result.max_atl = max_atl
    market_result.ath_count = ath_count
    market_result.atl_count = atl_count

    print(market_result)


if __name__ == "__main__":
    cal_history_ath_model(load_new_data=True,marketCap=MARKET_CAP_100E)
    #cal_this_weekly_ath_model()