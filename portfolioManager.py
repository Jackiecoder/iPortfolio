import sqlite3
import yfinance as yf
import csv
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pytz
import os
import matplotlib.dates as mdates


class PortfolioManager:
    def __init__(self, db_name="portfolio.db"):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()

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
            CREATE TABLE IF NOT EXISTS gains (
                    date TEXT,
                    realized_gain REAL,
                    unrealized_gain REAL,
                    PRIMARY KEY (date)
                )
            """)

    def add_transaction(self, date, ticker, cost, quantity, source):
        # 检查是否已经存在相同的记录
        existing = self.conn.execute("""
            SELECT 1 FROM transactions WHERE date = ? AND ticker = ? AND source = ?
        """, (date, ticker, source)).fetchone()

        if existing:
            # print(f"Transaction for {ticker} on {date} already exists. Skipping insertion.")
            return

        # 计算成本基础
        # per_unit_cost = round(cost / quantity, 8) if quantity != 0 else 0
        row = self.conn.execute("SELECT cost_basis, total_quantity FROM stock_data WHERE ticker = ? AND date <= ? ORDER BY date DESC LIMIT 1",
                                (ticker, date)).fetchone()
        
        current_cost_basis, current_quantity = 0, 0 # 默认值
        if row:
            current_cost_basis, current_quantity = row

        total_cost = round(current_cost_basis * current_quantity + cost, 8)
        new_quantity = current_quantity + quantity
        new_cost_basis = round(total_cost / new_quantity, 8) if new_quantity != 0 else 0
        # else:
        #     new_cost_basis = per_unit_cost
        #     new_quantity = quantity

        # 插入新交易记录
        with self.conn:
            self.conn.execute("INSERT INTO transactions (date, ticker, source, cost, quantity) VALUES (?, ?, ?, ?, ?)",
                              (date, ticker, source, cost, quantity))
            self.conn.execute("INSERT OR REPLACE INTO stock_data (date, ticker, cost_basis, total_quantity) VALUES (?, ?, ?, ?)",
                              (date, ticker, new_cost_basis, new_quantity))
            self.update_future_cost_basis_and_quantity(date, ticker, cost, quantity)

        # 获取并存储当天价格
        # previous_date = self.get_previous_date(date)
        # if self.is_past_date(previous_date):
        #     self.fetch_price_without_dbwrite(ticker, previous_date, date)
        # else:
        #     print(f"Cannot fetch price for {ticker} on {previous_date} because it is a future date.")

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

        # row = self.conn.execute("SELECT cost_basis, total_quantity FROM stock_data WHERE ticker = ? AND date = ?",
        #                         (ticker, date)).fetchone()
        # if not row:
        #     return
        # cost_basis, quantity = row

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


    # def update_future_cost_basis_and_quantity(self, date, ticker):
    #     future_dates = self.conn.execute("SELECT date FROM stock_data WHERE ticker = ? AND date > ? ORDER BY date ASC",
    #                                      (ticker, date)).fetchall()

    #     row = self.conn.execute("SELECT cost_basis, total_quantity FROM stock_data WHERE ticker = ? AND date = ?",
    #                             (ticker, date)).fetchone()
    #     if not row:
    #         return

    #     cost_basis, quantity = row

    #     for future_date in future_dates:
    #         future_date = future_date[0]
    #         trans_rows = self.conn.execute("SELECT cost, quantity FROM transactions WHERE date = ? AND ticker = ?",
    #                                        (future_date, ticker)).fetchall()

    #         for trans_cost, trans_quantity in trans_rows:
    #             total_cost = round(cost_basis * quantity + trans_cost, 8)
    #             quantity += trans_quantity
    #             cost_basis = round(total_cost / quantity, 8) if quantity != 0 else 0

    #         self.conn.execute("UPDATE stock_data SET cost_basis = ?, total_quantity = ? WHERE date = ? AND ticker = ?",
    #                           (cost_basis, quantity, future_date, ticker))

    def get_previous_date(self, date_str):
        date = datetime.strptime(date_str, "%Y-%m-%d")
        previous_date = date - timedelta(days=1)
        return previous_date.strftime("%Y-%m-%d")

    def is_past_date(self, date_str):
        date = datetime.strptime(date_str, "%Y-%m-%d")
        today = datetime.now()
        return date < today

    def fetch_price_without_dbwrite(self, ticker, date):
        stock = yf.Ticker(ticker)
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        start_date = (date_obj - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")

        history = yf.download(ticker, start_date, end_date)
        if not history.empty:
            price_series = history['Close']
            if not price_series.empty:
                price = list(round(price_series.iloc[-1], 8))[0]
                return price
            else:
                print(f"No price data found for {ticker} on or before {date}")
                return None
        else:
            print(f"No data available for {ticker} in the date range")
            return None

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

    def fetch_price(self, ticker, date, ori_date):
        try:
            row = self.conn.execute("SELECT price FROM daily_prices WHERE date = ? AND ticker = ?", (date, ticker)).fetchone()
            if row:
                print(f"Price for {ticker} on {date} already stored: {row[0]}")
                return row[0]

            stock = yf.Ticker(ticker)
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            start_date = (date_obj - timedelta(days=7)).strftime("%Y-%m-%d")
            end_date = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")

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

    def print_all_holding(self):
        dates = sorted(set(row[0] for row in self.conn.execute("SELECT date FROM transactions")))
        tickers = set(row[0] for row in self.conn.execute("SELECT DISTINCT ticker FROM stock_data"))
        date = dates[-1]

        for ticker in tickers:
            # 获取当天或最近的有效 cost_basis 和 quantity
            row = self.conn.execute("""
                SELECT cost_basis, total_quantity FROM stock_data
                WHERE ticker = ? AND date <= ?
                ORDER BY date DESC LIMIT 1
            """, (ticker, date)).fetchone()

            if row:
                cost_basis, quantity = row

                # 尝试从 daily_prices 表读取价格
                price_row = self.conn.execute("""
                    SELECT price FROM daily_prices WHERE date = ? AND ticker = ?
                """, (date, ticker)).fetchone()

                if price_row:
                    price = price_row[0]
                else:
                    # 如果表中没有数据，从 Yahoo Finance 下载价格
                    price = self.fetch_and_store_price(ticker, date)
                print(f'ticker: {ticker}, cost_basis: {cost_basis}, price: {price}, quantity: {quantity}')



    def plot_asset_value_vs_cost(self):
        dates = sorted(set(row[0] for row in self.conn.execute("SELECT date FROM transactions")))
        total_values = []
        total_costs = []

        # 获取所有出现过的ticker列表
        tickers = set(row[0] for row in self.conn.execute("SELECT DISTINCT ticker FROM stock_data"))

        for date in dates:
            total_value = 0
            total_cost = 0

            # 获取现金余额
            # cash_balance = self.get_previous_cash_balance(date)
            # total_value += cash_balance
            # total_cost += cash_balance

            for ticker in tickers:
                # 获取当天或最近的有效 cost_basis 和 quantity
                row = self.conn.execute("""
                    SELECT cost_basis, total_quantity FROM stock_data
                    WHERE ticker = ? AND date <= ?
                    ORDER BY date DESC LIMIT 1
                """, (ticker, date)).fetchone()

                if row:
                    cost_basis, quantity = row
                    total_cost += cost_basis * quantity

                    # 尝试从 daily_prices 表读取价格
                    price_row = self.conn.execute("""
                        SELECT price FROM daily_prices WHERE date = ? AND ticker = ?
                    """, (date, ticker)).fetchone()

                    if price_row:
                        price = price_row[0]
                    else:
                        # 如果表中没有数据，从 Yahoo Finance 下载价格
                        price = self.fetch_and_store_price(ticker, date)
                        # # 获取价格信息
                        # price = self.fetch_price_without_dbwrite(ticker, date)
                    if price is not None and quantity is not None:
                        total_value += price * quantity

            total_values.append(total_value)
            total_costs.append(total_cost)

        # 转换日期为 datetime 对象
        dates = [datetime.strptime(d, "%Y-%m-%d") for d in dates]
        filtered_data = [(d, v, c) for d, v, c in zip(dates, total_values, total_costs) if d >= datetime(2024, 1, 1)]

        if not filtered_data:
            print("No data available from 2024-01-01 onwards.")
            return

        dates, total_values, total_costs = zip(*filtered_data)

        # 绘制线性图
        plt.figure(figsize=(12, 6))
        plt.plot(dates, total_values, label="Total Asset Value (Including Cash)", linestyle='-')
        plt.plot(dates, total_costs, label="Total Cost (Excluding Cash)", linestyle='-')
        # 在每个点上标注数值
        for i, (x, y_value, y_cost) in enumerate(zip(dates, total_values, total_costs)):
            if i % 10 == 0:  # 每 10 个点标注一次
                plt.text(x, y_value, f"{y_value:.2f}", fontsize=8, ha='center', va='bottom', color='green')  # 标注总资产值
                plt.text(x, y_cost, f"{y_cost:.2f}", fontsize=8, ha='center',  va='top', color='blue')    # 标注总成本

        # 设置 x 轴为日期格式
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.gcf().autofmt_xdate()  # 自动调整日期显示的角度

        # 保存/显示线性图
        plt.xlabel("Date")
        plt.ylabel("Value")
        plt.title("Portfolio Asset Value vs Total Cost Over Time")
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        file_name = "/content/drive/MyDrive/Asset/portfolio_line_chart.png"
        plt.savefig(file_name)
        plt.show()


    def plot_pie_chart_with_cash(self, file_name="/content/drive/MyDrive/Asset/portfolio_pie_chart.png"):
        """
        绘制一个饼图，显示最新的 stock_data，包括现金余额。
        """
        # 获取每个 ticker 的最新数据
        stock_data = self.conn.execute("""
            SELECT ticker, total_quantity, cost_basis, date FROM stock_data
            WHERE (ticker, date) IN (
                SELECT ticker, MAX(date) FROM stock_data GROUP BY ticker
            )
        """).fetchall()

        # 获取现金余额
        latest_cash_date = self.conn.execute("SELECT MAX(date) FROM daily_cash").fetchone()[0]
        cash_row = self.conn.execute("""
            SELECT cash_balance FROM daily_cash WHERE date = ?
        """, (latest_cash_date,)).fetchone()
        cash_balance = cash_row[0] if cash_row else 0

        # 计算各股票的总价值
        labels = []
        values = []

        for ticker, quantity, cost_basis, date in stock_data:
            # 获取最新价格
            # price_row = self.conn.execute("""
            #     SELECT price FROM daily_prices WHERE date = ? AND ticker = ?
            # """, (date, ticker)).fetchone()
            # latest_price = price_row[0] if price_row else 0

            # 获取最新价格并尝试存储到 daily_prices 表
            latest_price = self.fetch_and_store_latest_price(ticker)

            # 计算总价值
            total_value = latest_price * quantity
            if total_value > 0:
                labels.append(ticker)
                values.append(total_value)

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

    def close(self):
        self.conn.close()

    # def load_transactions_from_csv(self, file_path):
    #     """
    #     加载单个 CSV 文件中的交易记录
    #     """
    #     with open(file_path, newline='') as csvfile:
    #         reader = csv.reader(csvfile)
    #         for row in reader:
    #             print(row)
    #             date, ticker, cost, quantity = row
    #             self.add_transaction(date, ticker, float(cost), float(quantity))
    #     print(f"All transactions from {file_path} have been loaded.")

    def load_transactions_from_csv(self, file_path):
        """
        从 CSV 文件加载交易记录，并将同一天的交易合并。
        """
        transactions = {}
        source = os.path.splitext(os.path.basename(file_path))[0]
        print(source)

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
        for (date, ticker, source), data in transactions.items():
            self.add_transaction(date, ticker, data['cost'], data['quantity'], source)

        print(f"All transactions from {file_path} have been loaded with daily aggregation.")


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
            if file_name.endswith('.csv'):
                file_path = os.path.join(folder_path, file_name)
                print(f"Loading transactions from file: {file_path}")
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

