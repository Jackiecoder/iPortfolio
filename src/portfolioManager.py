import sqlite3
import yfinance as yf
import csv
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pytz
import os
import matplotlib.dates as mdates
from portfolioDisplayer_util import PortfolioDisplayerUtil, Util


class PortfolioManager:
    def __init__(self, db_name="portfolio.db"):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()
        self.stock_splits = self.load_stock_splits('transactions/stock_split.csv')

    def create_tables(self):
        with self.conn:
            '''
            Input data: read from csv file.
            1. transactions: date, ticker, source, cost, quantity
            2. daily_cash: date, cash_balance
            '''
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    date TEXT,
                    ticker TEXT,
                    source TEXT,
                    cost REAL,
                    quantity REAL,
                    PRIMARY KEY (date, ticker, source)
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_cash (
                    date TEXT PRIMARY KEY,
                    cash_balance REAL
                )
            """)

            '''
            Fetch data: read from Yahoo Finance.
            1. daily_prices: date, ticker, price
            '''
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_prices (
                    date TEXT,
                    ticker TEXT,
                    price REAL,
                    PRIMARY KEY (date, ticker)
                )
            """)

            '''
            Output data: calculate cost_basis, total_quantity and store them.
            1. stock_data: date, ticker, cost_basis, total_quantity
            2. gains: date, realized_gain, unrealized_gain
            '''
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_data (
                    date TEXT,
                    ticker TEXT,
                    cost_basis REAL,
                    total_quantity REAL,
                    PRIMARY KEY (date, ticker)
                )
            """)
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS realized_gains (
                date TEXT,
                ticker TEXT,
                gain REAL,
                PRIMARY KEY (date, ticker)
                )
            """)

    def load_stock_splits(self, file_path):
        stock_splits = {}
        with open(file_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                date, ticker, before_split, after_split = row
                if ticker not in stock_splits:
                    stock_splits[ticker] = []
                stock_splits[ticker].append((date, float(before_split), float(after_split)))
        return stock_splits

    def adjust_quantity_for_splits(self, ticker, old_date, new_date, old_quantity, old_cost_basis):
        if ticker in self.stock_splits:
            for split_date, before_split, after_split in sorted(self.stock_splits[ticker]):
                if (old_date == 0 or old_date < split_date) and new_date >= split_date:
                    old_quantity *= (after_split / before_split)
                    old_cost_basis /= (after_split / before_split)
        return old_quantity, old_cost_basis

    def add_transaction(self, date, ticker, cost, quantity, source):
        # check if the transaction already exists
        existing = self.conn.execute("""
            SELECT * FROM transactions WHERE date = ? AND ticker = ? AND source = ?
        """, (date, ticker, source)).fetchone()
        
        if existing:
            # update the transaction if it already exists
            date, ticker, source, total_cost_date, total_quantity_date = existing
            total_cost_date += cost
            total_quantity_date += quantity
            self.conn.execute("""
                UPDATE transactions
                SET cost = ?, quantity = ?
                WHERE date = ? AND ticker = ? AND source = ?
            """, (total_cost_date, total_quantity_date, date, ticker, source))
        else:
            self.conn.execute("""
                INSERT INTO transactions (date, ticker, cost, quantity, source)
                VALUES (?, ?, ?, ?, ?)
            """, (date, ticker, cost, quantity, source))

        # Update realized gains if the transaction has a negative value
        # cost > 0, quantity > 0: buy
        # cost < 0, quantity < 0: sell
        # cost < 0, quantity = 0: dividend
        # For sell and dividend, update realized gains and change the quantity of stock_data only
        if cost < 0:
            # only update realized gains and the stock data holding
            self.update_realized_gains(date, ticker, cost, quantity)
            self.update_stock_data(date, ticker, 0, quantity)
        else:
            self.update_stock_data(date, ticker, cost, quantity)
            self.update_future_cost_basis_and_quantity(date, ticker, cost, quantity)


    def update_stock_data(self, date, ticker, cost_new, quantity_new):
        # calculate cost_basis and total_quantity
        # if cost <= 0, means dividend or sell, only quantity will be recalculated
        #   quantity <= 0 
        # if cost > 0, means buy, both cost_basis and quantity will be recalculated
        #   quantity must > 0
        if (cost_new <= 0 and quantity_new > 0) or (cost_new > 0 and quantity_new <= 0):
            print("Invalid transaction")
            return 

        row = self.conn.execute("SELECT cost_basis, total_quantity, date FROM stock_data WHERE ticker = ? AND date <= ? ORDER BY date DESC LIMIT 1",
                                (ticker, date)).fetchone()
        
        cost_basis, quantity, prev_date = 0, 0, 0 # 默认值
        if row:
            cost_basis, quantity, prev_date = row

        # Adjust quantity for splits
        quantity, cost_basis = self.adjust_quantity_for_splits(ticker=ticker, 
                                                   old_date=prev_date, 
                                                   new_date=date, 
                                                   old_quantity=quantity,
                                                   old_cost_basis=cost_basis)
        

        if cost_new > 0: # buy 
            # calculate new total cost
            total_cost = round(cost_basis * quantity + cost_new, 8)
            # calculate new total quantity
            quantity = quantity + quantity_new 
            # calculate new cost basis
            cost_basis = round(total_cost / quantity, 8) if quantity != 0 else 0
        else:   # sell or dividend
            # only quantity will be recalculated
            quantity = quantity + quantity_new 

        if quantity < 0.00001:
            quantity = 0

        self.conn.execute("INSERT OR REPLACE INTO stock_data (date, ticker, cost_basis, total_quantity) VALUES (?, ?, ?, ?)",
                            (date, ticker, cost_basis, quantity))


    def update_realized_gains(self, date, ticker, gain, quantity):
        # Fetch the latest cost_basis from stock_data
        cost_basis = self.conn.execute("""
            SELECT cost_basis FROM stock_data 
            WHERE ticker = ? AND date <= ? 
            ORDER BY date DESC LIMIT 1
        """, (ticker, date)).fetchone()

        if not cost_basis:
            print("No cost basis found for the stock")
            return
        
        gain = abs(gain) - cost_basis[0] * abs(quantity)

        existing = self.conn.execute("""
            SELECT gain FROM realized_gains WHERE date = ? AND ticker = ?
        """, (date, ticker)).fetchone()

        if existing:
            new_gain = existing[0] + gain
            self.conn.execute("""
                UPDATE realized_gains
                SET gain = ?
                WHERE date = ? AND ticker = ?
            """, (new_gain, date, ticker))
        else:
            self.conn.execute("""
                INSERT INTO realized_gains (date, ticker, gain)
                VALUES (?, ?, ?)
            """, (date, ticker, gain))

    def set_daily_cash(self, date, cash_balance):
        """
        设置某一天的现金余额。
        """
        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO daily_cash (date, cash_balance) VALUES (?, ?)
            """, (date, cash_balance))
        # print(f"Cash balance for {date} set to {cash_balance}.")

    def update_future_cost_basis_and_quantity(self, trans_date, ticker, trans_cost, trans_quantity):
        '''
        Update future cost_basis and total_quantity on stock_data after a transaction. 
        '''
        future_dates = self.conn.execute("SELECT date FROM stock_data WHERE ticker = ? AND date > ? ORDER BY date ASC",
                                         (ticker, trans_date)).fetchall()

        for future_date in future_dates:
            future_date = future_date[0]

            row = self.conn.execute("SELECT cost_basis, total_quantity FROM stock_data WHERE ticker = ? AND date = ?",
                                    (ticker, future_date)).fetchone()
            if not row:
                return
            cost_basis, quantity = row

            total_cost = round(cost_basis * quantity + trans_cost, 8)
            quantity += trans_quantity
            cost_basis = round(total_cost / quantity, 8) if quantity != 0 else 0

            self.conn.execute("UPDATE stock_data SET cost_basis = ?, total_quantity = ? WHERE date = ? AND ticker = ?",
                              (cost_basis, quantity, future_date, ticker))

    def get_previous_date(self, date_str):
        date = datetime.strptime(date_str, "%Y-%m-%d")
        previous_date = date - timedelta(days=1)
        return previous_date.strftime("%Y-%m-%d")

    def is_past_date(self, date_str):
        date = datetime.strptime(date_str, "%Y-%m-%d")
        today = Util.get_today_est_dt()
        return date < today

    def fetch_and_store_latest_price(self, ticker):
        today = Util.get_today_est_str()

        # 检查是否已有最新价格
        existing_price = self.conn.execute("""
            SELECT price FROM daily_prices WHERE date = ? AND ticker = ?
        """, (today, ticker)).fetchone()

        if existing_price:
            print(f"Price for {ticker} on {today} already exists: {existing_price[0]}")
            return existing_price[0]

        # return self.fetch_and_store_price(ticker, today)
        return Util.fetch_and_store_price(self.conn, ticker, today)

    def fetch_price(self, ticker, date, ori_date):
        try:
            row = self.conn.execute("SELECT price FROM daily_prices WHERE date = ? AND ticker = ?", (date, ticker)).fetchone()
            if row:
                print(f"Price for {ticker} on {date} already stored: {row[0]}")
                return row[0]

            stock = yf.Ticker(ticker)
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            start_date = (date_obj - timedelta(days=7)).strftime("%Y-%m-%d")
            # end_date = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
            end_date = date_obj.strftime("%Y-%m-%d")

            history = yf.download(ticker, start_date, end_date)

            if not history.empty:
                price_series = history['Close']

                if not price_series.empty:
                    price = list(round(price_series.iloc[-1], 8))[0]
                    with self.conn:
                        self.conn.execute("INSERT OR REPLACE INTO daily_prices (date, ticker, price) VALUES (?, ?, ?)",
                                          (ori_date, ticker, price))
                    print(f"Fetched and stored price for {ticker} on {ori_date}: {price}")
                    return price
                else:
                    print(f"No price data found for {ticker} on or before {date}")
                    return None
            else:
                print(f"No data available for {ticker} in the date range")
                return None

        except Exception as e:
            print(f"Error fetching price for {ticker} on {date}: {e}")

    def get_previous_cash_balance(self, date):
        cash_row = self.conn.execute("""
                  SELECT cash_balance FROM daily_cash
                  WHERE date <= ?
                  ORDER BY date DESC LIMIT 1
              """, (date,)).fetchone()
        cash_balance = cash_row[0] if cash_row else 0
        return cash_balance

    # def print_all_holding(self):
    #     dates = sorted(set(row[0] for row in self.conn.execute("SELECT date FROM transactions")))
    #     tickers = set(row[0] for row in self.conn.execute("SELECT DISTINCT ticker FROM stock_data"))
    #     date = dates[-1]

    #     for ticker in tickers:
    #         # 获取当天或最近的有效 cost_basis 和 quantity
    #         row = self.conn.execute("""
    #             SELECT cost_basis, total_quantity FROM stock_data
    #             WHERE ticker = ? AND date <= ?
    #             ORDER BY date DESC LIMIT 1
    #         """, (ticker, date)).fetchone()

    #         if row:
    #             cost_basis, quantity = row

    #             # 尝试从 daily_prices 表读取价格
    #             price_row = self.conn.execute("""
    #                 SELECT price FROM daily_prices WHERE date = ? AND ticker = ?
    #             """, (date, ticker)).fetchone()

    #             if price_row:
    #                 price = price_row[0]
    #             else:
    #                 # 如果表中没有数据，从 Yahoo Finance 下载价格
    #                 price = self.fetch_and_store_price(ticker, date)
    #             print(f'ticker: {ticker}, cost_basis: {cost_basis}, price: {price}, quantity: {quantity}')

    def close(self):
        self.conn.close()

    def load_transactions_from_csv(self, file_path):
        """
        从 CSV 文件加载交易记录，并将同一天的交易合并。
        """
        transactions = {}
        source = os.path.splitext(os.path.basename(file_path))[0]

        # 读取 CSV 文件并合并同一天的交易
        with open(file_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                date, ticker, cost, quantity = row
                cost = float(cost)
                quantity = float(quantity)
                key = (date, ticker, source)  # 以 (日期, 股票代码) 作为唯一键

                if key in transactions:
                    # 合并同一天的交易
                    transactions[key]['cost'] += cost
                    transactions[key]['quantity'] += quantity
                else:
                    transactions[key] = {'cost': cost, 'quantity': quantity}

        # 插入合并后的交易
        for (date, ticker, source), data in sorted(transactions.items(), key=lambda x: x[0][0]):
            self.add_transaction(date, ticker, data['cost'], data['quantity'], source)

        print(f"Successfully loaded transactions from {source}.")


    def load_daily_cash_from_csv(self, file_path):
        """
        从 CSV 文件加载每日现金余额。
        """
        with open(file_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                date, _, cash_balance, _ = row  # 假设格式为 yyyy-mm-dd, cash, amount, 1
                self.set_daily_cash(date, float(cash_balance))
        print(f"All daily cash balances from {file_path} have been loaded.")


    def load_transactions_from_folder(self, folder_path):
        """
        加载指定文件夹下的所有交易 CSV 文件并插入到数据库中
        """
        # 检查文件夹是否存在
        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist.")
            return

        # 遍历文件夹中的所有 CSV 文件
        for file_name in os.listdir(folder_path):
            if file_name.endswith('.csv') and file_name != 'demo_msft.csv':
                file_path = os.path.join(folder_path, file_name)
                print(f"Loading transactions from file: {file_name}")
                self.load_transactions_from_csv(file_path)

    def clear_table(self, table_name):
        """
        清空指定的表数据。

        Parameters:
        - table_name (str): 需要清空的表的名称。
        """
        try:
            with self.conn:
                self.conn.execute(f"DELETE FROM {table_name}")
            print(f"All data from table '{table_name}' has been cleared.")
        except sqlite3.Error as e:
            print(f"Error clearing table '{table_name}': {e}")

