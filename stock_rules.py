from file_io import read_lastest_rs_report, read_lastest_heat_report

# 改為大寫，代表全域常數；並將 list 改為 set，搜尋速度更快 (O(1) 複雜度)
STOCKS_TO_EXCLUDE = {'MOBBW', 'NUKKW'}

def qualified_stocks(df):
    """強勢突破股篩選策略"""
    return df[
        df['close_to_high_10%'] & 
        df['powerful_than_spy'] & 
        df['group_powerful_than_spy'] &
        df['breakout_with_big_volume'] &
        (df['rank'] >= 90) &
        ~df['name'].isin(STOCKS_TO_EXCLUDE)
        # df['above_all_moving_avg_line']  # 如果想啟用，直接取消註解即可
    ]

def powerful_than_spy_stock(df):
    """大盤超額收益股篩選策略"""
    return df[
        df['powerful_than_spy'] & 
        df['group_powerful_than_spy'] &
        df['above_all_moving_avg_line']
    ]

def rs_above_90(df):
    """RS 評級大於 90 的股票"""
    return df[df['rank'] >= 90]

def heat_rank_rs90(rs_df, heat_df):
    """
    交集策略：找出同時具備高熱度與高 RS 評級的股票。
    支援 heat_df 是 DataFrame（含 'name' 欄位）或是純代號列表。
    """
    # 取得 RS > 90 的股票名稱集合
    rs_names = set(rs_above_90(rs_df)['name'])
    
    # 判斷 heat_df 是 DataFrame 還是一般的 list/set
    if hasattr(heat_df, 'columns') and 'name' in heat_df.columns:
        heat_names = set(heat_df['name'])
    else:
        heat_names = set(heat_df)

    # 使用 set 的 intersection 取交集，效率極高
    return list(rs_names.intersection(heat_names))
