import yfinance as yf
from portfolioManager import PortfolioManager
from databaseViewer import DatabaseViewer
from portfolioChartDrawer import ChartDrawer
from portfolioDisplayer import Displayer

LOCAL_PATH = "results/"
ROR_TABLE_PATH = "results/ror_table/"
CHART_PATH = "results/charts/"

def load_transactions():
    pm = PortfolioManager()
    transactions_folder = "transactions/"
    pm.load_transactions_from_folder(transactions_folder)
    pm.load_daily_cash_from_csv("transactions/cash/cash.csv")
    pm.close()

def view_database():
    viewer = DatabaseViewer()
    # viewer.view_transactions()    # 查看所有交易记录，包括 cost_basis 和 total_quantity 列
    # viewer.view_stock_data()      # 查看当前股票数据
    # viewer.view_daily_cash()
    viewer.view_daily_prices()
    # viewer.view_realized_gain()
    viewer.close()

def draw_chart():
    cd = ChartDrawer()
    cd.plot_pie_chart_with_cash()
    cd.plot_asset_value_vs_cost()

def display_portfolio():
    pd = Displayer()
    yyyy_mm_dd = [ ("2024", "11", "30"), ("2024", "11", "01"), ("2024", "10", "01"), ("2024", "09", "01"), ("2024", "08", "01")]
    for yyyy, mm, dd in yyyy_mm_dd:
        print(f"Generating portfolio snapshot for {yyyy}-{mm}-{dd}...")
        ror_df, summary_df = pd.calculate_rate_of_return_v2(f"{yyyy}-{mm}-{dd}")
        print("Generating rate of return chart...")
        pd.save_df_as_png(df = ror_df, 
                          filename=ROR_TABLE_PATH + f"portfolio_rate_of_return_{yyyy}_{mm}_{dd}.png",
                          title=f"Portfolio Rate of Return {yyyy}-{mm}-{dd}")
        print("Generating portfolio summary...")
        pd.save_df_as_png(df = summary_df, 
                          filename=ROR_TABLE_PATH + f"portfolio_summary_{yyyy}_{mm}_{dd}.png",
                          title=f"Portfolio Summary {yyyy}-{mm}-{dd}")

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
    # clear daily_prices table
    portfolio.clear_table("realized_gains")

def main():
    print("Welcome to Portfolio Manager!")
    # clear_table()
    # load_transactions()
    # view_database()
    # draw_chart()
    display_portfolio()
    

if __name__ == "__main__":
    main()