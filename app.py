import yfinance as yf
from portfolioManager import PortfolioManager
from databaseViewer import DatabaseViewer
from chartDrawer import ChartDrawer
from portfolioDisplayer import Displayer

def load_transactions():
    pm = PortfolioManager()
    transactions_folder = "transactions/"
    pm.load_transactions_from_folder(transactions_folder)
    pm.load_daily_cash_from_csv("transactions/cash/cash.csv")
    pm.close()

def view_database():
    viewer = DatabaseViewer()
    viewer.view_transactions()    # 查看所有交易记录，包括 cost_basis 和 total_quantity 列
    viewer.view_stock_data()      # 查看当前股票数据
    viewer.view_daily_cash()
    viewer.view_daily_prices()
    viewer.close()

def draw_chart():
    cd = ChartDrawer()
    cd.plot_pie_chart_with_cash()
    cd.close()

def display_portfolio():
    pd = Displayer()
    ror_df, summary_df = pd.calculate_rate_of_return()
    pd.save_df_as_png(df = ror_df, filename="results/portfolio_rate_of_return.png")
    pd.save_df_as_png(df = summary_df, filename="results/portfolio_summary.png")
    pd.close()

def main():
    print("Welcome to Portfolio Manager!")
    # load_transactions()
    # view_database()
    # draw_chart()
    display_portfolio()

if __name__ == "__main__":
    main()