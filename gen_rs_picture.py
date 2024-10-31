import yfinance as yf
import mplfinance as mpf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime, timedelta
import os
import shutil
import gc

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

    csv_data = pd.read_csv(lastest_report)

    stock = csv_data['name']
    total_count = len(stock)
    process = 0

    for idx,name in enumerate(stock):

            save_path = os.path.join(picture_path,name+".png")

            gen_pic(save_path,ticker=name)

            process+=1 
            print(f" total process ==== ({process} / {total_count}) ==== ")

