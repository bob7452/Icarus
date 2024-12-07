import requests
from bs4 import BeautifulSoup
import pandas as pd
from file_io import read_lastest_rs_report, read_lastest_rs_report_path, HEAT_REPORT , NEW_REPORT

def get_heat_ranks_and_news() -> tuple:
    # 目标网址
    url = "https://www.futunn.com/hk/quote/us/most-active-stocks"

    # 请求头 (伪装为浏览器)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    ranks = {}
    news_list = {}

    # 发起HTTP请求
    response = requests.get(url, headers=headers)

    # 检查响应状态
    if response.status_code == 200:
        # 解析HTML内容
        soup = BeautifulSoup(response.text, "html.parser")

        # 提取股票代码和热度排名
        list_items = soup.find_all("a", class_="list-item")
        for item in list_items:
            # 提取股票代码
            code = item.find("span", class_="code ellipsis")
            if code:
                code_text = code.get_text(strip=True)  # 提取并去除两端空白

            # 提取热度指数
            average_index = item.find("span", class_="ellipsis data-column data-column-averageIndex value-sort-column")
            if average_index:
                average_index_text = average_index.get_text(strip=True)
                
                # 存储到 ranks 字典
                ranks[code_text] = average_index_text

        # 提取新闻标题和链接
        news_items = soup.find_all("a", class_="news-title")  # 根据实际 HTML 结构调整类名
        for news_item in news_items:
            title = news_item.get_text(strip=True)
            link = news_item.get("href")
            print(f"{title} : {link}")
            news_list[title] = link

    else:
        print(f"请求失败，状态码：{response.status_code}")

    return ranks, news_list


if __name__ == "__main__":
    ranks, news_list = get_heat_ranks_and_news()

    # 处理热度排名数据
    heat_ranks = []
    for ticket, heat in ranks.items():
        tmp = {"ticket": ticket, "heat": int(heat)}
        df = pd.DataFrame(tmp, index=[0])
        heat_ranks.append(df)

    ALLDF = pd.concat(heat_ranks, ignore_index=True)
    ALLDF = ALLDF.sort_values(by='heat', ascending=False)
    ALLDF.to_csv(HEAT_REPORT, index=False)

    # 合并热度排名到最新报告
    rs_df = read_lastest_rs_report()
    rs_df['Heat'] = rs_df['name'].apply(lambda x: x in ranks)
    rs_df.to_csv(read_lastest_rs_report_path(), index=False)

    news = []
    for title , link in news_list.items():
        tmp = {"title":title,"link":link}
        df = pd.DataFrame(tmp,index=[0])
        news.append(df)

    ALLDF = pd.concat(news, ignore_index=True)
    ALLDF.to_csv(NEW_REPORT, index=False)

