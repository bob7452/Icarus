import requests
import json
import random
import time
import pandas as pd
import os
from datetime import datetime
from file_io import read_from_json

ROOT = os.path.dirname(__file__)
TOKEN = os.path.join(ROOT,"token.json")
RS_REPORT = os.path.join(ROOT,"rs_report")
PICTURE_PATH = os.path.join(ROOT,"picture","rs_picture")

def get_context():
    today = datetime.today().strftime("%Y-%m-%d")

    excels = []
    for file_name in os.listdir(RS_REPORT):
        excels.append(os.path.join(RS_REPORT,file_name))

    lastest_report = max(excels,key=os.path.getmtime)
    df = pd.read_csv(lastest_report)

    filtered_stocks = df[
        (df['close_to_high_10%'] == True) & 
        (df['powerful_than_spy'] == True) & 
        (df['group_powerful_than_spy'] == True)
        # (df['breakout_with_big_volume'] == True)
    ]

    return [f'============== {today} ---- SPILT LINE ---- {today} =============='] + filtered_stocks['name'].to_list() + [f'============== {today} ---- SPILT LINE ---- {today} =============='] + ["!TodayStock"]



def chat(chanel_list,authorization_list):
    stock_names = get_context()

    for authorization in authorization_list:
        header = {
            "Authorization": authorization,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36",
        }


        for chanel_id in chanel_list:
            for stock_name in stock_names:
                msg = {
                    "content": stock_name,
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
                    time.sleep(0.5)


if __name__ == "__main__":
    token_from_json = read_from_json(TOKEN) 

    chanel_list = ["1302051093596868658"]
    authorization_list = [token_from_json['discord_channel_token']]
    # while True:
    try:
        chat(chanel_list,authorization_list)
        # sleeptime = random.randrange(10, 30)
        # time.sleep(sleeptime)
    except Exception as e:
        print(f"error occur : {e}")
        # break
