import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler

def calculate_bear_risk_index(df):
    """
    計算並正則化熊市風險指數 (Bear Market Risk Index)
    
    :param df: DataFrame，需包含 'ath_count' 和 'atl_count' 列
    :return: DataFrame，附加 'bear_risk_index' 列
    """
    WINDOWS = 5 # 移動平均視窗大小
    df['ath_ma'] = df['ath_count'].rolling(window=WINDOWS).mean()
    df['atl_ma'] = df['atl_count'].rolling(window=WINDOWS).mean()
    df['ath_std'] = df['ath_count'].rolling(window=WINDOWS).std()
    df['atl_std'] = df['atl_count'].rolling(window=WINDOWS).std()

    # 避免 NaN 值影響計算
    df.fillna(0, inplace=True)

    # 計算風險指數
    df['bear_risk_index'] = (df['atl_ma'] * df['atl_std']) / (df['ath_ma'] + 1)

    # 正則化風險指數 (0~1 之間)
    scaler = MinMaxScaler()
    df['bear_risk_index'] = scaler.fit_transform(df[['bear_risk_index']])

    return df

def plot_bear_risk_index(df):
    """
    繪製熊市風險指數趨勢圖，並在副軸上繪製 ATH 計數，避免 x 軸重複
    
    :param df: DataFrame，需包含 'start_date', 'bear_risk_index', 和 'ath_count' 列
    """
    fig, ax1 = plt.subplots(figsize=(15,6))

    # 主軸：熊市風險指數
    ax1.plot(df['start_date'], df['bear_risk_index'], label='Bear Market Risk Index', color='purple')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Normalized Risk Index', color='purple')
    ax1.tick_params(axis='y', labelcolor='purple')
    ax1.set_title('Normalized Bear Market Risk Index and ATH Count Over Time')
    ax1.grid(True)

    # 副軸：ATH 計數
    ax2 = ax1.twinx()
    ax2.plot(df['start_date'], df['ath_count'], label='ATH Count', color='orange', linestyle='dashed')
    ax2.set_ylabel('ATH Count', color='orange')
    ax2.tick_params(axis='y', labelcolor='orange')

    # 讓副軸共享 x 軸，但不重複顯示
    ax2.get_xaxis().set_visible(False)

    # 避免日期重疊
    ax1.set_xticks(df['start_date'][::len(df)//10])  # 只顯示 10 個間距的日期
    plt.xticks(rotation=45)

    # 圖例
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')

    #plt.show()
    plt.savefig("market_index.png")

def plot_ath_atl_data(df):

    # 轉換日期欄位
    df["start_date"] = pd.to_datetime(df["start_date"])

    # 繪製雙軸圖
    fig, ax1 = plt.subplots(figsize=(12, 6))

    color_ath = 'tab:blue'
    color_atl = 'tab:red'

    # 主軸: ath_count
    ax1.set_xlabel('Date')
    ax1.set_ylabel('ATH Count', color=color_ath)
    ax1.plot(df["start_date"], df["ath_count"], color=color_ath, label='ATH Count')
    ax1.tick_params(axis='y', labelcolor=color_ath)

    # 副軸: atl_count
    ax2 = ax1.twinx()
    ax2.set_ylabel('ATL Count', color=color_atl)
    ax2.plot(df["start_date"], df["atl_count"], color=color_atl, label='ATL Count')
    ax2.tick_params(axis='y', labelcolor=color_atl)

    plt.title('ATH vs ATL Count Over Time')
    plt.grid(True)
    # plt.tight_layout()
    # plt.show()
    plt.savefig("ath_atl_data.png")

def calculate_bear_risk_index(df):
    """
    這個函數是您環境中自定義的，在此處僅作為佔位符。
    請確保它返回一個 DataFrame，且包含 'start_date', 'ath_count', 'atl_count'。
    """
    # 假設它在 DataFrame 中加入了一些新的欄位或計算
    # 為了演示，我們在這裡加入一個簡單的檢查
    if 'start_date' not in df.columns:
         raise ValueError("DataFrame 缺少 'start_date' 欄位。")
    print("已執行 calculate_bear_risk_index 函數。")
    return df

def plot_weekly_ath_atl_data():
    
    # --- 步驟 0: 資料載入與處理 ---
    try:
        # --------------------------------------------------------
        # 請使用以下程式碼來載入您的真實數據
        df = pd.read_csv("datasheet.csv")

        # --------------------------------------------------------
        
    except FileNotFoundError:
        print("錯誤：找不到 datasheet.csv 文件。請確保檔案位於正確路徑。")
        return
    except ValueError as e:
        print(f"錯誤：calculate_bear_risk_index 函數出錯：{e}")
        return
    
    # 確保 'start_date' 是 datetime 格式
    df["start_date"] = pd.to_datetime(df["start_date"])
    
    # 如果您只想要週一到週五的數據總和，請取消註釋下面一行：
    # df = df[df['start_date'].dt.weekday < 5].copy() 

    # --- 步驟 1: 彙總成週資料 (找出當週週一到週五的總和) ---
    
    # 關鍵：計算該日期所屬週的星期一日期 (作為週的代表日期)
    df['week_start_date'] = df['start_date'] - pd.to_timedelta(df['start_date'].dt.weekday, unit='D')
    
    # 透過 week_start_date 進行分組，並計算每週 ath_count 和 atl_count 的總和
    weekly_df = df.groupby('week_start_date')[['ath_count', 'atl_count']].sum().reset_index()

    # ⭐ 新增要求：只輸出最後 52 週的結果 (約一年)
    weekly_df = weekly_df.tail(52)
    weekly_df.to_csv("weekly_ath_atl.csv", encoding='utf-8-sig',index=False)
    print(f"\n--- 彙總後的每週數據 (僅顯示最新的 {len(weekly_df)} 週) ---")
    print(weekly_df.head())

    # --- 步驟 2: 繪製雙軸圖 ---

    fig, ax1 = plt.subplots(figsize=(12, 6))

    color_ath = 'tab:blue'
    color_atl = 'tab:red'

    # 主軸: ath_count
    ax1.set_xlabel('Week Starting Date (Monday)')
    ax1.set_ylabel(f'Weekly ATH Count (Last {len(weekly_df)} Weeks Sum)', color=color_ath)
    
    # 使用篩選後的 weekly_df 繪圖
    ax1.plot(weekly_df["week_start_date"], weekly_df["ath_count"], 
             color=color_ath, label='Weekly ATH Count', marker='o', linestyle='-')
    ax1.tick_params(axis='y', labelcolor=color_ath)

    # 副軸: atl_count
    ax2 = ax1.twinx()
    ax2.set_ylabel(f'Weekly ATL Count (Last {len(weekly_df)} Weeks Sum)', color=color_atl)
    
    # 使用篩選後的 weekly_df 繪圖
    ax2.plot(weekly_df["week_start_date"], weekly_df["atl_count"], 
             color=color_atl, label='Weekly ATL Count', marker='x', linestyle='--')
    ax2.tick_params(axis='y', labelcolor=color_atl)

    # 設定 X 軸格式
    plt.gcf().autofmt_xdate()

    plt.title(f'Weekly ATH vs ATL Count Over Time (Last {len(weekly_df)} Weeks)')
    fig.tight_layout()
    plt.grid(True)
    
    # 將兩條線的圖例合併顯示在同一位置
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

    plt.savefig("weekly_ath_atl_data_last_52_weeks.png")
    print("\n已成功生成以週為單位，且只顯示最近 52 週的統計圖: weekly_ath_atl_data_last_52_weeks.png")
    # plt.show()


if __name__ == "__main__":
    df = pd.read_csv("datasheet.csv")
    df_252day = calculate_bear_risk_index(df).tail(252)
    plot_ath_atl_data(df_252day)
    plot_weekly_ath_atl_data()
    #plot_bear_risk_index(df)
