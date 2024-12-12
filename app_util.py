from portfolioManager import PortfolioManager
from databaseViewer import DatabaseViewer
from portfolioPlotter import Plotter
from portfolioDisplayer import Displayer
from tickerRORPlotter import TickerRORPlotter
from portfolioDisplayer_util import PortfolioDisplayerUtil
from const import *

def load_transactions():
    clear_table()
    pm = PortfolioManager()
    for cat in TRANSACTIONS_CATS:
        pm.load_transactions_from_folder(TRANSACTIONS_PATH + cat + "/")
    pm.load_daily_cash_from_csv(CASH_PATH)
    pm.close()

def view_database():
    viewer = DatabaseViewer()
    viewer.save_transactions_to_csv(f"{DBVIEWER_PATH}transactions.csv")
    viewer.save_stock_data_to_csv(f"{DBVIEWER_PATH}stock_data.csv")
    viewer.save_daily_cash_to_csv(f"{DBVIEWER_PATH}daily_cash.csv")
    viewer.save_daily_prices_to_csv(f"{DBVIEWER_PATH}daily_prices.csv")
    viewer.save_realized_gain_to_csv(f"{DBVIEWER_PATH}realized_gains.csv")
    viewer.close()

def clear_table():
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

def plot_chart():
    pt = Plotter()
    for date_str, (date_num, date_unit) in DATES.items():
        if (date_str != "3M"):
            continue
        
        pt.plot_line_chart(f"{CHART_PATH}portfolio_line_chart_{date_unit}_{date_str}.png", time_period=date_num)


def display_portfolio(yyyy_mm_dd):
    pd = Displayer()
    for yyyy, mm, dd in yyyy_mm_dd:
        print(f"Generating portfolio snapshot for {yyyy}-{mm}-{dd}...")
        ror_df, summary_df = pd.calculate_rate_of_return_v2(f"{yyyy}-{mm}-{dd}")
        print("Generating rate of return chart...")
        pd.save_df_as_png(df = ror_df, 
                          filename=ROR_TABLE_PATH + f"{yyyy}_{mm}_{dd}_portfolio_ror.png",
                          title=f"Portfolio Rate of Return {yyyy}-{mm}-{dd}")
        print("Generating portfolio summary...")
        pd.save_df_as_png(df = summary_df, 
                          filename=ROR_TABLE_PATH + f"{yyyy}_{mm}_{dd}_portfolio_summary.png",
                          title=f"Portfolio Summary {yyyy}-{mm}-{dd}")

    pd.close()

def display_ticker_ror():
    ror_plotter = TickerRORPlotter()
    ror_plotter.plot_all_tickers()
