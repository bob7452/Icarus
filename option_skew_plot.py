import pandas as pd
from datetime import timedelta, datetime
from option.sql_lib import fetch_data_from_option_db
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np 
import os 
from pandas_market_calendars import get_calendar
import sys


# =================================================================
# STEP 1: Logic to find the NEXT monthly expiration (下下個月的第三個週五)
# =================================================================

def find_next_monthly_expiration(date):
    """
    找出給定日期之後的「第二個」第三週星期五（下下個月的結算日）。
    如果遇到假日，結算日會自動提前一天到週四。
    """
    nyse = get_calendar('NYSE')
    
    def get_third_friday(d):
        """Helper function to find the 3rd Friday of the month of date 'd'."""
        d = d.replace(day=1)
        friday_count = 0
        while True:
            if d.weekday() == 4: # 4 is Friday
                friday_count += 1
            if friday_count == 3:
                # 檢查這天是否為假日
                valid_days = nyse.valid_days(start_date=d, end_date=d)
                if valid_days.empty:
                    # 如果週五休市，提前一天到週四
                    return d - timedelta(days=1)
                return d
            d += timedelta(days=1)

    # 1. 取得當月的第三個星期五
    nearest_expiry = get_third_friday(date)
    
    # 2. 確保找到的是「未來」的最近結算日
    if nearest_expiry <= date:
        next_month_start = date.replace(day=28) + timedelta(days=4)
        next_month_start = next_month_start.replace(day=1)
        nearest_expiry = get_third_friday(next_month_start)
        
    # 3. 往下一一個月尋找 (目標：下下個月的結算日)
    target_month_start = nearest_expiry.replace(day=28) + timedelta(days=4)
    target_month_start = target_month_start.replace(day=1)
    target_expiry = get_third_friday(target_month_start)
    
    return target_expiry


