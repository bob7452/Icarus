from stock_rules import rs_above_90
from file_io import read_stock_info_json
HEADER = "###{},"
FORMAT = "{}:{},"


def main():
    stocks = rs_above_90()
    stocks = stocks['name'].to_list() 

    info = read_stock_info_json()
    txt_words = ""
    group = {}

    with open("trading_view_list.txt",mode='w',) as file:
        for stock in stocks:
            industry : str = info[stock]["industry"]
            universe : str = info[stock]["universe"]
            universe = universe.replace('NYSE MKT','AMEX')

            if industry not in group:
                group[industry] = [FORMAT.format(universe,stock)]
            else:
                group[industry].append(FORMAT.format(universe,stock))
        

        for universe , stock in group.items():
            txt_words += HEADER.format(universe) + "".join(stock)
        
        file.write(txt_words)

if __name__ == "__main__":
    main()