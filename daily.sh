#!/bin/bash

cd /home/ponder/Icarus
python3 daily_run.py
if [ $? -ne 0 ]; then
    echo "Today is Holiday~~~"
    exit 1
fi
cp -f datasheet.csv ~/GoogleDrive/datasheet.csv
python3 heat_parser.py
python3 gen_rs_picture.py
python3 market_index.py
python3 mspi.py
python3 update_news.py
python3 tradingview_list.py
cp -f trading_view_list_over90.txt ~/GoogleDrive/trading_view_list_over90.txt
cp -f today_stock.txt ~/GoogleDrive/today_stock.txt