def run_skew_plot():

    # ⚠️ Note: Assuming fetch_data_from_option_db runs successfully
    df = fetch_data_from_option_db("SELECT * FROM skew_snapshot")

    # 1. Ensure date columns are datetime objects
    df['snapshot_date'] = pd.to_datetime(df['snapshot_date'])
    df['expiration'] = pd.to_datetime(df['expiration'])

    # 2. Remove time component from snapshot_date
    df['snapshot_date'] = df['snapshot_date'].dt.normalize()

    # 3. Find target expiration for each snapshot date
    unique_snapshots = df['snapshot_date'].unique()
    target_exp_map = {}
    for date in unique_snapshots:
        # ✅ 呼叫更新後的 find_next_monthly_expiration
        target_exp_map[date] = find_next_monthly_expiration(pd.to_datetime(date).to_pydatetime())

    # Apply the target expiration date
    df['target_expiration'] = df['snapshot_date'].map(target_exp_map)

    # ----------------- STEP 3: Filter Data and Prepare for Plotting -----------------

    # Filter for rows where expiration equals the target next monthly expiration
    result_df = df[df['expiration'] == df['target_expiration']].sort_values(by='snapshot_date').reset_index(drop=True)


    # =================================================================
    # STEP: Q95 & Q5 Calculation (Internal Only) and Q95 Alert Column
    # =================================================================

    # Define skew columns
    skew_cols = ['put_10delta_skew', 'put_25delta_skew', 'call_put_skew']

    # 1. Calculate Q95 AND Q5 for internal use (plotting)
    q95_values = result_df[skew_cols].quantile(0.95).to_dict()
    q05_values = result_df[skew_cols].quantile(0.05).to_dict() 

    # 2. Add Q95 Alert tag column to result_df for CSV export
    for col in skew_cols:
        q95_val = q95_values[col]
        alert_col_name = f"{col}_Q95_Alert"
        
        # 標記超過 Q95 為 'Panic Alert'，其餘為空
        result_df[alert_col_name] = np.where(result_df[col] > q95_val, 'Panic Alert', '')

    # Print Result 
    print("\n" + "="*70)
    print("### 📉 Next Monthly Option Volatility Skew Changes (Q95 Alert Tags Only) ###")
    print("="*70)
    print(result_df[['snapshot_date', 'expiration'] + skew_cols + [f"{col}_Q95_Alert" for col in skew_cols]])
    print("\n" + "="*70)


    # =================================================================
    # STEP 4: Save Data to CSV File
    # =================================================================

    # ✅ 改檔名為 next_monthly_skew.csv 避免覆蓋舊檔
    filename = f"next_monthly_skew.csv"

    columns_to_export = ['snapshot_date', 'expiration', 'target_expiration'] + \
                        skew_cols + \
                        [f"{col}_Q95_Alert" for col in skew_cols]

    try:
        result_df[columns_to_export].to_csv(filename, index=False)
        print(f"🎉 Data successfully saved to file: {os.path.abspath(filename)}")
    except Exception as e:
        print(f"❌ Error saving CSV file: {e}")

    # =================================================================
    # STEP 5: Plot Three Separate Time Series (Q95 Red, Q5 Dark Blue)
    # =================================================================

    plot_df = result_df.melt(
        id_vars=['snapshot_date', 'expiration'], 
        value_vars=skew_cols, 
        var_name='Skew_Type', 
        value_name='Skew_Value'
    ).sort_values(by='snapshot_date') 

    metrics_to_plot = {
        'put_10delta_skew': {'color': '#1f77b4', 'label': 'Put 10-Delta Skew (Extreme OTM)', 'title': 'Put 10-Delta Skew Trend (Historical Extremes)'},
        'put_25delta_skew': {'color': '#ff7f0e', 'label': 'Put 25-Delta Skew (Mid OTM)', 'title': 'Put 25-Delta Skew Trend (Historical Extremes)'},
        'call_put_skew': {'color': '#2ca02c', 'label': 'Call-Put Skew', 'title': 'Call-Put Skew Trend (Historical Extremes)'}
    }

    roll_over_dates = result_df['snapshot_date'][result_df['expiration'].shift(1) != result_df['expiration']].tolist()

    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(16, 12), sharex=True)
    
    # ✅ 標題更新為 Next Monthly Option
    fig.suptitle('Volatility Skew Changes for Next Monthly Option (Continuous Rolling Contract)', fontsize=18, fontweight='bold')

    for i, (skew_type, params) in enumerate(metrics_to_plot.items()):
        ax = axes[i]
        
        current_df = plot_df[plot_df['Skew_Type'] == skew_type]
        q95_value = q95_values[skew_type]
        q05_value = q05_values[skew_type]
        
        sns.lineplot(
            data=current_df, 
            x='snapshot_date', 
            y='Skew_Value', 
            color=params['color'], 
            estimator=None, 
            alpha=0.8,
            ax=ax
        )
        
        ax.axhline(0, color='gray', linestyle=':', linewidth=1.0, alpha=0.7, label='Zero Line')
        ax.axhline(q95_value, color='#e31a1c', linestyle='--', linewidth=1.5, alpha=0.9, label=f'Q95 Panic ({q95_value:.4f})')
        ax.axhline(q05_value, color='#1f78b4', linestyle='--', linewidth=1.5, alpha=0.9, label=f'Q05 Complacency ({q05_value:.4f})')
        
        for date in roll_over_dates:
            if date != result_df['snapshot_date'].min():
                ax.axvline(x=date, color='grey', linestyle='--', linewidth=1.0, alpha=0.5)

        ax.set_title(params['title'], fontsize=14, loc='left')
        ax.set_ylabel(params['label'], fontsize=12)
        ax.set_xlabel('') 

    axes[-1].set_xlabel('Snapshot Date', fontsize=14)
    plt.xticks(rotation=45, ha='right')

    fig.tight_layout(rect=[0, 0, 1, 0.98])
    
    # ✅ 圖片存檔名稱也更新避免覆蓋舊圖
    plt.savefig("option_skew_summary.png")


def is_holiday(date: datetime) -> bool:
    nyse = get_calendar('NYSE')
    valid_days = nyse.valid_days(start_date=date, end_date=date)
    return valid_days.empty

if __name__ == "__main__":

    process_day = datetime.today()
    if is_holiday(process_day):
        print(f"[{process_day}] is a holiday. Skipping.")
        sys.exit(1)

    run_skew_plot()
