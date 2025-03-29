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



if __name__ == "__main__":
    df = pd.read_csv("datasheet.csv")
    df = calculate_bear_risk_index(df).tail(240)
    plot_ath_atl_data(df)
    plot_bear_risk_index(df)
