import yfinance as yf
from datetime import datetime , timedelta
import pandas as pd
from .option_calculate import OptionInput,OptionGreeks,implied_volatility,calculate_greeks
from .sql_lib import insert_option_db

OPTION_LIST = ["SPY",
               "^VIX"]

def exdays(cur_date : datetime , exp_date : str):
    year,mom,day = exp_date.split("-")
    day = int(day)
    mom = int(mom)
    year = int(year)
            
    exp = datetime(year, mom, day) + timedelta(hours = 16)
    return (exp- cur_date).days / 365.0
    
def save_option_snap(today:datetime):
    option_snapshots = []

    for stock_name in OPTION_LIST:
        ticker = yf.Ticker(stock_name)
        options = ticker.options
        current_stock_price = ticker.history(period="1d")['Close'].iloc[0]
        last_trade_day = ticker.history(period="1d").index[0]
        year, month, day = last_trade_day.year, last_trade_day.month, last_trade_day.day
        
        if datetime(year=year,month=month,day=day,hour=16) != today:
            return
        
        for exp_date in options:
            option_chain  = ticker.option_chain(exp_date)
            chains = []
            call_chain = option_chain.calls['strike']
            put_chain = option_chain.puts['strike']
            chains.append(("call",call_chain))
            chains.append(("put",put_chain))

            for type,chain in chains:
                
                for price in chain:
                    if "call" == type:
                        selected_option = option_chain.calls[chain == price]
                    else:
                        selected_option = option_chain.puts[chain == price]

                    print(selected_option)

                    k = selected_option['strike'].iloc[0]
                    oi = selected_option['openInterest'].iloc[0]
                    volume = selected_option['volume'].iloc[0]
                    market_price = selected_option['lastPrice'].iloc[0]

                    t = exdays(today,exp_date)
                    opt = OptionInput(
                        option_type=type,
                        S=current_stock_price,
                        K=k,
                        T=t,
                        r=0.04,
                        market_price=market_price
                    )

                    iv = implied_volatility(opt)
                    if iv:
                        greek = calculate_greeks(opt,iv)
                        print(greek)
                    else:
                        print("cal iv fail")
                        continue
                    
                    option_snapshots.append({
                        "symbol":stock_name,
                        "date":today,
                        "dte":round(t*365),
                        "expiration": exp_date,
                        "strike": k,
                        "option_type": type,
                        "iv": iv,
                        "delta": float(greek.Delta),
                        "gamma": float(greek.Gamma),
                        "theta": float(greek.Theta),
                        "vega": float(greek.Vega),
                        "rho": float(greek.Rho),
                        "oi": oi,
                        "volume": volume,
                        "last_price": market_price,
                    })

    df = pd.DataFrame(option_snapshots)
    insert_option_db(df)

if __name__ == "__main__":
    save_option_snap()