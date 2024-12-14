from tabulate import tabulate  # 用于表格格式化显示
import sqlite3
import pandas as pd

class DatabaseViewer:
    def __init__(self, db_name="portfolio.db"):
        # 初始化 SQLite 数据库连接
        self.conn = sqlite3.connect(db_name)

    def fetch_data(self, query):
        df = pd.read_sql_query(query, self.conn)
        return df

    def save_tabulate_to_csv(self, query, keys, filename):
        df = self.fetch_data(query)
        table = tabulate(df, headers=keys, tablefmt='pretty')
        with open(filename, 'w') as f:
            f.write(table)

    def save_transactions_to_csv(self, filename):
        query = "SELECT * FROM transactions ORDER BY date DESC"
        keys = ["Date", "Ticker", "Source", "Cost", "Quantity"]
        self.save_tabulate_to_csv(query, keys, filename)

    def save_stock_data_to_csv(self, filename):
        query = "SELECT * FROM stock_data ORDER BY date DESC"
        keys = ["Date", "Ticker", "Cost Basis", "Total Quantity"]
        self.save_tabulate_to_csv(query, keys, filename)    

    def save_daily_cash_to_csv(self, filename):
        query = "SELECT * FROM daily_cash ORDER BY date DESC"
        keys = ["Date", "Cash Balance"]
        self.save_tabulate_to_csv(query, keys, filename)

    def save_daily_prices_to_csv(self, filename):
        query = "SELECT * FROM daily_prices ORDER BY date DESC"
        keys = ["Date", "Ticker", "Price"]
        self.save_tabulate_to_csv(query, keys, filename)

    def save_realized_gain_to_csv(self, filename):
        query = "SELECT * FROM realized_gains ORDER BY date DESC"
        keys = ["Date", "Ticker", "Gain"]
        self.save_tabulate_to_csv(query, keys, filename)

    def view_transactions(self):
        """按日期降序查看交易记录表的数据"""
        with self.conn:
            cursor = self.conn.execute("SELECT * FROM transactions ORDER BY date DESC")
            transactions = cursor.fetchall()
            print("\nTransactions (sorted by date, descending):")
            print(tabulate(transactions, headers=["Date", "Ticker", "Source", "Cost", "Quantity"], tablefmt="pretty"))

    def view_daily_prices(self):
        """查看 daily_prices 表的数据"""
        with self.conn:
            cursor = self.conn.execute("SELECT * FROM daily_prices ORDER BY date DESC")
            daily_prices = cursor.fetchall()
            print("\nDaily Prices:")
            print(tabulate(daily_prices, headers=["Date", "Ticker", "Price"], tablefmt="pretty"))

    def view_stock_data(self):
        """查看 stock_data 表的数据，包括 date、cost_basis 和 total_quantity 列"""
        with self.conn:
            cursor = self.conn.execute("SELECT * FROM stock_data ORDER BY date DESC")
            stock_data = cursor.fetchall()
            print("\nStock Data (including date, cost_basis, and total_quantity):")
            print(tabulate(stock_data, headers=["Date", "Ticker", "Cost Basis", "Total Quantity"], tablefmt="pretty"))

    def view_daily_cash(self):
        """查看 daily_cash 表的数据，包括日期和现金余额"""
        with self.conn:
            cursor = self.conn.execute("SELECT * FROM daily_cash ORDER BY date DESC")
            daily_cash = cursor.fetchall()
            print("\nDaily Cash:")
            print(tabulate(daily_cash, headers=["Date", "Cash Balance"], tablefmt="pretty"))

    def view_realized_gain(self):
        with self.conn:
            cursor = self.conn.execute("SELECT * FROM realized_gains ORDER BY date DESC")
            realized_gain = cursor.fetchall()
            print("\nRealized Gain:")
            print(tabulate(realized_gain, headers=["Date", "Ticker", "Gain"], tablefmt="pretty"))

    def close(self):
        """关闭数据库连接"""
        self.conn.close()