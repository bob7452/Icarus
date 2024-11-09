import discord
from discord.ext import commands
# 設置 intents
intents = discord.Intents.default()  # 或者使用 discord.Intents.all() 獲取更多權限
intents.message_content = True  # 啟用接收訊息內容的權限
bot = commands.Bot(command_prefix='!', intents=intents)


import time
import pandas as pd
import os
from datetime import datetime
from file_io import read_from_json

ROOT = os.path.dirname(__file__)
TOKEN = os.path.join(ROOT,"token.json")
RS_REPORT = os.path.join(ROOT,"rs_report")
PICTURE_PATH = os.path.join(ROOT,"picture","rs_picture")

def get_picture_path():
    
    excels = []
    for file_name in os.listdir(RS_REPORT):
        excels.append(os.path.join(RS_REPORT,file_name))

    lastest_report = max(excels,key=os.path.getmtime)
    df = pd.read_csv(lastest_report)

    filtered_stocks = df[
        (df['close_to_high_10%'] == True) & 
        (df['powerful_than_spy'] == True) & 
        (df['group_powerful_than_spy'] == True) &
        (df['breakout_with_big_volume'] == True)
    ]

    stock_names = filtered_stocks['name'].to_list() 

    picpath = [os.path.join(PICTURE_PATH,f"{name}.png") for name in stock_names]

    return picpath


# 啟動事件
@bot.event
async def on_ready():
    print(f'已登入為 {bot.user}!')

@bot.command()
async def TodayStock(ctx):
    pictures = get_picture_path()

    for picture in pictures:
        pic = discord.File(picture)
        await ctx.send(file=pic)    



token_from_json = read_from_json(TOKEN) 
rebot_token = token_from_json['rebot_token']
bot.run(rebot_token)