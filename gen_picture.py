import yfinance as yf
import mplfinance as mpf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import matplotlib
import os
import gc
import shutil

def gen_pic(save_path,ticker):
    # Download historical data for a given ticker symbol
    data = yf.download(ticker, period='5y', progress=False)

    # Filter data to show only the last 3 years
    end_date = data.index[-1]
    start_date = end_date - timedelta(days=int(3 * 252))
    data_filtered = data.loc[start_date:end_date]

    # Define the colors for each moving average line
    mav_colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown']

    # Set figure size to 1920x1080 pixels
    fig, ax = mpf.plot(data_filtered, type='candle', style='charles',
                    title=f'{ticker} Daily Candlestick Chart with MA (Last 3 Years)',
                    mav=(5, 20, 50, 100, 150, 200),
                    volume=True,
                    show_nontrading=False,
                    mavcolors=mav_colors,
                    figsize=(19.2, 10.8),  # width, height in inches
                    returnfig=True)

    # Add legend in the lower-right corner
    ma_labels = ['MA5', 'MA20', 'MA50', 'MA100', 'MA150', 'MA200']
    lines = [plt.Line2D([0], [0], color=color, linewidth=2) for color in mav_colors]
    ax[0].legend(lines, ma_labels, loc='lower right')

    # Specify the path where you want to save the fileh
    # Save the figure with higher resolution (e.g., 300 DPI)
    fig.savefig(save_path, dpi=300)

    fig.clf()
    plt.close(fig)
    del data, data_filtered, fig, ax, lines
    gc.collect()


def copy_png_files(src_dir, dest_dir):
    # 如果目的地資料夾不存在，則創建它
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    # 遍歷來源資料夾中的所有檔案
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            # 如果檔案是 .png 格式
            if file.endswith('.png'):
                # 生成完整路徑
                src_file_path = os.path.join(root, file)
                dest_file_path = os.path.join(dest_dir, file)
                
                # 複製檔案到目標資料夾
                shutil.copy2(src_file_path, dest_file_path)
                print(f"Copied: {src_file_path} -> {dest_file_path}")

if __name__ == "__main__":
    matplotlib.use('Agg')  # Use a non-interactive backend

    report_loc = os.path.dirname(__file__)
    report_loc = os.path.join(report_loc,"report")

    picture_path = os.path.join(os.path.dirname(__file__),"picture")
    if os.path.exists(picture_path):
        shutil.rmtree(picture_path)
    
    os.mkdir(picture_path)

    excels = []
    for file_name in os.listdir(report_loc):
        excels.append(os.path.join(report_loc,file_name))

    lastest_report = max(excels,key=os.path.getmtime)

    csv_data = pd.read_csv(lastest_report)

    industry_name = csv_data['industry_name']
    break_high_group = csv_data['break_high_group']
    approach_high = csv_data['approach_high']
    approach_count = csv_data['approach_count']

    total_count = sum(approach_count)
    process = 0

    for idx,industry in enumerate(industry_name):

        if isinstance(approach_high[idx],float):
            continue

        folder = os.path.join(os.path.dirname(__file__),"picture",industry)
        os.mkdir(folder)

        bh_folder = os.path.join(folder,"break_high")
        os.mkdir(bh_folder)

        approach_high_list : str = approach_high[idx]
        approach_high_list = approach_high_list.split(" ,")
        break_high_list : str = break_high_group[idx]
        
        if isinstance(break_high_list,float):
            break_high_list = ""
        else:
            break_high_list = break_high_list.split(" ,")

        print(approach_high_list)
        print(break_high_list)
        
        for high in approach_high_list:

            if high in break_high_list:
                save_path = os.path.join(bh_folder,f"{high}.png")            
            else:
                save_path = os.path.join(folder,f"{high}.png")

            print(save_path)

            gen_pic(save_path,ticker=high)

            process+=1 
            print(f" total process ==== ({process} / {total_count}) ==== ")


    path = os.path.dirname(__file__)

    src_directory = os.path.join(path,"picture") 
    dest_directory = os.path.join(path,"all")

    if os.path.exists(dest_directory):
        shutil.rmtree(dest_directory)
    
    os.mkdir(dest_directory)

    copy_png_files(src_directory, dest_directory)
