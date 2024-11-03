#!/bin/bash

cd /home/ponder/Icarus
python3 daily_run.py
python3 gen_rs_picture.py
python3 update_news.py
