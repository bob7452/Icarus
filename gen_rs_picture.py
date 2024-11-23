import yfinance as yf
import mplfinance as mpf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from file_io import read_from_json
import os
import shutil
import gc

def gen_pic(save_path,ticker):
    # Download historical data for a given ticker symbol
    data = yf.download(ticker, period='ytd', progress=False)

    data_dict = {
        "Adj Close" : data['Adj Close'][ticker].tolist(),
        "Close" : data['Close'][ticker].tolist(),
        "High" : data['High'][ticker].tolist(),
        "Low" : data['Low'][ticker].tolist(),
        "Open" : data['Open'][ticker].tolist(),
        "Volume" : data['Volume'][ticker].tolist(),
    }

    data_filtered = pd.DataFrame(data=data_dict)
    data_filtered.index = data['High'][ticker].index.tolist()
    

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

if __name__ == "__main__":
    
    matplotlib.use('Agg')  # Use a non-interactive backend


    report_loc = os.path.dirname(__file__)
    report_loc = os.path.join(report_loc,"rs_report")

    picture_path = os.path.join(os.path.dirname(__file__),"picture","rs_picture")
    if os.path.exists(picture_path):
        shutil.rmtree(picture_path)
    
    os.mkdir(picture_path)

    excels = []
    for file_name in os.listdir(report_loc):
        excels.append(os.path.join(report_loc,file_name))

    lastest_report = max(excels,key=os.path.getmtime)

    df = pd.read_csv(lastest_report)

    filtered_stocks = df[
        (df['close_to_high_10%'] == True) & 
        (df['powerful_than_spy'] == True) & 
        (df['group_powerful_than_spy'] == True) &
        (df['breakout_with_big_volume'] == True)
    ]

    stock = filtered_stocks['name'].to_list() 

    total_count = len(stock)
    process = 0

    candles = read_from_json("candles.json")

    for idx,name in enumerate(stock):

            save_path = os.path.join(picture_path,name+".png")

            gen_pic(save_path,ticker=name)

            process+=1 
            print(f" total process ==== ({process} / {total_count}) ==== ")

