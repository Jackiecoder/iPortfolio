from portfolioManager import PortfolioManager
from databaseViewer import DatabaseViewer
from portfolioPlotter import Plotter
from portfolioDisplayer import Displayer
from portfolioTickerPlotter import TickerRORPlotter
from portfolioDisplayer_util import PortfolioDisplayerUtil
from const import *
from const_private import *

def load_transactions():
    clear_table()
    print(f"{title_line} Loading transactions... {title_line}")
    pm = PortfolioManager()
    for cat in TRANSACTIONS_CATS:
        pm.load_transactions_from_folder(TRANSACTIONS_PATH + cat + "/")
    pm.load_daily_cash_from_csv(CASH_PATH)
    pm.close()

def view_database():
    print(f"{title_line} Saving database to CSV... {title_line}")
    viewer = DatabaseViewer()
    viewer.save_transactions_to_csv(f"{DBVIEWER_PATH}transactions.csv")
    viewer.save_stock_data_to_csv(f"{DBVIEWER_PATH}stock_data.csv")
    viewer.save_daily_cash_to_csv(f"{DBVIEWER_PATH}daily_cash.csv")
    viewer.save_daily_prices_to_csv(f"{DBVIEWER_PATH}daily_prices.csv")
    viewer.save_realized_gain_to_csv(f"{DBVIEWER_PATH}realized_gains.csv")
    viewer.close()

def clear_table():
    print(f"{title_line} Clearing tables... {title_line}")
    # 初始化 PortfolioManager 并添加一些交易记录
    portfolio = PortfolioManager()
    # 清空 transactions 表
    portfolio.clear_table("transactions")
    # 清空 stock_data 表
    portfolio.clear_table("stock_data")
    # clear daily_cash table
    portfolio.clear_table("daily_cash")
    # clear daily_prices table
    portfolio.clear_table("realized_gains")

def plot_line_chart():
    print(f"{title_line} Plotting line chart... {title_line}")
    pt = Plotter()
    for date_str, (date_num, date_unit) in DATES.items():
        print(f"Plotting line chart for {date_str}...")
        pt.plot_line_chart(file_name= f"{CHART_PATH}portfolio_line_chart_{date_unit}_{date_str}.png", 
                           time_period=date_num, 
                           time_str=date_str)

def plot_ticker_line_chart():
    print(f"{title_line} Plotting ticker line chart... {title_line}")
    pt = Plotter()
    ticker = [STOCK_TICKERS[0], CRYPTO_TICKERS[0], CRYPTO_TICKERS[1]]
    dates = ["1M", "3M", "6M"]
    for ticker in ticker:
        for date_str in dates:
            print(f"Plotting line chart for {ticker} {date_str}")
            date_num, date_unit = DATES[date_str]
            pt.plot_ticker_line_chart(file_name=f"{TICKER_CHART_PATH}{ticker}_{date_unit}_{date_str}.png",
                                    ticker=ticker,
                                    time_period=date_num,
                                    time_str=date_str)

def display_portfolio_ror(yyyy_mm_dd):
    print(f"{title_line} Displaying portfolio ror... {title_line}")
    pd = Displayer()
    for yyyy, mm, dd in yyyy_mm_dd:
        print(f"Generating portfolio snapshot for {yyyy}-{mm}-{dd}...")
        ror_df, summary_df = pd.calculate_rate_of_return_v2(f"{yyyy}-{mm}-{dd}")
        print("Generating rate of return chart...")
        pd.save_df_as_png(df = ror_df, 
                          filename=ROR_TABLE_PATH + f"{yyyy}_{mm}_{dd}_Total_RoR.png",
                          title=f"Portfolio Rate of Return {yyyy}-{mm}-{dd}")
        print("Generating portfolio summary...")
        pd.save_df_as_png(df = summary_df, 
                          filename=ROR_TABLE_PATH + f"{yyyy}_{mm}_{dd}_Summary.png",
                          title=f"Portfolio Summary {yyyy}-{mm}-{dd}")

    pd.close()

def display_ticker_ror():
    print("{title_line} Displaying ticker ror... {title_line}")
    ror_plotter = TickerRORPlotter()
    ror_plotter.plot_all_tickers()

def test():
    # PortfolioManager()
    dbv = DatabaseViewer()
    pdu = PortfolioDisplayerUtil()
    pdu.clear_daily_prices(date="2024-12-10", before=False)
    dbv.save_daily_prices_to_csv("./test_daily_prices_1.csv")
    # pdu.fetch_and_store_price("NVDA", "2024-12-15")
    # dbv.save_daily_prices_to_csv("./test_daily_prices_2.csv")