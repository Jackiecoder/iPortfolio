import sqlite3
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pandas_market_calendars as mcal
from const_private import *
from const import *
import pytz

TEMP_PRICE_MAP = {} # DATE: {TICKER: PRICE}

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
        query = """
            SELECT gain FROM realized_gains 
            WHERE ticker = ? AND date <= ?
            ORDER BY date DESC LIMIT 1
        """
        result = self.conn.execute(query, (ticker, date)).fetchone()
        if not result:
            return 0
        return result[0] 

    def fetch_and_store_price(self, ticker, date):
        """
        从 Yahoo Finance 获取指定日期的股票价格，并存储到 daily_prices 表。
        """
        # Check if the ticker and date already exist in the daily_prices table
        query = "SELECT price FROM daily_prices WHERE ticker = ? AND date = ?"

        # if ticker is crypto and date is in TEMP_PRICE_MAP, return the price
        if ticker in CRYPTO_TICKERS and date in TEMP_PRICE_MAP:
            if ticker in TEMP_PRICE_MAP[date]:
                return TEMP_PRICE_MAP[date][ticker]

        # if ticker is not crypto, check the db
        result = self.conn.execute(query, (ticker, date)).fetchone()
        if result:
            return result[0]
        
        # fetch the price from Yahoo Finance
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
                is_market_open = Util.is_market_open(date)
                if is_market_open == False and ticker not in CRYPTO_TICKERS:
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
        today = Util.get_today_est_str()

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

