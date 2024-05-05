import os
import json

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