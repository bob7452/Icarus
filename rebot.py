import discord
from discord.ext import commands
# 設置 intents
intents = discord.Intents.default()  # 或者使用 discord.Intents.all() 獲取更多權限
intents.message_content = True  # 啟用接收訊息內容的權限
bot = commands.Bot(command_prefix='!', intents=intents)


import os
from file_io import read_from_json , read_lastest_heat_report
from stock_rules import qualified_stocks

ROOT = os.path.dirname(__file__)
TOKEN = os.path.join(ROOT,"token.json")
RS_REPORT = os.path.join(ROOT,"rs_report")
PICTURE_PATH = os.path.join(ROOT,"picture","rs_picture")
HEAT_REPORT = os.path.join(RS_REPORT,"heat_rank.csv")


def get_picture_path():
    
    filtered_stocks = qualified_stocks()
    stock_names = filtered_stocks['name'].to_list() 

    picpath = [(name,os.path.join(PICTURE_PATH,f"{name}.png")) for name in stock_names]

    return picpath


# 啟動事件
@bot.event
async def on_ready():
    print(f'已登入為 {bot.user}!')

@bot.command()
async def TodayStock(ctx):
    pictures = get_picture_path()
    heat = read_lastest_heat_report()

    for name,path in pictures:
        if not os.path.exists(path):
            continue
        if name in heat:
            await ctx.send(f"!!! {name} --- Today HEAT --- {name}!!!")
        pic = discord.File(path)
        await ctx.send(file=pic)    



token_from_json = read_from_json(TOKEN) 
rebot_token = token_from_json['rebot_token']
bot.run(rebot_token)