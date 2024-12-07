import os
import json
import pandas as pd
ROOT = os.path.dirname(__file__)
RS_REPORT = os.path.join(ROOT,"rs_report")
HEAT_REPORT = os.path.join(RS_REPORT,"heat_rank.csv")
NEW_REPORT = os.path.join(RS_REPORT,"new.csv")


def read_from_json(json_file_path: str) -> None:
    """
    read json data
    """

    with open(file=json_file_path, mode="r") as file:
        data = json.load(file)

    return data


def save_to_json(data: dict, json_file_path) -> None:
    """
    save stock info to json
    """

    if os.path.exists(json_file_path):
        os.remove(path=json_file_path)

    with open(file=json_file_path, mode="w") as file:
        json.dump(data, file)

def read_lastest_rs_report()->pd.DataFrame:
    excels = []
    for file_name in os.listdir(RS_REPORT):
        if file_name.startswith("rs_model"):
            excels.append(os.path.join(RS_REPORT,file_name))

    lastest_report = max(excels,key=os.path.getmtime)

    return pd.read_csv(lastest_report)

def read_lastest_rs_report_path()->str:
    excels = []
    for file_name in os.listdir(RS_REPORT):
        if file_name.startswith("rs_model"):
            excels.append(os.path.join(RS_REPORT,file_name))

    lastest_report = max(excels,key=os.path.getmtime)

    return lastest_report

def read_lastest_heat_report()->pd.DataFrame:
    heats = pd.read_csv(HEAT_REPORT)
    return heats['ticket'].to_list()

def read_lastest_news_report() -> list[str]:
    news = pd.read_csv(NEW_REPORT)
    
    title = news['title'].to_list()
    link  = news['link'].to_list()

    message = []
    for t , l in zip(title,link):
        message.append(f"{t}\n{l}")

    return message