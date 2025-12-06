#!/bin/bash

cd /home/ponder/Icarus
python3 daily_option.py

cp -f database/option_data.db ~/GoogleDrive/option_data.db

