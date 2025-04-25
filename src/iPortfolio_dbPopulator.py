import sqlite3
from const import TRANSACTIONS_PATH
import csv
from util import Util
import os
from enum import Enum

class TRANSACTIONS(Enum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    TRANSACTION_FEE = "transaction_fee"
    CRYPTO_FEE = "crypto_fee"
    INVALID = "invalid"

class DbPopulator:
    def __init__(self, db_name="portfolio.db"):
        self.conn = sqlite3.connect(db_name)
        self._create_tables()
        self.stock_splits = self._load_stock_splits(f'{TRANSACTIONS_PATH}stock_split.csv')
        self.transactions = {}

    def _create_tables(self):
        with self.conn:

            # Create transactions table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    date TEXT,
                    ticker TEXT,
                    source TEXT,
                    cost REAL,
                    quantity REAL,
                    cost_basis REAL,
                    PRIMARY KEY (date, ticker, source)
                )
            """)
            
            # Create daily_cash table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_cash (
                    date TEXT PRIMARY KEY,
                    cash_balance REAL
                )
            """)

            # Create daily_prices table
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

            # Create stock_data table
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

            # Create realized_gains table
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS realized_gains (
                date TEXT,
                ticker TEXT,
                gain REAL,
                PRIMARY KEY (date, ticker)
                )
            """)
    
    def _load_stock_splits(self, file_path):
        stock_splits = {}
        with open(file_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                date, ticker, before_split, after_split = row
                if ticker not in stock_splits:
                    stock_splits[ticker] = []
                stock_splits[ticker].append((date, float(before_split), float(after_split)))
        Util.log(f"Loaded stock splits: {stock_splits}")
        return stock_splits
    
    def _adjust_quantity_for_splits(self, ticker, old_date, new_date, old_quantity, old_cost_basis):
        if ticker in self.stock_splits:
            for split_date, before_split, after_split in sorted(self.stock_splits[ticker]):
                if (old_date == 0 or old_date < split_date) and new_date >= split_date:
                    Util.log(f"Adjusting quantity for split: {ticker}, {split_date}, {before_split}, {after_split}")
                    Util.log(f"Old quantity: {old_quantity}, old cost basis: {old_cost_basis}, old date: {old_date}, new date: {new_date}")
                    old_quantity *= (after_split / before_split)
                    old_cost_basis /= (after_split / before_split)

        return old_quantity, old_cost_basis

    def _validate_transaction(self, cost, quantity):
        '''
            Update realized gains if the transaction has a negative value
            cost > 0, quantity > 0: buy, update cost, quantity, cost_basis
            cost < 0, quantity < 0: sell, update cost, quantity
            cost < 0, quantity = 0: dividend, update releaized gain
            cost > 0, quantity = 0: transaction fee, update cost, cost_basis
            cost == 0, quantity < 0: crypto fee, update quantity, cost_basis

            ------------------------------------------------------------------------------------------
                            |  cost > 0                 |  cost < 0    |   cost = 0
            ------------------------------------------------------------------------------------------
            quantity > 0     |    buy                   |     X        |    X
            ------------------------------------------------------------------------------------------
            quantity = 0     |    fee (paid by money)   |  dividend    |    X
            ------------------------------------------------------------------------------------------
            quantity < 0     |     X                    |    sell      |    crpto fee (paid by crypto)
        '''
        Util.log(f"Checking transaction: {cost}, {quantity}")
        if cost > 0 and quantity > 0: 
            return TRANSACTIONS.BUY
        elif cost < 0 and quantity < 0:
            return TRANSACTIONS.SELL
        elif cost < 0 and quantity == 0:
            return TRANSACTIONS.DIVIDEND
        elif cost > 0 and quantity == 0:
            return TRANSACTIONS.TRANSACTION_FEE
        elif cost == 0 and quantity < 0:
            return TRANSACTIONS.CRYPTO_FEE
        else:
            return TRANSACTIONS.INVALID

    def _add_transaction(self, date, ticker, cost, quantity, source):
        # Since the caller already merge the transactions with same date, ticker and source,
        # we don't need to check for duplicates here.
        cost_basis = cost / quantity if quantity != 0 else 0
        self.conn.execute("""
            INSERT INTO transactions (date, ticker, source, cost, quantity, cost_basis)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (date, ticker, source, cost, quantity, cost_basis))

    def _update_stock_data(self, date, ticker, source, tran_cost, tran_quantity):
        transaction_type = self._validate_transaction(tran_cost, tran_quantity)

        if transaction_type == TRANSACTIONS.INVALID:
            raise ValueError(f"Invalid transaction: {date}, {ticker}, {source}, {tran_cost}, {tran_quantity}")

        row = self.conn.execute("SELECT cost_basis, total_quantity, date FROM stock_data WHERE ticker = ? AND date <= ? ORDER BY date DESC LIMIT 1",
                                (ticker, date)).fetchone()
        
        cost_basis, quantity, prev_date = 0, 0, 0 # 默认值
        if row:
            cost_basis, quantity, prev_date = row

        # Adjust quantity for splits
        quantity, cost_basis = self._adjust_quantity_for_splits(ticker=ticker, 
                                                   old_date=prev_date, 
                                                   new_date=date, 
                                                   old_quantity=quantity,
                                                   old_cost_basis=cost_basis)
        
        Util.log(f"Adjusted quantity: {quantity}, cost basis: {cost_basis}")

        if transaction_type == TRANSACTIONS.BUY:
            # BUY, update total quantity, cost_basis 
            total_cost = round(cost_basis * quantity + tran_cost, 8)
            quantity += tran_quantity
            cost_basis = round(total_cost / quantity, 8) if quantity != 0 else 0
            Util.log(f"Process BUY operation. Total cost: {total_cost}, quantity: {quantity}")
        elif transaction_type == TRANSACTIONS.SELL:
            # SELL, update quantity 
            quantity += tran_quantity
            Util.log(f"Process SELL operation. Quantity: {quantity}")
        elif transaction_type == TRANSACTIONS.DIVIDEND:
            # DIVIDEND, update realized_gain only
            pass
        elif transaction_type == TRANSACTIONS.TRANSACTION_FEE:
            # TRANSACTION FEE, update cost_basis and quantity
            total_cost = round(cost_basis * quantity + tran_cost, 8)
            quantity += tran_quantity
            cost_basis = round(total_cost / quantity, 8) if quantity != 0 else 0
            Util.log(f"Process TRANSACTION FEE operation. Total cost: {total_cost}, cost basis: {cost_basis}")
        elif transaction_type == TRANSACTIONS.CRYPTO_FEE:
            # CRYPTO FEE, update quantity and cost_basis
            total_cost = round(cost_basis * quantity + tran_cost, 8)
            quantity += tran_quantity
            cost_basis = round(total_cost / quantity, 8) if quantity != 0 else 0
            Util.log(f"Process CRYPTO FEE operation. Quantity: {quantity}")
        else:
            raise ValueError(f"Invalid transaction: {date}, {ticker}, {tran_cost}, {tran_quantity}")
        
        # Update the stock_data tables
        if quantity < 0.00001:
            quantity = 0

        self.conn.execute("INSERT OR REPLACE INTO stock_data (date, ticker, cost_basis, total_quantity) VALUES (?, ?, ?, ?)",
                            (date, ticker, cost_basis, quantity))

    def _update_realized_gains(self, date, ticker, source, tran_cost, tran_quantity):
        transaction_type = self._validate_transaction(tran_cost, tran_quantity)
        if transaction_type == TRANSACTIONS.INVALID:
            raise ValueError(f"Invalid transaction: {date}, {ticker}, {source}, {tran_cost}, {tran_quantity}")

        if transaction_type not in (TRANSACTIONS.SELL, TRANSACTIONS.DIVIDEND):
            return
        
        cost_basis = 0
        if transaction_type == TRANSACTIONS.SELL:
            # Fetch the latest cost_basis from stock_data
            row = self.conn.execute("""
                SELECT cost_basis FROM stock_data 
                WHERE ticker = ? AND date <= ? 
                ORDER BY date DESC LIMIT 1
            """, (ticker, date)).fetchone()
            if not row:
                print("No cost basis found for the stock")
                return
            cost_basis = row[0]
        
        net_income = abs(tran_cost) - cost_basis * abs(tran_quantity)

        existing = self.conn.execute("""
            SELECT gain FROM realized_gains WHERE ticker = ? ORDER BY date DESC LIMIT 1
        """, (ticker,)).fetchone()

        net_income += existing[0] if existing else 0
        self.conn.execute("""
            INSERT OR REPLACE INTO realized_gains (date, ticker, gain)
            VALUES (?, ?, ?)
        """, (date, ticker, net_income))

    def _update_future_cost_basis_and_quantity(self, trans_date, ticker, trans_cost, trans_quantity):
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

    def _set_daily_cash(self, date, cash_balance):
        """
        设置某一天的现金余额。
        """
        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO daily_cash (date, cash_balance) VALUES (?, ?)
            """, (date, cash_balance))
        # print(f"Cash balance for {date} set to {cash_balance}.")
        

    def load_transactions_from_csv(self, file_path):
        """
        从 CSV 文件加载交易记录，并将同一天的交易合并。
        """
        try:
            source = os.path.splitext(os.path.basename(file_path))[0]

            with open(file_path, newline='') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    date, ticker, cost, quantity = row
                    cost = float(cost)
                    quantity = float(quantity)
                    key = (date, ticker, source)  

                    # Merge transactions with the same date, ticker and source
                    if key in self.transactions:
                        self.transactions[key]['cost'] += cost
                        self.transactions[key]['quantity'] += quantity
                    else:
                        self.transactions[key] = {'cost': cost, 'quantity': quantity}
        except Exception as e:
            exit(f"Error reading CSV file {file_path}: {e}")

    def populate_transaction_db(self):
        # Insert transactions into the database
        transactions = self.transactions
        for (date, ticker, source), data in sorted(transactions.items(), key=lambda x: x[0][0]):
            Util.log(f"Processing transaction: {date}, {ticker}, {source}, {data['cost']}, {data['quantity']}")
            self._add_transaction(date, ticker, data['cost'], data['quantity'], source)
            self._update_stock_data(date, ticker, source, data['cost'], data['quantity'])
            self._update_realized_gains(date, ticker, source, data['cost'], data['quantity'])

            # # For sell and dividend, update realized gains and change the quantity of stock_data only
            # if data['cost'] < 0:
            #     # only update realized gains and the stock data holding
            #     self._update_realized_gains(date, ticker, source, data['cost'], data['quantity'])
            #     self._update_stock_data(date, ticker, source, data['cost'], data['quantity'])
            # elif cost > 0:
            #     self._update_stock_data(date, ticker, source, data['cost'], data['quantity'])
            #     # self._update_future_cost_basis_and_quantity(date, ticker, cost, quantity)
            # else:
            #     # cost == 0
            #     raise ValueError(f"cost cannot be 0: {date}, {ticker}, {source}, {cost}, {data['quantity']}")

        print(f"Successfully loaded transactions")
        
    def load_daily_cash_from_csv(self, file_path):
        """
        从 CSV 文件加载每日现金余额。
        """
        with open(file_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                date, _, cash_balance, _ = row  # 假设格式为 yyyy-mm-dd, cash, amount, 1
                self._set_daily_cash(date, float(cash_balance))
        print(f"Successfully loaded daily cash from {file_path}")

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
                Util.log(f"Loading transactions from file: {file_name}")
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

    def close(self):
        self.conn.close()

    def verify_table_size(self):
        with self.conn:
            cursor = self.conn.execute("SELECT COUNT(*) FROM transactions")
            count = cursor.fetchone()[0]
            print(f"Number of records in transactions table: {count}")
            cursor = self.conn.execute("SELECT COUNT(*) FROM stock_data")
            count = cursor.fetchone()[0]
            print(f"Number of records in stock_data table: {count}")
            cursor = self.conn.execute("SELECT COUNT(*) FROM daily_cash")
            count = cursor.fetchone()[0] 
            print(f"Number of records in daily_cash table: {count}")
            cursor = self.conn.execute("SELECT COUNT(*) FROM daily_prices")
            count = cursor.fetchone()[0]
            print(f"Number of records in daily_prices table: {count}")
            cursor = self.conn.execute("SELECT COUNT(*) FROM realized_gains")
            count = cursor.fetchone()[0]
            print(f"Number of records in realized_gains table: {count}")