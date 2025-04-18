from portfolioManager import PortfolioManager
from iPortfolio_dbloader import DbLoader
from databaseViewer import DatabaseViewer
from portfolioPlotter import Plotter
from portfolioDisplayer import Displayer
from portfolioTickerPlotter import TickerRORPlotter
from iPortfolio_util import PortfolioDisplayerUtil, Util
from util import Util
from const import *
from const_private import *
from datetime import datetime, timedelta

def load_transactions():
    clear_table()
    print(f"{title_line} Loading transactions... {title_line}")
    db_loader = DbLoader()
    for cat in TRANSACTIONS_CATS:
        db_loader.load_transactions_from_folder(TRANSACTIONS_PATH + cat + "/")
    db_loader.load_daily_cash_from_csv(CASH_PATH)
    db_loader.populate_transaction_db()
    db_loader.verify_table_size()
    db_loader.close()


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
    # portfolio = PortfolioManager()
    # # 清空 transactions 表
    # portfolio.clear_table("transactions")
    # # 清空 stock_data 表
    # portfolio.clear_table("stock_data")
    # # clear daily_cash table
    # portfolio.clear_table("daily_cash")
    # # clear daily_prices table
    # portfolio.clear_table("realized_gains")
    db_loader = DbLoader()
    db_loader.clear_table("transactions")
    db_loader.clear_table("stock_data")
    db_loader.clear_table("daily_cash")
    db_loader.clear_table("realized_gains")

def plot_line_chart():
    print(f"{title_line} Plotting line chart... {title_line}")
    pt = Plotter()
    for date_str, (date_num, date_unit) in DATES.items():
        print(f"Plotting line chart for {date_str}...")
        pt.plot_line_chart_ends_at_today(file_name= f"{CHART_PATH}portfolio_line_chart_{date_unit}_{date_str}.png", 
                                        time_period=date_num, 
                                        time_str=date_str)

def display_historical_portfolio_ror():
    print(f"{title_line} Displaying historical portfolio ror... {title_line}")
    dates = [("2024", "11", "01"),("2024", "10", "01"), ("2024", "09", "01"), ("2024", "08", "01"), ("2024", "07", "01"), ("2024", "06", "01"), ("2024", "05", "01"), ("2024", "04", "01"), ("2024", "03", "01"), ("2024", "02", "01"), ("2024", "01", "01")]
    display_portfolio_ror(dates)

def plot_historical_line_chart():
    print(f"{title_line} Plotting historical line chart... {title_line}")
    pt = Plotter()
    dates = ["2023-12-31", "2022-12-31", "2021-12-31", "2024-12-31"]
    for date in dates:
        date_dt = datetime.strptime(date, "%Y-%m-%d")
        date_num, date_str = "YTD", "YTD"
        pt.plot_line_chart(file_name=f"{CHART_PATH}portfolio_line_chart_{date}_{date_str}.png",
                                        end_date=date_dt,
                                        time_period=date_num,
                                        time_str=date_str)  
    
def plot_ticker_line_chart():
    print(f"{title_line} Plotting ticker line chart... {title_line}")
    pt = Plotter()
    ticker = [STOCK_TICKERS[0], CRYPTO_TICKERS[0], CRYPTO_TICKERS[1], CRYPTO_TICKERS[2]]
    dates = ["1M", "3M", "6M"]
    for ticker in ticker:
        for date_str in dates:
            if DIYSWITCH == True and ticker == CRYPTO_TICKERS[2] and date_str != "1M":
                continue
            print(f"Plotting line chart for {ticker} {date_str}")
            date_num, date_unit = DATES[date_str]
            pt.plot_ticker_line_chart(file_name=f"{TICKER_CHART_PATH}{ticker}_{date_unit}_{date_str}.png",
                                    ticker=ticker,
                                    time_period=date_num,
                                    time_str=date_str)

