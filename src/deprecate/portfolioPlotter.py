import matplotlib.pyplot as plt
import sqlite3
import yfinance as yf
from datetime import datetime, timedelta
from iPortfolio_util import PortfolioDisplayerUtil, Util
from const import *
from deprecate.util import Util

class Plotter:
    def __init__(self, db_name="portfolio.db"):
      self.conn = sqlite3.connect(db_name)

    def fetch_and_store_price(self, ticker, date):
        """
        从 Yahoo Finance 获取指定日期的股票价格，并存储到 daily_prices 表。
        """
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            start_date = (date_obj - timedelta(days=7)).strftime("%Y-%m-%d")
            end_date = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")

            history = yf.download(ticker, start_date, end_date)
            if not history.empty:
                price_series = history['Close']
                price = list(round(price_series.iloc[-1], 8))[0]
                with self.conn:
                    self.conn.execute("INSERT OR REPLACE INTO daily_prices (date, ticker, price) VALUES (?, ?, ?)",
                                      (date, ticker, price))
                print(f"Fetched and stored price for {ticker} on {date}: {price}")
                return price
            print(f"No price data found for {ticker} on {date}")
            return None

        except Exception as e:
            print(f"Error fetching price for {ticker} on {date}: {e}")
            return None

    def fetch_and_store_latest_price(self, ticker):
        today = Util.get_today_est_str()

        # 检查是否已有最新价格
        existing_price = self.conn.execute("""
            SELECT price FROM daily_prices WHERE date = ? AND ticker = ?
        """, (today, ticker)).fetchone()

        if existing_price:
            print(f"Price for {ticker} on {today} already exists: {existing_price[0]}")
            return existing_price[0]

        return self.fetch_and_store_price(ticker, today)

    def plot_pie_chart_with_cash(self, file_name="results/portfolio_pie_chart.png"):
        """
        绘制一个饼图，显示最新的 stock_data,包括现金余额。
        """
        tickers = set(row[0] for row in self.conn.execute("SELECT DISTINCT ticker FROM stock_data"))

        # 获取现金余额
        latest_cash_date = self.conn.execute("SELECT MAX(date) FROM daily_cash").fetchone()[0]
        cash_row = self.conn.execute("""
            SELECT cash_balance FROM daily_cash WHERE date = ?
        """, (latest_cash_date,)).fetchone()
        cash_balance = cash_row[0] if cash_row else 0

        # 计算各股票的总价值
        labels = []
        values = []

        for ticker in tickers:
            # 获取最新价格并尝试存储到 daily_prices 表
            latest_price = Util.fetch_and_store_latest_price(self.conn, ticker)

            # 获取最新一天的持仓数量和成本基础
            stock_row = self.conn.execute("""
                SELECT total_quantity, cost_basis FROM stock_data WHERE ticker = ? ORDER BY date DESC LIMIT 1
            """, (ticker,)).fetchone()
            total_quantity_ticker = stock_row[0] if stock_row[0] else 0
            total_value_ticker = (latest_price * total_quantity_ticker) if latest_price else 0
            if total_value_ticker > 0:
                labels.append(ticker)
                values.append(total_value_ticker)

        # 添加现金到图表
        if cash_balance > 0:
            labels.append("Cash")
            values.append(cash_balance)

        # 按比例从高到低排序
        values, labels = zip(*sorted(zip(values, labels), reverse=False))

        # 创建颜色渐变从深到浅
        cmap = plt.get_cmap("Blues")
        colors = [cmap(i / len(values)) for i in range(len(values))]

        # 绘制饼图
        plt.figure(figsize=(8, 8))
        plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
        plt.title("Portfolio Distribution (Latest Data)")
        plt.tight_layout()
        plt.savefig(file_name)
        plt.show()
        plt.close()

    def plot_line_chart(self, file_name, end_date, time_period, time_str, number_of_points=NUM_OF_PLOT):
        # dates = sorted(set(row[0] for row in self.conn.execute("SELECT date FROM transactions")))
        total_values = []
        total_costs = []
        total_profits = []
        pdu = PortfolioDisplayerUtil()

        # calculate dates from ytd
        if time_period == "YTD":
            time_period = Util.calculate_ytd_date_delta(end_date)

        # 获取所有出现过的ticker列表
        tickers = set(row[0] for row in self.conn.execute("SELECT DISTINCT ticker FROM stock_data"))

        # Get dates
        dates = Util.get_evenly_spaced_dates(start_date = end_date - timedelta(days=time_period),
                                                                end_date=end_date,
                                                                num_dates=number_of_points)
        for i, date in enumerate(dates):
            day_profit = 0
            day_cost = 0
            day_value = 0
            for ticker in tickers:
                # Get prices, quantity, and cost basis
                quantity = pdu.get_stock_quantity(ticker=ticker, 
                                                    date=date)
                cost_basis = pdu.get_cost_basis(ticker=ticker,
                                                date=date)
                
                # skip if quantity is 0
                if quantity == 0:
                    continue

                price = Util.fetch_and_store_price(db_conn=self.conn,
                                                   ticker=ticker,
                                                   date=date)

                value = price * quantity
                cost = cost_basis * quantity
                profit = value - cost
                day_profit += profit
                day_cost += cost
                day_value += value

            total_values.append(day_value)
            total_costs.append(day_cost)
            total_profits.append(day_profit)

            latest_cost = total_costs[-1]

        self.plot_asset_value_vs_cost_util(latest_cost, total_profits, dates, file_name, time_str)

    def plot_line_chart_ends_at_today(self, file_name, time_period, time_str, number_of_points=NUM_OF_PLOT):
        self.plot_line_chart(file_name, Util.get_today_est_dt(), time_period, time_str, number_of_points)

    def plot_asset_value_vs_cost_util(self, latest_cost, total_profits, dates, file_name, time_str):
        '''
        The logic is using the latest cost as the base cost, and adding the profit to the total value.
        '''
        total_values = [profit + latest_cost for profit in total_profits]

        # 绘制线性图
        plt.figure(figsize=(18, 9))
        plt.plot(dates, total_values, label="Total Asset Value (Excluding cash)", linestyle='-')

        colors = ['blue', 'green', 'purple']
        # 在每个点上标注数值
        for i, (x, y_value) in enumerate(zip(dates, total_values)):
            color = colors[i % len(colors)]
            y_format = f"{y_value / 1_000:.1f}K"
            plt.text(x, y_value, f"{y_format}", fontsize=16, ha='center', va='bottom', color=color)  # 标注总资产值

        # Calculate and show percentage of profit increase        
        last_value = total_values[-1]
        start_value = total_values[0]
        profit_increase_percentage = (last_value - start_value) / start_value * 100 if start_value != 0 else 0

        # 设置 x 轴为日期格式
        # plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        # plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.gcf().autofmt_xdate()  # 自动调整日期显示的角度

        # 保存/显示线性图
        plt.xlabel("Date")
        plt.ylabel("Value")
        plt.title(f"Portfolio Asset Value ({time_str})")
        plt.legend()

        # Show percentage of profit increase under the legend
        plt.text(0.5, 0.95, f"Profit Increase: {round(last_value - start_value, 2):,} ({profit_increase_percentage:.2f}%)", fontsize=18, ha='center', va='center', transform=plt.gca().transAxes, color='purple', fontweight='bold')

        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(file_name)
        plt.show()
        plt.close()

    def plot_ticker_line_chart(self, file_name, ticker, time_period, time_str, number_of_points=NUM_OF_PLOT):
        # dates = sorted(set(row[0] for row in self.conn.execute("SELECT date FROM transactions")))
        total_values = []
        total_costs = []
        total_profits = []
        pdu = PortfolioDisplayerUtil()

        # calculate dates from ytd
        if time_period == "YTD":
            time_period = Util.calculate_ytd_date_delta_ends_today()

        # Get dates
        today = Util.get_today_est_dt()
        dates = Util.get_evenly_spaced_dates(start_date = today - timedelta(days=time_period),
                                                                end_date=today,
                                                                num_dates=number_of_points)
        emtpy_dates = []
        for i, date in enumerate(dates):
            # Get prices, quantity, and cost basis
            quantity = pdu.get_stock_quantity(ticker=ticker, 
                                                date=date)
            cost_basis = pdu.get_cost_basis(ticker=ticker,
                                            date=date)
            
            # skip if quantity is 0
            if quantity == 0:
                emtpy_dates.append(date)
                continue

            price = Util.fetch_and_store_price(db_conn=self.conn,
                                                ticker=ticker,
                                                date=date)

            value = price * quantity
            cost = cost_basis * quantity
            profit = value - cost

            total_values.append(value)
            total_costs.append(cost)
            total_profits.append(profit)
            latest_cost = total_costs[-1]
        
        dates = [date for date in dates if date not in emtpy_dates]
        # print(file_name)
        # print(f"latest_cost: {latest_cost}, total_profits: {total_profits}, dates: {dates},time_str: {time_str}")
        # print(len(total_profits), len(dates))

        self.plot_asset_value_vs_cost_util(latest_cost, total_profits, dates, file_name, time_str)

    def close(self):
        self.conn.close()
        print("Database connection closed.")