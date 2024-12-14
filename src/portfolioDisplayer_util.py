import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta
import pandas_market_calendars as mcal


class PortfolioDisplayerUtil:
    def __init__(self, db_name="portfolio.db", debug=False):
        self.conn = sqlite3.connect(db_name)
        self.debug = debug

    def log(self, message):
        if self.debug:
            print(message)

    def get_cash(self, date):
        query = "SELECT cash_balance FROM daily_cash WHERE date <= ? ORDER BY date DESC LIMIT 1"
        result = self.conn.execute(query, (date, )).fetchone()
        return result[0] if result else 0
    
    def get_stock_quantity(self, ticker, date):
        query = "SELECT total_quantity FROM stock_data WHERE ticker = ? AND date <= ? ORDER BY date DESC LIMIT 1"
        result = self.conn.execute(query, (ticker, date)).fetchone()
        return result[0] if result else 0
    
    def get_all_tickers(self):
        query = "SELECT DISTINCT ticker FROM stock_data"
        result = self.conn.execute(query).fetchall()
        return [row[0] for row in result]

    def get_cost_basis(self, ticker, date):
        query = "SELECT cost_basis FROM stock_data WHERE ticker = ? AND date <= ? ORDER BY date DESC LIMIT 1"
        result = self.conn.execute(query, (ticker, date)).fetchone()
        return result[0] if result else 0
    
    def get_ticker_date_range(self, ticker):
        date_range = self.conn.execute("""
            SELECT MIN(date), MAX(date) FROM stock_data WHERE ticker = ?
        """, (ticker,)).fetchone()
        first_date = date_range[0] if date_range and date_range[0] else None
        last_date = date_range[1] if date_range and date_range[1] else None

        # convert into YYYY-MM-DD
        first_date = first_date[:10] if first_date else None
        last_date = last_date[:10] if last_date else None

        return first_date, last_date
    
    def get_overall_date_range(self):
        # 获取所有 tickers 的最早和最晚日期
        overall_date_range = self.conn.execute("""
            SELECT MIN(date), MAX(date) FROM stock_data
        """).fetchone()
        overall_first_date = overall_date_range[0][:10] if overall_date_range and overall_date_range[0] else None
        overall_last_date = overall_date_range[1][:10] if overall_date_range and overall_date_range[1] else None

        return overall_first_date, overall_last_date
    
    def get_realized_gain(self, ticker, date):
        # if ticker not exist 
        ticker_exists = self.conn.execute("""
        SELECT 1 FROM realized_gains WHERE ticker = ?
        """, (ticker,)).fetchone()

        if not ticker_exists:
            return 0

        query = """
        SELECT SUM(gain) FROM realized_gains 
        WHERE ticker = ? AND date <= ?
        """
        result = self.conn.execute(query, (ticker, date)).fetchone()
        return result[0] if result[0] is not None else 0

    def fetch_and_store_price(self, ticker, date):
        """
        从 Yahoo Finance 获取指定日期的股票价格，并存储到 daily_prices 表。
        """
        # Check if the ticker and date already exist in the daily_prices table
        query = "SELECT price FROM daily_prices WHERE ticker = ? AND date = ?"
        result = self.conn.execute(query, (ticker, date)).fetchone()
        if result:
            return result[0]
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            start_date = (date_obj - timedelta(days=7)).strftime("%Y-%m-%d")
            end_date = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")


            self.log(f"Fetching price for {ticker} on {date}...")
            history = yf.download(ticker, start_date, end_date)
            if not history.empty:
                # Get the last valid price and date
                price_series = history['Close']
                last_valid_price = list(round(price_series.iloc[-1], 8))[0]
                last_valid_date = price_series.index[-1].strftime("%Y-%m-%d")

                # if market is close and ticker is not crypto, save the date, price to db
                is_market_open = PortfolioDisplayerUtil.is_market_open(date)
                if is_market_open == False and ticker not in ["BTC-USD", "ETH-USD", "ADA-USD"]:
                    self.log(f"Market is closed on {date}, saving the last valid price {last_valid_price} on {date}")
                    with self.conn:
                        self.conn.execute("INSERT OR REPLACE INTO daily_prices (date, ticker, price) VALUES (?, ?, ?)",
                                        (date, ticker, last_valid_price))
                else:
                    self.log(f"Market is open on {date}, saving the last valid price {last_valid_price} on {last_valid_date}")
                    with self.conn:
                        self.conn.execute("INSERT OR REPLACE INTO daily_prices (date, ticker, price) VALUES (?, ?, ?)",
                                        (last_valid_date, ticker, last_valid_price))
                return last_valid_price
            self.log(f"No price data found for {ticker} on {date}")
            return None

        except Exception as e:
            self.log(f"Error fetching price for {ticker} on {date}: {e}")
            return None

    def fetch_and_store_prices_for_multiple_dates(self, ticker, dates):
        """
        从 Yahoo Finance 获取指定日期列表的股票价格，并存储到 daily_prices 表。
        """
        prices = []
        for date in dates:
            price = self.fetch_and_store_price(ticker, date)
            prices.append(price)
        return prices

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

    def clear_daily_prices(self, date, before=False):
        """
        清除 daily_prices 表中基于日期的记录。

        Parameters:
        - date (str): 日期，格式为 "YYYY-MM-DD"
        - before (bool): 如果为 True,则删除指定日期之前的记录,否则删除指定日期之后的记录。
        """
        if before:
            query = "DELETE FROM daily_prices WHERE date < ?"
        else:
            query = "DELETE FROM daily_prices WHERE date >= ?"
        
        with self.conn:
            self.conn.execute(query, (date,))
            print(f"Cleared daily_prices records {'before' if before else 'after'} {date}")


    @staticmethod
    def get_evenly_spaced_dates(start_date, end_date, num_dates=20):
        """
        从 start_date 到 end_date 中均匀取出 num_dates 个日期点，返回长度为 num_dates 的日期列表。
        start_date 和 end_date 必须包括在内。
        
        Parameters:
        - start_date (str): 起始日期，格式为 "YYYY-MM-DD"
        - end_date (str): 结束日期，格式为 "YYYY-MM-DD"
        - num_dates (int): 需要取出的日期点数量
        
        Returns:
        - List[datetime]: 长度为 num_dates 的日期列表
        """
        # start_date = datetime.strptime(start_date, "%Y-%m-%d")
        # end_date = datetime.strptime(end_date, "%Y-%m-%d")
        
        if num_dates < 2:
            raise ValueError("num_dates must be at least 2 to include both start_date and end_date.")
        
        delta = (end_date - start_date) / (num_dates - 1)
        dates = [start_date + i * delta for i in range(num_dates)]
        dates = [date.strftime("%Y-%m-%d") for date in dates]
        
        return dates

    @staticmethod
    def calculate_ytd_date_delta():
        """
        计算 Year-to-Date (YTD) 的日期差异，返回当前日期和当年年初的日期之间的天数差异。
        
        Returns:
        - int: 当前日期和当年年初的日期之间的天数差异
        """
        today = datetime.now()
        start_of_year = datetime(today.year, 1, 1)
        delta = (today - start_of_year).days
        return delta
    
    @staticmethod
    def is_market_open(date, market="NYSE"):
        """
        Check if the given date is a market open day.

        Parameters:
            date (str): The date in 'YYYY-MM-DD' format to check.
            market (str): The market code (default is 'NYSE').

        Returns:
            bool: True if the market is open on the given date, False otherwise.
        """
        try:
            # Parse the input date
            date = pd.Timestamp(date)

            # Get the market calendar
            market_calendar = mcal.get_calendar(market)

            # Get the market schedule for the year of the given date
            schedule = market_calendar.schedule(start_date=date.strftime('%Y-01-01'), end_date=date.strftime('%Y-12-31'))

            # Check if the market is open on the given date
            return date in schedule.index
        except Exception as e:
            print(f"Error: {e}")
            return False

