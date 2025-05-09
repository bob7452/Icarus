import requests
import json
import random
import time
import pandas as pd
import os
from datetime import datetime
from file_io import read_from_json , read_lastest_news_report
from stock_rules import qualified_stocks
from collections import Counter

ROOT = os.path.dirname(__file__)
TOKEN = os.path.join(ROOT,"token.json")
RS_REPORT = os.path.join(ROOT,"rs_report")
PICTURE_PATH = os.path.join(ROOT,"picture","rs_picture")

def get_content():
    today = datetime.today().strftime("%Y-%m-%d")

    filtered_stocks = qualified_stocks()
    industry = filtered_stocks['industry_name'].to_list()
    industry_cnt = Counter(industry)    
    industry_summary = "\n".join(f"{industry_name} : {count}" for industry_name, count in industry_cnt.most_common())

    return [f'============== {today} ---- SPILT LINE ---- {today} =============='] \
    + filtered_stocks['name'].to_list() \
    + [f'============== {today} ---- Group Summary ---- {today} ==============']\
    + industry_summary.splitlines() \
    + [f'============== {today} ---- News Summary ---- {today} ==============']\
    + read_lastest_news_report()\
    + [f'============== {today} ---- SPILT LINE ---- {today} ==============']\
    + ["!TodayStock"]


def chat(contents:list):
    token_from_json = read_from_json(TOKEN) 
    chanel_list = ["1302051093596868658"]
    authorization_list = [token_from_json['discord_channel_token']]

    for authorization in authorization_list:
        header = {
            "Authorization": authorization,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36",
        }


        for chanel_id in chanel_list:
            for content in contents:
                msg = {
                    "content": content,
                    "nonce": "82329451214{}33232234".format(random.randrange(0, 1000)),
                    "tts": False,
                }

                url = "https://discord.com/api/v9/channels/{}/messages".format(chanel_id)
                try:
                    res = requests.post(url=url, headers=header, data=json.dumps(msg))
                    print(res.content)
                except Exception as e:
                    print(e)
                finally:
                    time.sleep(3)


if __name__ == "__main__":
    try:
        contents = get_content()
        chat(contents=contents)
    except Exception as e:
        print(f"error occur : {e}")

