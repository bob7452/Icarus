import requests
from bs4 import BeautifulSoup
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def get_heat_ranks()->list:
    # 目标网址
    url = "https://www.futunn.com/hk/quote/us/most-active-stocks"

    # 请求头 (伪装为浏览器)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    ranks = []

    # 发起HTTP请求
    response = requests.get(url, headers=headers)

    # 检查响应状态
    if response.status_code == 200:
        # 解析HTML内容
        soup = BeautifulSoup(response.text, "html.parser")
        
        list_items = soup.find_all("a", class_="list-item")

        for item in list_items:
            # 提取 `code ellipsis` 的内容
            code = item.find("span", class_="code ellipsis")
            if code:
                code_text = code.get_text(strip=True)  # 提取并去除两端空白
                print(f"Code: {code_text}")

            # 提取 `ellipsis data-column data-column-averageIndex value-sort-column` 的内容
            average_index = item.find("span", class_="ellipsis data-column data-column-averageIndex value-sort-column")
            if average_index:
                average_index_text = average_index.get_text(strip=True)
                print(f"Average Index: {average_index_text}")

            ranks+=[(code_text,average_index_text)]

    else:
        print(f"请求失败，状态码：{response.status_code}")


    return ranks


if __name__ == "__main__":
    ranks = get_heat_ranks()
    heat_report_path = os.path.join(os.path.dirname(__file__),"rs_report","heat_rank.csv")

    heat_ranks = []
    for ticket,heat in ranks:
        tmp = {"ticket" : ticket,
               "heat" : int(heat),}
        df = pd.DataFrame(tmp, index=[0])
        heat_ranks.append(df)

        ALLDF = pd.concat(heat_ranks, ignore_index=True)
        ALLDF = ALLDF.sort_values(by='heat',ascending=False)
        ALLDF.to_csv(heat_report_path,index=False)