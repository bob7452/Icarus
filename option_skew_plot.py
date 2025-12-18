import pandas as pd
from datetime import timedelta
from option.sql_lib import fetch_data_from_option_db
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np 
import os 
from datetime import datetime, timedelta
from pandas_market_calendars import get_calendar
import sys


# =================================================================
# STEP 1: Logic to find the nearest monthly expiration (Third Friday) - UNCHANGED
# =================================================================

def find_nearest_monthly_expiration(date):
    """
    Finds the first third Friday of a month that strictly occurs AFTER the given snapshot_date (date).
    This ensures the contract rolls to the next month if the snapshot date is on the current expiration.
    """
    
    def get_third_friday(d):
        """Helper function to find the 3rd Friday of the month of date 'd'."""
        # Start at the 1st day of the month
        d = d.replace(day=1)
        friday_count = 0
        while True:
            # 4 is Friday
            if d.weekday() == 4: 
                friday_count += 1
            if friday_count == 3:
                return d
            
            # Move to the next day
            d += timedelta(days=1)

    # 1. Calculate the 3rd Friday of the current month
    expiry_date = get_third_friday(date)
    
    # 2. Check if this expiration has passed or is today (expiry_date <= date)
    # if expiry_date <= date:
    # Roll to the next month's expiry.
    next_month_start = date.replace(day=28) + timedelta(days=4)
    next_month_start = next_month_start.replace(day=1)
    expiry_date = get_third_friday(next_month_start)
        
    return expiry_date


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
        target_exp_map[date] = find_nearest_monthly_expiration(pd.to_datetime(date).to_pydatetime())

    # Apply the target expiration date
    df['target_expiration'] = df['snapshot_date'].map(target_exp_map)

    # ----------------- STEP 3: Filter Data and Prepare for Plotting - MODIFIED -----------------

    # Filter for rows where expiration equals the target nearest monthly expiration
    result_df = df[df['expiration'] == df['target_expiration']].sort_values(by='snapshot_date').reset_index(drop=True)


    # =================================================================
    # ✅ MODIFIED STEP: Q95 & Q5 Calculation (Internal Only) and Q95 Alert Column (CSV Export)
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

    # Print Result (updated with only alert tags)
    print("\n" + "="*70)
    print("### 📉 Nearest Monthly Option Volatility Skew Changes (Q95 Alert Tags Only) ###")
    print("="*70)
    # 顯示將匯出至 CSV 的核心欄位和 Alert 欄位
    print(result_df[['snapshot_date', 'expiration'] + skew_cols + [f"{col}_Q95_Alert" for col in skew_cols]])
    print("\n" + "="*70)


    # =================================================================
    # ✅ STEP 4: Save Data to CSV File (Now only contains Skew values and Alert Tags)
    # =================================================================

    # Define file name
    filename = f"nearest_monthly_skew.csv"

    # 決定要匯出的欄位
    columns_to_export = ['snapshot_date', 'expiration', 'target_expiration'] + \
                        skew_cols + \
                        [f"{col}_Q95_Alert" for col in skew_cols]

    try:
        # Save CSV file, only including core data and the Q95 Alert tag
        result_df[columns_to_export].to_csv(filename, index=False)
        print(f"🎉 Data successfully saved to file: {os.path.abspath(filename)}")
    except Exception as e:
        print(f"❌ Error saving CSV file: {e}")

    # =================================================================
    # STEP 5: Plot Three Separate Time Series (Q95 Red, Q5 Dark Blue) - UNCHANGED LOGIC
    # =================================================================

    # Melt the skew columns for unified plotting format
    plot_df = result_df.melt(
        id_vars=['snapshot_date', 'expiration'], 
        value_vars=skew_cols, 
        var_name='Skew_Type', 
        value_name='Skew_Value'
    ).sort_values(by='snapshot_date') 

    # Define plot metrics
    metrics_to_plot = {
        'put_10delta_skew': {'color': '#1f77b4', 'label': 'Put 10-Delta Skew (Extreme OTM)', 'title': 'Put 10-Delta Skew Trend (Historical Extremes)'},
        'put_25delta_skew': {'color': '#ff7f0e', 'label': 'Put 25-Delta Skew (Mid OTM)', 'title': 'Put 25-Delta Skew Trend (Historical Extremes)'},
        'call_put_skew': {'color': '#2ca02c', 'label': 'Call-Put Skew', 'title': 'Call-Put Skew Trend (Historical Extremes)'}
    }

    # Find roll-over dates for annotation
    roll_over_dates = result_df['snapshot_date'][result_df['expiration'].shift(1) != result_df['expiration']].tolist()

    # Set plot style and create figure with three subplots, sharing the X-axis
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(16, 12), sharex=True)
    fig.suptitle('Volatility Skew Changes for Nearest Monthly Option (Continuous Rolling Contract)', fontsize=18, fontweight='bold')

    for i, (skew_type, params) in enumerate(metrics_to_plot.items()):
        ax = axes[i]
        
        # Filter data for the current skew type
        current_df = plot_df[plot_df['Skew_Type'] == skew_type]
        
        # Get the specific Q95 and Q05 values for this skew type
        q95_value = q95_values[skew_type]
        q05_value = q05_values[skew_type]
        
        # Plot the line (Continuous Curve)
        sns.lineplot(
            data=current_df, 
            x='snapshot_date', 
            y='Skew_Value', 
            color=params['color'], 
            estimator=None, 
            alpha=0.8,
            ax=ax
        )
        
        # Plot Zero Line
        ax.axhline(0, color='gray', linestyle=':', linewidth=1.0, alpha=0.7, label='Zero Line')
        
        # Plot Q95 Quantile Line (Upper Extreme - Red)
        ax.axhline(q95_value, color='#e31a1c', linestyle='--', linewidth=1.5, alpha=0.9, label=f'Q95 Panic ({q95_value:.4f})')
        
        # Plot Q05 Quantile Line (Lower Extreme - Dark Blue)
        ax.axhline(q05_value, color='#1f78b4', linestyle='--', linewidth=1.5, alpha=0.9, label=f'Q05 Complacency ({q05_value:.4f})')
        
        # Add Roll-over Annotations (Vertical Lines)
        for date in roll_over_dates:
            if date != result_df['snapshot_date'].min():
                ax.axvline(x=date, color='grey', linestyle='--', linewidth=1.0, alpha=0.5)

        # Set Title and Labels
        ax.set_title(params['title'], fontsize=14, loc='left')
        ax.set_ylabel(params['label'], fontsize=12)
        ax.set_xlabel('') # Clear X label for shared axis
        
        # Add legend
        #ax.legend(loc='lower right', fontsize=10)

    # Final adjustments for the shared X-axis (only the bottom chart gets the X label)
    axes[-1].set_xlabel('Snapshot Date', fontsize=14)
    plt.xticks(rotation=45, ha='right')

    fig.tight_layout(rect=[0, 0, 1, 0.98]) # Adjust layout
    #plt.show()
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
