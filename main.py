from get_component import load_component
from download_data import load_prices_from_yahoo, history_price_search
from ath_model import market_group,industry_group
import pandas as pd
from datetime import datetime

RANGE = 10

if __name__ == "__main__":
    
    market_result = market_group()

    tickets_info = load_component()
    total = len(tickets_info.keys())

    for idx,ticket_name in enumerate(tickets_info.keys()):
        print(f"process ({idx+1}/{total})")

        candles = load_prices_from_yahoo(ticket_name=ticket_name)

        his_data = history_price_search(candles=candles)

        if his_data is None:
            continue

        print("ticket name ",ticket_name)
        print(his_data)

        industry =tickets_info[ticket_name]['industry']

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
            market_result.industry[industry].ath_count +=1
            market_result.industry[industry].break_high_group.append(ticket_name)
        
        if his_data.break_low:
            market_result.industry[industry].atl_count +=1
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

    for industry_name , industry_data in market_result.industry.items():
        data = {}
        data['industry_name'] = industry_name
        data.update({
               "break_high_group" : ' ,'.join(industry_data.break_high_group),
               "break_low_group" : ' ,'.join(industry_data.break_low_group),
               "approach_high"  : ' ,'.join(industry_data.approach_high),
               "ath_count" : industry_data.ath_count,
               "atl_count" : industry_data.atl_count,})
        
        df = pd.DataFrame(data, index=[0])
        dfs.append(df)

        ath_list[industry_name] = industry_data.ath_count
        atl_list[industry_name] = industry_data.atl_count
        
        ath_count += industry_data.ath_count
        atl_count += industry_data.atl_count

    allDF = pd.concat(dfs,ignore_index=True)

    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    file_name = "ath_model_" + today + ".csv"
    print(today)
    allDF.to_csv(file_name,index=False)

    max_ath = max(ath_list,key=ath_list.get)
    max_atl = max(atl_list,key=atl_list.get)

    market_result.max_ath = max_ath
    market_result.max_atl  = max_atl
    market_result.ath_count = ath_count
    market_result.atl_count = atl_count

    print(market_result)
