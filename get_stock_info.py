"""
File : get_stock_info.py
load s&p 500 and nasdaq companies
"""

from collections import namedtuple
import re
from ftplib import FTP
from io import StringIO
import yfinance as yf
from file_io import save_to_json, read_from_json
import time
from common_data_type import candles_info

UNKNOWN = "unknown"

STOCK_INFO_JSON_PATH = "stock_info.json"
STOCK_PRICE_JSON_FILE = "candles.json"

MARKET_CAP_1000E = 100_000_000_000
MARKET_CAP_100E = 10_000_000_000
MARKET_CAP_50E  = 5_000_000_000
MARKET_CAP_10E  = 1_000_000_000

Ticket = namedtuple("Ticket", ["ticket", "sector", "industry", "marketCap",])

@staticmethod
def get_tickers_from_nasdaq() -> dict:

    def exchange_from_symbol(symbol):
        if symbol == "Q":
            return "NASDAQ"
        if symbol == "A":
            return "NYSE MKT"
        if symbol == "N":
            return "NYSE"
        if symbol == "P":
            return "NYSE ARCA"
        if symbol == "Z":
            return "BATS"
        if symbol == "V":
            return "IEXG"
        return "n/a"

    tickers = {}

    filename = "nasdaqtraded.txt"
    ticker_column = 1
    etf_column = 5
    exchange_column = 3
    test_column = 7
    ftp = FTP("ftp.nasdaqtrader.com")
    ftp.login()
    ftp.cwd("SymbolDirectory")
    lines = StringIO()
    ftp.retrlines("RETR " + filename, lambda x: lines.write(str(x) + "\n"))
    ftp.quit()
    lines.seek(0)
    results = lines.readlines()

    for entry in results:
        sec = {}
        values = entry.split("|")
        ticker = values[ticker_column]
        if (
            re.match(r"^[A-Z]+$", ticker)
            and values[etf_column] == "N"
            and values[test_column] == "N"
        ):
            sec["ticker"] = ticker
            sec["sector"] = UNKNOWN
            sec["industry"] = UNKNOWN
            sec["universe"] = exchange_from_symbol(values[exchange_column])
            sec["marketCap"] = UNKNOWN
            tickers[sec["ticker"]] = sec

    return tickers

@staticmethod
def search_ticker_info(name) -> Ticket:
    
    def escape_ticker(ticker):
        return ticker.replace(".", "-")

    def get_info_from_dict(dict, key):
        value = dict[key] if key in dict else "n/a"
        # fix unicode
        if type(value) == str:
            value = value.replace("\u2014", " ")
            value = value.replace("â€”", " ")
            value = value.replace("-","")
            value = ' '.join(value.split())

        return value

    escaped_ticker = escape_ticker(name)
    
    try:
        info = yf.Ticker(escaped_ticker)

        ticket = Ticket(
            ticket=name,
            sector=get_info_from_dict(info.info, "sector"),
            industry=get_info_from_dict(info.info, "industry"),
            marketCap=get_info_from_dict(info.info, "marketCap"),
        )
    except:
        return None

    return ticket


def get_total_stocks_basic_info(marketCap = MARKET_CAP_10E,reuse_data = False) -> dict:
    """
    input : 
        1. marketCap : Set minimum stock market capitalization limit.

    return : 
        stock info
        1. marketCap
        2. Sector
        3. Industry
    """
    
    if reuse_data:
        return read_from_json(STOCK_INFO_JSON_PATH) 

    tickets=get_tickers_from_nasdaq()

    size = len(tickets)

    empty_list = []

    for idx, name in enumerate(tickets.keys()):

        print(f"process {name} info ({idx+1}/{size})")

        ticket = search_ticker_info(name=name)

        if ticket is None:
            continue

        tickets[name]["sector"] = ticket.sector
        tickets[name]["industry"] = ticket.industry
        tickets[name]["marketCap"] = ticket.marketCap
        if (
            ticket.sector == "n/a"
            or ticket.industry == "n/a"
            or ticket.marketCap == "n/a"
            or ticket.marketCap < marketCap
        ):
            empty_list.append(name)

        time.sleep(0.1)

    for name in empty_list:
        del tickets[name]

    save_to_json(data=tickets, json_file_path=STOCK_INFO_JSON_PATH)

    return tickets

@staticmethod
def load_prices_from_yahoo(
    ticket_name: str,
) -> candles_info:
    """
    load stocks price and save to json
    """
    df = yf.download(ticket_name, period= "max", auto_adjust=True)
    # yahoo_response = df.to_dict()
    # print(yahoo_response)

    # print(df['High']['AAPL'].tolist())
    # print(df['High']['AAPL'].index.tolist()[0].timestamp())

    timestamps = df['High'][ticket_name].index.tolist()
    timestamps = list(map(lambda timestamp: int(timestamp.timestamp()), timestamps))
    opens  = df['Open'][ticket_name].tolist()
    closes = df['Close'][ticket_name].tolist()
    lows = df['Low'][ticket_name].tolist()
    highs = df['High'][ticket_name].tolist()
    volumes = df['Volume'][ticket_name].tolist()


    # timestamps = list(yahoo_response.keys())
    # timestamps = list(map(lambda timestamp: int(timestamp.timestamp()), timestamps))
    # opens = list(yahoo_response["Open"].values())
    # closes = list(yahoo_response["Close"].values())
    # lows = list(yahoo_response["Low"].values())
    # highs = list(yahoo_response["High"].values())
    # volumes = list(yahoo_response["Volume"].values())
    return candles_info(
        opens=opens,
        closes=closes,
        lows=lows,
        highs=highs,
        volumes=volumes,
        timestamps=timestamps,
    )
    

def get_stock_history_price_data(tickets_info: dict,reuse_data = False) -> dict:
    '''
    download stock histroy price data (days)
    '''

    if reuse_data:
        return read_from_json(STOCK_PRICE_JSON_FILE)

    total_stocks = len(tickets_info.keys())

    all_candles = {}

    for idx, name in enumerate(tickets_info.keys()):
        print(f"load candles ({idx+1}/{total_stocks})")
        all_candles[name] = load_prices_from_yahoo(
            ticket_name=name,
        )._asdict()
        
        time.sleep(0.1)

    file_path = "candles.json"
    save_to_json(data=all_candles,json_file_path=file_path)
    return all_candles


def get_stock_option_data(ticket_name: str, type: str = "call") -> list:
    """
    Fetches option chain data (calls or puts) for a given stock symbol from Yahoo Finance.

    Parameters:
    ticket_name (str): The stock symbol (e.g., 'AAPL') for which to fetch options data.
    type (str): The type of options to fetch. It can be either 'call' or 'put'. Default is 'call'.

    Returns:
    list: A list of dataframes, each containing the option chain for a specific expiration date. 
          Each dataframe corresponds to either call or put options, depending on the 'type' parameter.
    None: If an error occurs while fetching the options data.
    """

    try:
        ticker = yf.Ticker(ticket_name)
        expiration_dates = ticker.options

        option_data_frames = []

        for expiration_date in expiration_dates:
            if type == "call":
                option_chain = ticker.option_chain(expiration_date).calls
            else:
                option_chain = ticker.option_chain(expiration_date).puts

            option_data_frames.append(option_chain)
    except Exception:
        return None

    return option_data_frames
