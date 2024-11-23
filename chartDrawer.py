import matplotlib.pyplot as plt
import sqlite3
import yfinance as yf
from datetime import datetime, timedelta

class ChartDrawer:
    def __init__(self, db_name="/content/drive/MyDrive/Asset/portfolio.db"):
      self.conn = sqlite3.connect(db_name)


    def fetch_and_store_price(self, ticker, date):
        """
        从 Yahoo Finance 获取指定日期的股票价格，并存储到 daily_prices 表。
        """
        try:
            stock = yf.Ticker(ticker)
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
        today = datetime.now().strftime("%Y-%m-%d")

        # 检查是否已有最新价格
        existing_price = self.conn.execute("""
            SELECT price FROM daily_prices WHERE date = ? AND ticker = ?
        """, (today, ticker)).fetchone()

        if existing_price:
            print(f"Price for {ticker} on {today} already exists: {existing_price[0]}")
            return existing_price[0]

        return self.fetch_and_store_price(ticker, today)


    def plot_pie_chart_with_cash(self, file_name="/content/drive/MyDrive/Asset/portfolio_pie_chart.png"):
        """
        绘制一个饼图，显示最新的 stock_data，包括现金余额。
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
            latest_price = self.fetch_and_store_latest_price(ticker)

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