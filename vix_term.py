import sqlite3
from pathlib import Path
import yfinance as yf
from datetime import datetime
from pandas_market_calendars import get_calendar
import sys
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from update_news import chat


VIX_DB = Path(__file__).parent / "database" / "vix_data.db"

def is_holiday(date: datetime) -> bool:
    nyse = get_calendar('NYSE')
    valid_days = nyse.valid_days(start_date=date, end_date=date)
    return valid_days.empty

def fetch_vix_term_structure():
    symbols = {
        "vix9d": "^VIX9D",
        "vix": "^VIX",
        "vix3m": "^VIX3M",
        "vix6m": "^VIX6M",
        "vix1y": "^VIX1Y"
    }
    result = {}
    for name, symbol in symbols.items():
        try:
            data = yf.Ticker(symbol).history(period="1d", interval="1d")
            price = data.iloc[-1]['Close']
            result[name] = price
        except Exception as e:
            print(f"Error fetching {name}: {e}")
            result[name] = None
    return result

def main(date : str):
    # === 建立連線
    conn = sqlite3.connect(VIX_DB.resolve())
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vix_term_structure (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL UNIQUE,
        vix9d REAL,
        vix REAL,
        vix3m REAL,
        vix6m REAL,
        vix1y REAL,
        spread_vix_vix3m REAL
    )
    """)

    term_structure = fetch_vix_term_structure()
    for name, price in term_structure.items():
        print(f"{name}: {price:.2f}" if price else f"{name}: N/A")

    # === 填入今天要存的資料
    vix_data = fetch_vix_term_structure()
    vix_data["date"] = date

    # === 自動計算 Spread
    spread = vix_data["vix"] - vix_data["vix3m"]


    # === 插入資料
    cursor.execute("""
    INSERT INTO vix_term_structure (date, vix9d, vix, vix3m, vix6m, vix1y, spread_vix_vix3m)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        vix_data["date"],
        vix_data["vix9d"],
        vix_data["vix"],
        vix_data["vix3m"],
        vix_data["vix6m"],
        vix_data["vix1y"],
        spread
    ))

    conn.commit()
    conn.close()

def plot_vix_term():
    # === 設定參數 ===
    SLOPE_WARNING_THRESHOLD = 0.2  # Spread每日加速斜率警戒線
    SPREAD_LEVELS = {
        "normal": (float('-inf'), 1.0),
        "caution": (1.0, 3.0),
        "warning": (3.0, 5.0),
        "danger": (5.0, float('inf'))
    }
    SPREAD_COLORS = {
        "normal": "black",
        "caution": "orange",
        "warning": "red",
        "danger": "darkred"
    }

    # === 連接資料庫並撈資料 ===
    conn = sqlite3.connect(VIX_DB)
    df = pd.read_sql_query("""
    SELECT date, vix, vix3m FROM vix_term_structure
    ORDER BY date DESC
    LIMIT 7
    """, conn)
    conn.close()

    # === 整理資料順序
    df = df.sort_values(by='date')

    # === 防呆：資料不足直接跳出
    if len(df) < 2:
        print(f"❌ 資料不足，目前只有 {len(df)} 筆，至少需要 2 筆資料才能分析！")
        exit()

    # === 計算 Spread（VIX - VIX3M）
    df['spread'] = df['vix'] - df['vix3m']

    # === 計算 Spread 斜率（加速率）
    df['date_numeric'] = pd.to_datetime(df['date']).map(lambda x: (x - pd.to_datetime(df['date'].iloc[0])).days)
    slope, intercept = np.polyfit(df['date_numeric'], df['spread'], 1)

    # === 判斷當天 Spread 等級
    today_spread = df.iloc[-1]['spread']
    def classify_spread(spread_value):
        for level, (lower, upper) in SPREAD_LEVELS.items():
            if lower < spread_value <= upper:
                return level
        return "unknown"

    today_level = classify_spread(today_spread)
    color = SPREAD_COLORS.get(today_level, "black")

    # === VIX 當日與前一日的變化
    vix_today = df.iloc[-1]['vix']
    vix_yesterday = df.iloc[-2]['vix']
    delta_vix = vix_today - vix_yesterday
    vix_trend = "↑" if delta_vix > 0 else "↓" if delta_vix < 0 else "→"

    # === 畫圖
    plt.figure(figsize=(12, 6))

    # 畫Spread線
    plt.plot(df['date'], df['spread'], marker='o', label='Spread (VIX - VIX3M)', color=color)
    # 畫趨勢虛線
    plt.plot(df['date'], slope * df['date_numeric'] + intercept, linestyle='--', label=f"Trend Line (slope={slope:.2f} pt/day)", color="gray")

    # 畫基準線
    plt.axhline(0, color='black', linewidth=0.8)

    # 標題、副標題
    title_text = f"7-Day VIX Spread Trend (VIX - VIX3M)\nToday Level: {today_level.upper()}"
    if len(df) < 7:
        title_text += "  ⚠️ (data < 7days)"
    plt.title(title_text, color=color, fontsize=16)

    # 顯示 VIX 當日變化
    vix_info = f"VIX: {vix_today:.2f} ({vix_trend}{abs(delta_vix):.2f} vs yesterday)"
    plt.figtext(0.5, 0.95, vix_info, wrap=True, horizontalalignment='center', fontsize=11, color='blue')

    plt.xlabel("Date")
    plt.ylabel("Spread")
    plt.grid(True)
    plt.legend()

    # === 底部加註警示或資訊
    if slope > SLOPE_WARNING_THRESHOLD:
        warning_text = f"⚠️ Spread accelerating: slope={slope:.2f} pt/day"
        plt.figtext(0.5, 0.01, warning_text, wrap=True, horizontalalignment='center', color='red', fontsize=12)
    else:
        info_text = f"Spread trend slope: {slope:.2f} pt/day"
        plt.figtext(0.5, 0.01, info_text, wrap=True, horizontalalignment='center', color='black', fontsize=10)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig("vix_term.png")
   


if __name__ == "__main__":
    process_day = datetime.today()
    if is_holiday(process_day):
        print(f"[{process_day}] is a holiday. Skipping.")
        sys.exit(1)
    today_str = process_day.strftime("%Y-%m-%d")
    main(today_str)
    plot_vix_term()
    chat(contents=["!TodayVixTerm"])
