import pandas as pd
import numpy as np
import time
import datetime
from stock_rules import rs_above_90 , heat_rank_rs90
from file_io import read_stock_info_json , read_stock_price_json
from update_news import chat

HEADER = "###{},"
FORMAT = "{}:{},"

chatid = "1317996103643435058"


def send_to_chat(contents):
    chat(contents=contents,chanel_list=[chatid])
    time.sleep(0.5)

def is_today_saturday():
    return datetime.datetime.today().weekday() == 5


def check_stock_conditions(stock_name , timestamps, opens, highs, lows, closes, volumes, verbose=True):
    messages = []

    if not (len(timestamps) == len(opens) == len(highs) == len(lows) == len(closes) == len(volumes)):
        messages.append("❌ 資料長度不一致")
        return False, messages

    df = pd.DataFrame({
        'timestamp': timestamps,
        'Open': opens,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes
    })

    if len(df) < 15:
        messages.append(f"❌ 資料過少：僅 {len(df)} 天，需至少 15 天")
        return False, messages

    # 成交額
    period_turnover = min(30, len(df))
    df['Value'] = df['Close'] * df['Volume']
    df['AvgTurnover'] = df['Value'].rolling(window=period_turnover).mean()
    turnover_value = df['AvgTurnover'].iloc[-1]
    turnover_ok = turnover_value > 50000000

    # EMA乖離
    ema_span = min(10, len(df))
    df['EMA'] = df['Close'].ewm(span=ema_span, adjust=False).mean()
    ema = df['EMA'].iloc[-1]
    close = df['Close'].iloc[-1]
    bias = (close - ema) / ema * 100
    bias_ok = True #bias < 20.0

    # ATR
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift(1)).abs()
    tr3 = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    period_atr = min(14, len(df))
    df['ATR'] = tr.rolling(window=period_atr).mean()
    atr = df['ATR'].iloc[-1]
    atr_range = df['High'].iloc[-1] - df['Low'].iloc[-1]
    atr_ok = True #atr_range < 2.0 * atr

    # 52週高點差距
    high_lookback = min(252, len(df))
    df['RollingHigh'] = df['Close'].rolling(window=high_lookback).max()
    rolling_high = df['RollingHigh'].iloc[-1]
    if pd.isna(rolling_high) or rolling_high == 0:
        high_gap_ok = False
        gap = float('inf')
    else:
        gap = (rolling_high - close) / rolling_high * 100
        high_gap_ok = gap < 15.0

    is_pass = "PASS" if turnover_ok and bias_ok and atr_ok and high_gap_ok else "FAIL"

    # 組裝 messages
    messages.append(f"==== {stock_name} 技術條件細節 [{is_pass}] ====")
    messages.append(f"📊 平均成交額（{period_turnover}日）     : {turnover_value:,.0f} 元   → {'✔' if turnover_ok else '✘'} (門檻 50,000,000)")
    messages.append(f"📈 EMA乖離率（{ema_span}日）         : {bias:.2f}%        → {'✔' if bias_ok else '✘'} (門檻 20.0%)")
    messages.append(f"📉 ATR區間（{period_atr}日）         : {atr_range:.2f} vs {2.0 * atr:.2f} → {'✔' if atr_ok else '✘'} (2x ATR)")
    messages.append(f"🏔️ 52週高點差距（{high_lookback}日）: {gap:.2f}%        → {'✔' if high_gap_ok else '✘'} (門檻 <15%)")
    messages.append("======================")

    return turnover_ok and bias_ok and atr_ok and high_gap_ok, messages

def main():

    if is_today_saturday():
        print("今天是星期六！")
    else:
        print("今天不是星期六。")
        return

    stocks = rs_above_90()['name'].to_list()

    info = read_stock_info_json()
    price = read_stock_price_json()
    txt_words = ""
    group = {}



    with open("trading_view_list.txt",mode='w',) as file:
        for stock in stocks:

            timestamps = price[stock]["timestamps"]
            opens = price[stock]["opens"]
            highs = price[stock]["highs"]
            lows = price[stock]["lows"]
            closes = price[stock]["closes"]
            volumes = price[stock]["volumes"]

            is_pass , message = check_stock_conditions(stock_name=stock,
                                        timestamps=timestamps,
                                        opens=opens,
                                        highs=highs,
                                        lows=lows,
                                        closes=closes,
                                        volumes=volumes,)

            if not is_pass:
                print(message)
                #continue
            else:
                print(message)
                send_to_chat(message)

            industry : str = info[stock]["industry"]
            universe : str = info[stock]["universe"]
            universe = universe.replace('NYSE MKT','AMEX')

            if industry not in group:
                group[industry] = [FORMAT.format(universe,stock)]
            else:
                group[industry].append(FORMAT.format(universe,stock))
        

        for universe , stock in group.items():
            txt_words += HEADER.format(universe) + "".join(stock)
        file.write(txt_words)

if __name__ == "__main__":
    main()