class Util:
    @staticmethod
    def log(message):
        if DBUG:
            print(message)

    @staticmethod
    def fetch_and_store_price(ticker, date):
        """
        从 Yahoo Finance 获取指定日期的股票价格，并存储到 daily_prices 表。
        """
        with sqlite3.connect("portfolio.db") as db_conn:
            # if  date is in TEMP_PRICE_MAP, return the price
            if date in TEMP_PRICE_MAP:
                if ticker in TEMP_PRICE_MAP[date]:
                    return TEMP_PRICE_MAP[date][ticker]
            
            # Check if the ticker and date already exist in the daily_prices table
            query = "SELECT price FROM daily_prices WHERE ticker = ? AND date = ?"
            result = db_conn.execute(query, (ticker, date)).fetchone()
            if result:
                return result[0]
        
            # fetch the price from Yahoo Finance
            try:
                print(f"Fetching price for {ticker} on {date}...")
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                start_date = (date_obj - timedelta(days=7)).strftime("%Y-%m-%d")
                end_date = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
                Util.log(f"start_date: {start_date}, end_date: {end_date}")
                # ticker = "VOO"
                # yf.download [start_date, end_date), start_date is included, end_date is excluded
                # https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html#yfinance.download
                Util.log(f"Fetching price for {ticker} on {start_date} to {end_date}")
                history = yf.download(ticker, start=start_date, end=end_date)
                Util.log(f"history: {history}")
                if not history.empty:
                    # Get the last valid price and date
                    # Util.log(f"hitory: {history}")
                    price_series = history['Close']
                    last_valid_price = list(round(price_series.iloc[-1], 8))[0]
                    last_valid_date = price_series.index[-1].strftime("%Y-%m-%d")

                    # if market is close and ticker is not crypto, save the date, price to db
                    """
                    If it's crypto, only save price if today > date, otherwise price will fetch on the fly 
                    If it's not crypto, check if it's market open.
                        if market is close, means this date will NOT have price data, 
                            then just save the last open date, price to db
                        if market is open, means this date will HAVE price data. So the data must be fetched after close.
                            The price data on last 7 days will be fetched,
                            and the lastest price will be today's price if today is already closed, 
                            otherwise the last open date price will be saved.
                    """
                    if ticker in CRYPTO_TICKERS:
                        # if it's crypto, only save price if today > date, otherwise price will fetch on the fly
                        today = Util.get_today_est_str()
                        if today > date:
                            Util.log(f"Saving the last valid price {last_valid_price} on {date}")
                            with db_conn:
                                db_conn.execute("INSERT OR REPLACE INTO daily_prices (date, ticker, price) VALUES (?, ?, ?)",
                                                (date, ticker, last_valid_price))
                        else:
                            Util.log(f"Today is not closed yet, will not save the price data ({last_valid_price}) for {ticker} on {date}")
                            # update the TEMP_PRICE_MAP
                            if date not in TEMP_PRICE_MAP:
                                TEMP_PRICE_MAP[date] = {}
                            TEMP_PRICE_MAP[date][ticker] = last_valid_price
                    else:
                        is_market_open = Util.is_market_open(date)
                        if is_market_open == False:
                            # if market is close and ticker is not crypto, save the date, price to db
                            Util.log(f"Market is closed on {date}, saving the last valid price {last_valid_price} on {date}")
                            with db_conn:
                                db_conn.execute("INSERT OR REPLACE INTO daily_prices (date, ticker, price) VALUES (?, ?, ?)",
                                                (date, ticker, last_valid_price))
                        else:
                            # if market is open, save the last valid price and date
                            Util.log(f"Market is open on {date}, saving the last valid price {last_valid_price} on {last_valid_date}")
                            if date not in TEMP_PRICE_MAP:
                                TEMP_PRICE_MAP[date] = {}
                            TEMP_PRICE_MAP[date][ticker] = last_valid_price
                            with db_conn:
                                db_conn.execute("INSERT OR REPLACE INTO daily_prices (date, ticker, price) VALUES (?, ?, ?)",
                                                (last_valid_date, ticker, last_valid_price))

                    return last_valid_price
                Util.log(f"No price data found for {ticker} on {date}")
                return None

            except Exception as e:
                Util.log(f"Error fetching price for {ticker} on {date}: {e}")
                return None

    # @staticmethod
    # def fetch_and_store_prices_for_multiple_dates(db_conn, ticker, dates):
    #     """
    #     从 Yahoo Finance 获取指定日期列表的股票价格，并存储到 daily_prices 表。
    #     """
    #     prices = []
    #     for date in dates:
    #         price = DbUtil.fetch_and_store_price(db_conn, ticker, date)
    #         prices.append(price)
    #     return prices

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
    def calculate_ytd_date_delta_ends_today():
        """
        计算 Year-to-Date (YTD) 的日期差异，返回当前日期和当年年初的日期之间的天数差异。
        
        Returns:
        - int: 当前日期和当年年初的日期之间的天数差异
        """
        today = Util.get_today_est_dt()
        return Util.calculate_ytd_date_delta(today)
    
    @staticmethod
    def calculate_ytd_date_delta(date):
        start_of_year = datetime(date.year, 1, 1, tzinfo=date.tzinfo)
        delta = (date - start_of_year).days
        return delta

    @staticmethod
    def is_market_open(date, market="NYSE"):
        """
        Check if the given date is a market open day.
        Note: 2025-01-09 is closed.

        Parameters:
            date (str): The date in 'YYYY-MM-DD' format to check.
            market (str): The market code (default is 'NYSE').

        Returns:
            bool: True if the market is open on the given date, False otherwise.
        """
        if date == "2025-01-09":
            return False
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

    @staticmethod
    def get_today_est_str():
        """
        获取当前日期(EST 时区)。
        """
        est = pytz.timezone('US/Eastern')
        today_est = datetime.now(est).strftime("%Y-%m-%d")
        return today_est
    
    @staticmethod
    def get_current_time_est_str():
        """
        获取当前时间(EST 时区)。
        """
        est = pytz.timezone('US/Eastern')
        current_time_est = datetime.now(est).strftime("%Y-%m-%d-%H:%M:%S")
        return current_time_est
    
    @staticmethod
    def get_today_est_dt():
        """
        获取当前日期(EST 时区)。
        """
        est = pytz.timezone('US/Eastern')
        today_est = datetime.now(est)
        return today_est
    
    @staticmethod
    def get_tickers_before_date(db_conn, date):
        query = "SELECT DISTINCT ticker FROM stock_data WHERE date <= ?"
        result = db_conn.execute(query, (date,)).fetchall()
        return [row[0] for row in result]
    
    @staticmethod
    def get_categories():
        return CATEGORIES
    
    @staticmethod
    def get_cat_for_ticker(ticker):
        for cat, tickers in CATEGORIES.items():
            if ticker in tickers:
                return cat
        raise ValueError(f"Ticker {ticker} not found in any category.")
    
    @staticmethod
    def get_date_before(date:str, days:int) -> str:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        new_date = date_obj - timedelta(days=days)
        return new_date.strftime("%Y-%m-%d")