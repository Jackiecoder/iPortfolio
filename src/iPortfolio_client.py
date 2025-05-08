from iPortfolio_dbPopulator import DbPopulator
from iPortfolio_dbViewer import DatabaseViewer
from iPortfolio_plotter import Plotter
from iPortfolio_dashboard import AssetDashboard
from iPortfolio_util import PortfolioDisplayerUtil, Util
from iPortfolio_dbAccessor import DbAccessor
from const import *
from const_private import *
from datetime import datetime

def load_transactions():
    clear_table()
    print(f"{title_line} Loading transactions... {title_line}")
    db_loader = DbPopulator()
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
    db_loader = DbPopulator()
    db_loader.clear_table("transactions")
    db_loader.clear_table("stock_data")
    db_loader.clear_table("daily_cash")
    db_loader.clear_table("realized_gains")

def plot_line_chart():
    print(f"{title_line} Plotting line chart... {title_line}")
    pt = Plotter()
    for date_str, (date_num, date_unit) in DATES.items():
        if date_str in ("1M", "3M", "YTD"):
            path = OUTPUT_DASHBOARD_PATH
        else:
            # Don't need other charts
            path = CHART_PATH
            continue
        print(f"Plotting line chart for {date_str}...")
        pt.plot_line_chart_ends_at_today(file_name= f"{path}portfolio_line_chart_{date_unit}_{date_str}.png", 
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
        pt.plot_line_chart(file_name=f"{OUTPUT_DASHBOARD_PATH}portfolio_line_chart_{date}_{date_str}.png",
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

def delete_daily_prices(date):
    print(f"{title_line} Clearing daily prices... {title_line}")
    DbAccessor.delete_daily_price(date)

# def display_portfolio_ror_util(yyyy_mm_dd):
#     if not yyyy_mm_dd:
#         print(f"Invalid date: {yyyy_mm_dd}")
#         return

#     pd = Displayer()
#     for yyyy, mm, dd in yyyy_mm_dd:
#         print(f"Generating portfolio snapshot for {yyyy}-{mm}-{dd}...")
#         ror_df, summary_df, cat_df = pd.calculate_rate_of_return_v2(f"{yyyy}-{mm}-{dd}")
#         print("Generating rate of return chart...")
#         pd.save_df_as_png(df = ror_df, 
#                           filename=ROR_TOTAL_TABLE_PATH + f"{yyyy}_{mm}_{dd}_Total.png",
#                           title=f"Portfolio Rate of Return {yyyy}-{mm}-{dd}")
#         print("Generating portfolio summary...")
#         pd.save_df_as_png(df = summary_df, 
#                           filename=ROR_SUMMARY_TABLE_PATH + f"{yyyy}_{mm}_{dd}_Summary.png",
#                           title=f"Portfolio Summary {yyyy}-{mm}-{dd}")

#         print("Generating category summary...")
#         pd.save_df_as_png(df = cat_df, 
#                           filename=ROR_SUMMARY_TABLE_PATH + f"{yyyy}_{mm}_{dd}_Category.png",
#                           title=f"Portfolio Category {yyyy}-{mm}-{dd}")
#     pd.close()

def display_portfolio_ror_latest():
    print(f"{title_line} Displaying today's portfolio ror... {title_line}")
    asset_dashboard = AssetDashboard()
    path = OUTPUT_DASHBOARD_PATH

    yyyy, mm, dd, time = Util.get_current_time_est_str().split("-")
    today = f"{yyyy}-{mm}-{dd}"
    ror_df, summary_df, cat_df, compare_df = asset_dashboard.calculate_ror(today)

    hour, minute, second = time.split(":")
    print(f"Generating rate of return chart for {yyyy}-{mm}-{dd}...")
    asset_dashboard.save_df_as_png(ori_df = ror_df, 
                      filename=path + "9999-99-99_Total.png",
                      title=f"Portfolio Rate of Return {yyyy}-{mm}-{dd} {hour}:{minute}:{second}")
    print(f"Generating portfolio summary for {yyyy}-{mm}-{dd}...")
    asset_dashboard.save_df_as_png(ori_df = summary_df, 
                        filename=path + f"9999-99-99_Summary.png",
                        title=f"Portfolio Summary {yyyy}-{mm}-{dd} {hour}:{minute}:{second}")

    print(f"Generating category summary for {yyyy}-{mm}-{dd}...")
    asset_dashboard.save_df_as_png(ori_df = cat_df, 
                        filename=path + f"9999-99-99_Category.png",
                        title=f"Portfolio Category {yyyy}-{mm}-{dd} {hour}:{minute}:{second}")
    
    print(f"Generating compare summary for {yyyy}-{mm}-{dd}...")
    asset_dashboard.save_df_as_png(ori_df = compare_df, 
                        filename=path + f"9999-99-99_Compare.png",
                        title=f"Portfolio Compare {yyyy}-{mm}-{dd} {hour}:{minute}:{second}")

# def display_ticker_ror():
#     print("{title_line} Displaying ticker ror... {title_line}")
#     ror_plotter = TickerRORPlotter()
#     ror_plotter.plot_all_tickers()

def test():
    dbv = DatabaseViewer()
    pdu = PortfolioDisplayerUtil()
    pdu.clear_daily_prices(date="2024-12-16", before=False)
    dbv.save_daily_prices_to_csv("./test_daily_prices_1.csv")
    # pdu.fetch_and_store_price("NVDA", "2024-12-15")
    # dbv.save_daily_prices_to_csv("./test_daily_prices_2.csv")