def display_portfolio_ror(yyyy_mm_dd, previous_range = 2):
    print(f"{title_line} Displaying portfolio ror... {title_line}")
    if yyyy_mm_dd:
        display_portfolio_ror_util(yyyy_mm_dd)

    if not yyyy_mm_dd:
        today = Util.get_today_est_dt()
        days = [today - timedelta(days=i) for i in range(previous_range)]
        Util.log(days)
        for day in days:
            print(f"Generating portfolio snapshot for {day.strftime('%Y-%m-%d')}...")
            yyyy_mm_dd = [day.strftime("%Y-%m-%d").split("-")]
            display_portfolio_ror_util(yyyy_mm_dd)

def display_portfolio_ror_util(yyyy_mm_dd):
    if not yyyy_mm_dd:
        print(f"Invalid date: {yyyy_mm_dd}")
        return

    pd = Displayer()
    for yyyy, mm, dd in yyyy_mm_dd:
        print(f"Generating portfolio snapshot for {yyyy}-{mm}-{dd}...")
        ror_df, summary_df, cat_df = pd.calculate_rate_of_return_v2(f"{yyyy}-{mm}-{dd}")
        print("Generating rate of return chart...")
        pd.save_df_as_png(df = ror_df, 
                          filename=ROR_TOTAL_TABLE_PATH + f"{yyyy}_{mm}_{dd}_Total.png",
                          title=f"Portfolio Rate of Return {yyyy}-{mm}-{dd}")
        print("Generating portfolio summary...")
        pd.save_df_as_png(df = summary_df, 
                          filename=ROR_SUMMARY_TABLE_PATH + f"{yyyy}_{mm}_{dd}_Summary.png",
                          title=f"Portfolio Summary {yyyy}-{mm}-{dd}")

        print("Generating category summary...")
        pd.save_df_as_png(df = cat_df, 
                          filename=ROR_SUMMARY_TABLE_PATH + f"{yyyy}_{mm}_{dd}_Category.png",
                          title=f"Portfolio Category {yyyy}-{mm}-{dd}")
    pd.close()

def display_portfolio_ror_latest():
    print(f"{title_line} Displaying today's portfolio ror... {title_line}")
    pd = Displayer()
    ror_df, summary_df, cat_df = pd.calculate_rate_of_return_latest()
    yyyy, mm, dd = Util.get_today_est_str().split("-")
    print(f"Generating rate of return chart for {yyyy}-{mm}-{dd}...")
    pd.save_df_as_png(df = ror_df, 
                      filename=ROR_TOTAL_TABLE_PATH + "9999-99-99_Total.png",
                      title=f"Portfolio Rate of Return {yyyy}-{mm}-{dd}")
    print(f"Generating portfolio summary for {yyyy}-{mm}-{dd}...")
    pd.save_df_as_png(df = summary_df, 
                        filename=ROR_SUMMARY_TABLE_PATH + f"9999-99-99_Summary.png",
                        title=f"Portfolio Summary {yyyy}-{mm}-{dd}")

    print(f"Generating category summary for {yyyy}-{mm}-{dd}...")
    pd.save_df_as_png(df = cat_df, 
                        filename=ROR_SUMMARY_TABLE_PATH + f"9999-99-99_Category.png",
                        title=f"Portfolio Category {yyyy}-{mm}-{dd}")
    pd.close()

def display_ticker_ror():
    print("{title_line} Displaying ticker ror... {title_line}")
    ror_plotter = TickerRORPlotter()
    ror_plotter.plot_all_tickers()

def test():
    # PortfolioManager()
    dbv = DatabaseViewer()
    pdu = PortfolioDisplayerUtil()
    pdu.clear_daily_prices(date="2024-12-16", before=False)
    dbv.save_daily_prices_to_csv("./test_daily_prices_1.csv")
    # pdu.fetch_and_store_price("NVDA", "2024-12-15")
    # dbv.save_daily_prices_to_csv("./test_daily_prices_2.csv")