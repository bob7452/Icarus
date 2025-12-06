#!/bin/bash

cd /home/ponder/Icarus
python3 daily_option.py
python3 vix_term.py
python3 option_skew_plot.py

cp -f database/option_data.db ~/GoogleDrive/option_data.db
cp -f database/vix_data.db ~/GoogleDrive/vix_data.db
