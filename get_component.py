"""
File : get_component.py
load s&p 500 and nasdaq companies
"""

from collections import namedtuple
import requests
import bs4 as bs
import re
from ftplib import FTP
from io import StringIO
import yfinance as yf
from file_io import save_to_json, read_from_json
from datetime import date
import datetime as dt

UNKNOWN = "unknown"
INFO_JSON_PATH = "stock_info.json"

Ticket = namedtuple("Ticket", ["ticket", "sector", "industry"])


def get_securities(url, ticker_pos=1, table_pos=1, sector_offset=1, industry_offset=1):
    """
    parsing components from wiki
    """
    resp = requests.get(url, timeout=5)
    soup = bs.BeautifulSoup(resp.text, "lxml")
    table = soup.findAll("table", {"class": "wikitable sortable"})[table_pos - 1]
    secs = {}
    for row in table.findAll("tr")[table_pos:]:
        sec = Ticket(
            ticket=row.findAll("td")[ticker_pos - 1].text.strip(),
            sector=row.findAll("td")[ticker_pos - 1 + sector_offset].text.strip(),
            industry=row.findAll("td")[
                ticker_pos - 1 + sector_offset + industry_offset
            ].text.strip(),
        )
        secs[sec.ticket] = sec
    return secs


def get_tickers_from_wikipedia():
    """
    return components list
    """
    tickers = {}
    tickers.update(
        get_securities(
            "http://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            sector_offset=3,
        )
    )
    tickers.update(
        get_securities(
            "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
            2,
        )
    )
    tickers.update(
        get_securities(
            "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
            2,
        )
    )
    return tickers


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
            tickers[sec["ticker"]] = sec

    return tickers


def load_ticker_info(name) -> Ticket:

    def escape_ticker(ticker):
        return ticker.replace(".", "-")

    def get_info_from_dict(dict, key):
        value = dict[key] if key in dict else "n/a"
        # fix unicode
        value = value.replace("\u2014", " ")
        value = value.replace("â€”", " ")
        return value

    escaped_ticker = escape_ticker(name)
    info = yf.Ticker(escaped_ticker)

    ticket = Ticket(
        ticket=name,
        sector=get_info_from_dict(info.info, "sector"),
        industry=get_info_from_dict(info.info, "industry"),
    )
    # ticker_info = {
    #     "info": {
    #         "industry": get_info_from_dict(info.info, "industry"),
    #         "sector": get_info_from_dict(info.info, "sector")
    #     }
    # }
    return ticket


def insert_sector(tickets: dict):
    """
    insert stock info to dict
    """
    size = len(tickets)

    empty_list = []

    stock_info: dict = read_from_json(json_file_path=INFO_JSON_PATH)

    for idx, name in enumerate(tickets.keys()):

        print(f"process ({idx+1}/{size})")

        if name in stock_info:
            tickets[name]["sector"] = stock_info[name]["sector"]
            tickets[name]["industry"] = stock_info[name]["industry"]
        else:
            ticket = load_ticker_info(name=name)
            tickets[name]["sector"] = ticket.sector
            tickets[name]["industry"] = ticket.industry

            if ticket.sector == "n/a" or ticket.industry == "n/a":
                empty_list.append(name)

    for name in empty_list:
        del tickets[name]

    save_to_json(data=tickets, json_file_path=INFO_JSON_PATH)
    return tickets


def load_component() -> dict:
    """
    return component stock info
    """
    return insert_sector(tickets=get_tickers_from_nasdaq())


def get_yf_data(ticket_name: str, start_date, end_date) -> dict:
    ticker_data = {}
    df = yf.download(ticket_name, start=start_date, end=end_date, auto_adjust=True)
    yahoo_response = df.to_dict()
    timestamps = list(yahoo_response["Open"].keys())
    timestamps = list(map(lambda timestamp: int(timestamp.timestamp()), timestamps))
    opens = list(yahoo_response["Open"].values())
    closes = list(yahoo_response["Close"].values())
    lows = list(yahoo_response["Low"].values())
    highs = list(yahoo_response["High"].values())
    volumes = list(yahoo_response["Volume"].values())
    candles = []

    for i in range(0, len(opens)):
        candle = {}
        candle["open"] = opens[i]
        candle["close"] = closes[i]
        candle["low"] = lows[i]
        candle["high"] = highs[i]
        candle["volume"] = volumes[i]
        candle["datetime"] = timestamps[i]
        candles.append(candle)

    ticker_data["candles"] = candles
    return ticker_data


def load_prices_from_yahoo(ticket_name: dict) -> dict:
    """
    load stocks price and save to json
    """

    print("*** Loading Stocks from Yahoo Finance ***")
    today = date.today()
    start_date = today - dt.timedelta(days=1 * 365 + 183)  # 183 = 6 months
    bar_dict = {}
    ticker_data = get_yf_data(ticket_name, start_date, today)
    bar_dict[ticket_name] = ticker_data

    return bar_dict
