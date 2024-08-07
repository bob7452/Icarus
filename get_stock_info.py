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
import os

UNKNOWN = "unknown"

STOCK_INFO_JSON_PATH = "stock_info.json"
STOCK_PRICE_JSON_FILE = "candles.json"

MARKET_CAP_1000E = 100_000_000_000
MARKET_CAP_100E = 10_000_000_000
MARKET_CAP_50E  = 5_000_000_000
MARKET_CAP_10E  = 1_000_000_000

Ticket = namedtuple("Ticket", ["ticket", "sector", "industry", "marketCap"])

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

        return value

    escaped_ticker = escape_ticker(name)
    info = yf.Ticker(escaped_ticker)

    ticket = Ticket(
        ticket=name,
        sector=get_info_from_dict(info.info, "sector"),
        industry=get_info_from_dict(info.info, "industry"),
        marketCap=get_info_from_dict(info.info, "marketCap"),
    )

    return ticket


def get_total_stocks_basic_info(marketCap = MARKET_CAP_10E) -> dict:
    """
    input : 
        1. marketCap : Set minimum stock market capitalization limit.

    return : 
        stock info
        1. marketCap
        2. Sector
        3. Industry
    """
    tickets=get_tickers_from_nasdaq()

    size = len(tickets)

    empty_list = []

    if os.path.exists(STOCK_INFO_JSON_PATH):
        stock_info: dict = read_from_json(json_file_path=STOCK_INFO_JSON_PATH)
    else:
        stock_info: dict = {}

    for idx, name in enumerate(tickets.keys()):

        print(f"process {name} info ({idx+1}/{size})")

        if name in stock_info:
            tickets[name]["sector"] = stock_info[name]["sector"]
            tickets[name]["industry"] = stock_info[name]["industry"]
            tickets[name]["marketCap"] = stock_info[name]["marketCap"]
        else:
            ticket = search_ticker_info(name=name)
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

    for name in empty_list:
        del tickets[name]

    save_to_json(data=tickets, json_file_path=STOCK_INFO_JSON_PATH)

    return tickets


import yfinance as yf
from collections import namedtuple
from file_io import save_to_json



candles_info = namedtuple(
    "candle_info",
    [
        "opens",
        "closes",
        "lows",
        "highs",
        "volumes",
        "timestamps",
    ],
)


@staticmethod
def load_prices_from_yahoo(
    ticket_name: str,
) -> candles_info:
    """
    load stocks price and save to json
    """
    df = yf.download(ticket_name, period= "5y", auto_adjust=True)
    yahoo_response = df.to_dict()
    timestamps = list(yahoo_response["Open"].keys())
    timestamps = list(map(lambda timestamp: int(timestamp.timestamp()), timestamps))
    opens = list(yahoo_response["Open"].values())
    closes = list(yahoo_response["Close"].values())
    lows = list(yahoo_response["Low"].values())
    highs = list(yahoo_response["High"].values())
    volumes = list(yahoo_response["Volume"].values())
    return candles_info(
        opens=opens,
        closes=closes,
        lows=lows,
        highs=highs,
        volumes=volumes,
        timestamps=timestamps,
    )
    

def get_stock_history_price_data(tickets_info: dict) -> dict:
    '''
    download stock histroy price data (days)
    '''

    total_stocks = len(tickets_info.keys())

    all_candles = {}

    for idx, name in enumerate(tickets_info.keys()):
        print(f"load candles ({idx+1}/{total_stocks})")
        all_candles[name] = load_prices_from_yahoo(
            ticket_name=name,
        )._asdict()

    file_path = "candles.json"
    save_to_json(data=all_candles,json_file_path=file_path)
    return all_candles
