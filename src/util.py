import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pandas_market_calendars as mcal
from const_private import *
from const import *
import pytz

TEMP_PRICE_MAP = {}

class Util:
    @staticmethod
    def log(message):
        if DBUG:
            print(message)

    @staticmethod
    def fetch_and_store_price(db_conn, ticker, date):
        """
        从 Yahoo Finance 获取指定日期的股票价格，并存储到 daily_prices 表。
        """
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

                # is_market_open = Util.is_market_open(date)
                # if is_market_open == False and ticker not in CRYPTO_TICKERS:
                #     # if market is close and ticker is not crypto, save the date, price to db
                #     Util.log(f"Market is closed on {date}, saving the last valid price {last_valid_price} on {date}")
                #     with db_conn:
                #         db_conn.execute("INSERT OR REPLACE INTO daily_prices (date, ticker, price) VALUES (?, ?, ?)",
                #                         (date, ticker, last_valid_price))
                # else:
                #     # if market is open, save the last valid price and date
                #     Util.log(f"Market is open on {date}, saving the last valid price {last_valid_price} on {last_valid_date}")
                #     with db_conn:
                #         db_conn.execute("INSERT OR REPLACE INTO daily_prices (date, ticker, price) VALUES (?, ?, ?)",
                #                         (last_valid_date, ticker, last_valid_price))
                return last_valid_price
            Util.log(f"No price data found for {ticker} on {date}")
            return None

        except Exception as e:
            Util.log(f"Error fetching price for {ticker} on {date}: {e}")
            return None

    @staticmethod
    def fetch_the_latest_price(ticker):
        """
        从 Yahoo Finance 获取最新的股票价格。
        """
        try:
            Util.log(f"Fetching the latest price for {ticker}...")
            stock = yf.Ticker(ticker)
            price = stock.info['regularMarketPrice']
            Util.log(price)
            return price
        except Exception as e:
            print(f"Error fetching the latest price for {ticker}: {e}")

    @staticmethod
    def test_fetch_yf(ticker, date):
        """
        测试从 Yahoo Finance 获取股票价格。
        """
        try:
            print(f"Fetching price for {ticker} on {date}...")
            # date_obj = datetime.strptime(date, "%Y-%m-%d")
            # start_date = (date_obj - timedelta(days=7)).strftime("%Y-%m-%d")
            # end_date = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
            # print(f"start_date: {start_date}, end_date: {end_date}")
            # history = yf.download(ticker, start=start_date, end=end_date)
            # print(f"history: {history}")
            stock = yf.Ticker(ticker)
            price = stock.info['regularMarketPrice']
            print(price)
 
        except Exception as e:
            print(f"Error fetching price for {ticker} on {date}: {e}")

    @staticmethod
    def fetch_and_store_prices_for_multiple_dates(db_conn, ticker, dates):
        """
        从 Yahoo Finance 获取指定日期列表的股票价格，并存储到 daily_prices 表。
        """
        prices = []
        for date in dates:
            price = Util.fetch_and_store_price(db_conn, ticker, date)
            prices.append(price)
        return prices

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