from file_io import read_lastest_rs_report

def qualified_stocks():
    df = read_lastest_rs_report()
    
    filtered_stocks = df[
        (df['close_to_high_10%'] == True) & 
        (df['powerful_than_spy'] == True) & 
        (df['group_powerful_than_spy'] == True) &
        (df['breakout_with_big_volume'] == True)
        # (df['above_all_moving_avg_line'] == True)
    ]

    return filtered_stocks

def powerful_than_spy_stock():
    df = read_lastest_rs_report()
    
    filtered_stocks = df[
        (df['powerful_than_spy'] == True) & 
        (df['group_powerful_than_spy'] == True) &
        (df['above_all_moving_avg_line'] == True)
    ]

    return filtered_stocks