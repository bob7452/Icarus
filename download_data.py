"""
File : technical_analysis.py
load s&p 500 and nasdaq companies
"""

import talib
import yfinance as yf
from datetime import date
import datetime as dt
from file_io import save_to_json, read_from_json
import pandas as pd
from collections import namedtuple
from dataclasses import dataclass

STOCK_PRICE_JSON_FILE = "stock_price_json_file.json"
PERIOD = 1 * 365 + 183
WEEKLY_52_BAR = 252


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

sliced_candle_info = namedtuple(
    "sliced_candle_info",
    [
        "opens",
        "closes",
        "lows",
        "highs",
        "volumes",
        "timestamps",
        "this_week",
    ],
)



def get_yf_data(ticket_name: str) -> dict:
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


def load_prices_from_yahoo(
    ticket_name: str,
) -> candles_info:
    """
    load stocks price and save to json
    """

    print("*** Loading Stocks from Yahoo Finance ***")
    return get_yf_data(ticket_name,)


history_price_group = namedtuple(
    "history_price_group",
    [
        "weekly_52_high",
        "weekly_52_low",
        "gap_from_the_last_high",
        "break_high",
        "break_low",
    ],
)

def history_price_search(candles: sliced_candle_info) -> history_price_group:
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
    )

    if break_high and break_low:
        return None

    return history
