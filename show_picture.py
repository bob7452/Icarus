from PIL import Image
import os
import pandas as pd
import matplotlib.pyplot as plt
import subprocess
import time

def find_picture_pid(image_file) -> int:
    '''
        return picture pid 
    '''
    output = subprocess.run(f"ps aux | grep {image_file}.png", shell=True, capture_output=True, text=True)
    
    
    results = output.stdout.split('\n')

    for line in results:
        if 'eog' in line and f'{image_file}.png' in line:
            return  int(line.split()[1])
    return 0



if __name__ == "__main__":

    # 設定圖片資料夾的路徑
    folder_path = os.path.join(os.path.dirname("__file__"),"picture","rs_picture") 

    report_loc = os.path.dirname(__file__)
    report_loc = os.path.join(report_loc,"rs_report")

    excels = []
    for file_name in os.listdir(report_loc):
        excels.append(os.path.join(report_loc,file_name))

    lastest_report = max(excels,key=os.path.getmtime)

    print(lastest_report)
    data = pd.read_csv(lastest_report)
    image_files = data['name']

    for image_file in image_files:
        # 完整的圖片路徑
        image_path = os.path.join(folder_path, image_file+".png")
        
        subprocess.run(['xdg-open', image_path])

        pid_num = find_picture_pid(image_file)

        while find_picture_pid(image_file):
            time.sleep(0.1)