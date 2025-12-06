import sqlite3
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import numpy as np

# Define the database path
VIX_DB_PATH = Path(__file__).parent / "database" / "vix_data.db" 
# Define the path for the output CSV file
CSV_OUTPUT_PATH = Path(__file__).parent / "vix_spread_with_flags.csv"

def plot_vix_term_summary():
    # === Step 1: Retrieve Data from the Database ===
    try:
        # Establish connection
        conn = sqlite3.connect(VIX_DB_PATH)
        cursor = conn.cursor()

        # Execute SQL query: retrieve date and spread_vix_vix3m
        cursor.execute("""
            SELECT date, spread_vix_vix3m
            FROM vix_term_structure
            ORDER BY date
        """)
        
        # Fetch all results
        data = cursor.fetchall()
        
        # Close connection
        conn.close()

    except sqlite3.Error as e:
        print(f"Database operation error: {e}")
        data = []

    # Check if data exists
    if not data:
        print("No VIX Spread data found in the database or connection failed.")
    else:
        # Convert data to a Pandas DataFrame
        df = pd.DataFrame(data, columns=['Date', 'Spread'])
        
        # Convert 'Date' column to datetime objects
        df['Date'] = pd.to_datetime(df['Date'])
        
        # === Step 2: Calculate Q95 and Q5 Percentiles & Set Flags ===
        spread_values = df['Spread'].values
        
        # Calculate the 95th percentile (Q95) and 5th percentile (Q5)
        q95 = np.percentile(spread_values, 95)
        q5 = np.percentile(spread_values, 5)

        print(f"95th Percentile (Q95): {q95:.4f}")
        print(f"5th Percentile (Q5): {q5:.4f}")
        
        # Create the 'Flag' column
        def set_flag(spread):
            if spread >= q95:
                return 'Extreme Backwardation (Fear/Q95+)'
            elif spread <= q5:
                return 'Extreme Contango (Calm/Q5-)'
            else:
                return 'Normal'

        # Apply the function to create the new column
        df['Flag'] = df['Spread'].apply(set_flag)

        # === Step 3: Save Data to CSV ===
        df.to_csv(CSV_OUTPUT_PATH, index=False)
        print(f"\nSuccessfully saved data with flags to: {CSV_OUTPUT_PATH.resolve()}")

        # === Step 4: Plot the Data using Matplotlib (Same as before) ===
        plt.figure(figsize=(12, 6))
        
        plt.plot(df['Date'], df['Spread'], marker='o', linestyle='-', markersize=2, label='VIX - VIX3M Spread')
        
        # Plot Q95 line (Red dashed line)
        plt.axhline(q95, color='r', linestyle='--', linewidth=2, label=f'Q95: {q95:.2f} (Extreme Backwardation)')
        
        # Plot Q5 line (Blue dashed line)
        plt.axhline(q5, color='b', linestyle='--', linewidth=2, label=f'Q5: {q5:.2f} (Extreme Contango)')
        
        # Title and labels
        plt.title('VIX Term Structure Spread (VIX - VIX3M) Time Series', fontsize=16)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('VIX - VIX3M Spread Value', fontsize=12)
        
        # Add grid lines
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Add legend
        plt.legend()
        
        # Adjust X-axis ticks
        plt.gcf().autofmt_xdate()
        
        # Display the chart
        plt.tight_layout()
        plt.savefig("vix_term_summary.png")

if __name__ == "__main__":
    plot_vix_term_summary()