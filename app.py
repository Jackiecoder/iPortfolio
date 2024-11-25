import yfinance as yf
from portfolioManager import PortfolioManager
from databaseViewer import DatabaseViewer
from portfolioChartDrawer import ChartDrawer
from portfolioDisplayer import Displayer

LOCAL_PATH = "results/"

def load_transactions():
    pm = PortfolioManager()
    transactions_folder = "transactions/"
    pm.load_transactions_from_folder(transactions_folder)
    pm.load_daily_cash_from_csv("transactions/cash/cash.csv")
    pm.close()

def view_database():
    viewer = DatabaseViewer()
    # viewer.view_transactions()    # 查看所有交易记录，包括 cost_basis 和 total_quantity 列
    viewer.view_stock_data()      # 查看当前股票数据
    viewer.view_daily_cash()
    # viewer.view_daily_prices()
    viewer.close()

def draw_chart():
    cd = ChartDrawer()
    cd.plot_pie_chart_with_cash()
    cd.plot_asset_value_vs_cost()

def display_portfolio():
    pd = Displayer()
    ror_df, summary_df = pd.calculate_rate_of_return_v2()
    print("Generating rate of return chart...")
    filename = "portfolio_rate_of_return.png"
    pd.save_df_as_png(df = ror_df, filename=LOCAL_PATH + filename)
    print("Generating portfolio summary...")
    filename = "portfolio_summary.png"
    pd.save_df_as_png(df = summary_df, filename=LOCAL_PATH + filename)
    pd.close()

def clear_table():
    # 初始化 PortfolioManager 并添加一些交易记录
    portfolio = PortfolioManager()
    # 清空 transactions 表
    portfolio.clear_table("transactions")
    # 清空 stock_data 表
    portfolio.clear_table("stock_data")
    # clear daily_cash table
    portfolio.clear_table("daily_cash")

def main():
    print("Welcome to Portfolio Manager!")
    # load_transactions()
    # view_database()
    # draw_chart()
    display_portfolio()
    # clear_table()

if __name__ == "__main__":
    main()