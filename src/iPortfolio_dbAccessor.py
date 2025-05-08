import sqlite3
from const import *
from iPortfolio_util import Util
from const_private import *
from datetime import datetime, timedelta
import yfinance as yf
import inspect

TEMP_PRICE_MAP = {}

class DbAccessor:
    @staticmethod
    def get_all_tickers():
        with sqlite3.connect("portfolio.db") as db_conn:
            query = "SELECT DISTINCT ticker FROM stock_data"
            result = db_conn.execute(query).fetchall()
            return [row[0] for row in result]
    
    @staticmethod
    def get_stock_quantity(ticker, date):
        with sqlite3.connect("portfolio.db") as db_conn:
            query = "SELECT total_quantity FROM stock_data WHERE ticker = ? AND date <= ? ORDER BY date DESC LIMIT 1"
            result = db_conn.execute(query, (ticker, date)).fetchone()
            return result[0] if result else 0
        
    @staticmethod
    def get_cost_basis(ticker, date):
        with sqlite3.connect("portfolio.db") as db_conn:
            query = "SELECT cost_basis FROM stock_data WHERE ticker = ? AND date <= ? ORDER BY date DESC LIMIT 1"
            result = db_conn.execute(query, (ticker, date)).fetchone()
            return result[0] if result else 0
    
    @staticmethod
    def get_start_end_date(ticker):
        with sqlite3.connect("portfolio.db") as db_conn:
            date_range = db_conn.execute("""
                SELECT MIN(date), MAX(date) FROM stock_data WHERE ticker = ?
            """, (ticker,)).fetchone()
            first_date = date_range[0] if date_range and date_range[0] else None
            last_date = date_range[1] if date_range and date_range[1] else None

            # first_date = first_date[:10] if first_date else None
            # last_date = last_date[:10] if last_date else None

            return first_date, last_date
    
    @staticmethod
    def _save_price_to_db(db_conn, date, ticker, last_valid_price, last_valid_date):
        """
        If it's crypto, only save price if today > date, otherwise price will fetch on the fly 
        If it's not crypto, check if it's market open.
            if market is close, means this date will NOT have price data, 
                then just save the last open date, price to db
            if market is open, means this date will HAVE price data. So the data must be saved after close.
                The price data on last 7 days will be fetched,
                and the lastest price will be today's price if today is already closed, 
                otherwise the last open date price will be saved.
        """
        if ticker in CRYPTO_TICKERS:
            # if it's crypto, only save price if today > date, otherwise price will fetch on the fly
            today = Util.get_today_est_str()
            if today > date:
                db_conn.execute("INSERT OR REPLACE INTO daily_prices (date, ticker, price) VALUES (?, ?, ?)",
                                (date, ticker, last_valid_price))
            else:
                # update the TEMP_PRICE_MAP
                if date not in TEMP_PRICE_MAP:
                    TEMP_PRICE_MAP[date] = {}
                TEMP_PRICE_MAP[date][ticker] = last_valid_price
        else:
            is_market_open = Util.is_market_open(date)
            if is_market_open == False:
                # if market is close and ticker is not crypto, this date will NOT have price data,
                # We will use the last_valid_price
                db_conn.execute("INSERT OR REPLACE INTO daily_prices (date, ticker, price) VALUES (?, ?, ?)",
                                (date, ticker, last_valid_price))
            else:
                # if market is open, save the last valid price to last valid date
                if date not in TEMP_PRICE_MAP:
                    TEMP_PRICE_MAP[date] = {}
                TEMP_PRICE_MAP[date][ticker] = last_valid_price
                db_conn.execute("INSERT OR REPLACE INTO daily_prices (date, ticker, price) VALUES (?, ?, ?)",
                                (last_valid_date, ticker, last_valid_price))

    @staticmethod
    def _fetch_and_store_price_helper(db_conn, ticker, date):
        # if  date is in TEMP_PRICE_MAP, return the price
        # To avoid get on-the-fly price multiple times
        if date in TEMP_PRICE_MAP:
            if ticker in TEMP_PRICE_MAP[date]:
                return TEMP_PRICE_MAP[date][ticker]
        
        query = "SELECT price FROM daily_prices WHERE ticker = ? AND date = ?"
        result = db_conn.execute(query, (ticker, date)).fetchone()
        if result:
            return result[0]
        
        try:
            print(f"Fetching price for {ticker} on {date}...")
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            start_date = (date_obj - timedelta(days=7)).strftime("%Y-%m-%d")
            end_date = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")

            # yf.download [start_date, end_date), start_date is included, end_date is excluded
            # https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html#yfinance.download
            history = yf.download(ticker, start=start_date, end=end_date)

            # TODO: 对于crypto来说，如果是latest price, 需要不同的workflow
            #  比如现在是5/08，得到
            # Price              Close          High           Low          Open       Volume
            # Ticker           BTC-USD       BTC-USD       BTC-USD       BTC-USD      BTC-USD
            # Date                                                                           
            # 2025-05-01  96492.335938  97437.960938  94153.632812  94212.859375  32875889623
            # 2025-05-02  96910.070312  97905.898438  96375.945312  96494.968750  26421924677
            # 2025-05-03  95891.796875  96943.882812  95821.289062  96904.632812  15775154889
            # 2025-05-04  94315.976562  96318.921875  94173.429688  95877.187500  18198688416
            # 2025-05-05  94748.054688  95193.187500  93566.265625  94319.562500  25816260327
            # 2025-05-06  96802.476562  96889.179688  93399.859375  94748.382812  26551275827
            # 2025-05-08  99306.484375  99386.750000  96940.203125  97037.687500  47684251648
            # 这里应该用05/08的close price

            # Util.log_to_file(__file__, inspect.currentframe().f_lineno, "INFO", f"Price data fetched for {ticker} on {date}: \n{history}")
            # exit(0)
            if history.empty:
                raise ValueError(f"No price data found for {ticker} on {date}")

            # Get the last valid price and date
            price_series = history['Close']
            last_valid_price = list(round(price_series.iloc[-1], 8))[0]
            last_valid_date = price_series.index[-1].strftime("%Y-%m-%d")

            is_market_open = Util.is_market_open(date)
            today = Util.get_today_est_str()
            if ticker in CRYPTO_TICKERS or (ticker not in CRYPTO_TICKERS and is_market_open == True):
                # if it's crypto, only save price if today > date, otherwise price will fetch on the fly
                # if market is close, means this date will NOT have price data, 
                # then just save the last open date, price to db
                if today > date:
                    DbAccessor._save_price_to_db(db_conn, date, ticker, last_valid_price, last_valid_date)


            TEMP_PRICE_MAP[date] = TEMP_PRICE_MAP.get(date, {})
            TEMP_PRICE_MAP[date][ticker] = last_valid_price
            
            return last_valid_price

        except Exception as e:
            Util.log(f"Error fetching price for {ticker} on {date}: {e}")
            return None


    @staticmethod
    def bulk_fetch_and_store_price(ticker, dates: list):
        with sqlite3.connect("portfolio.db") as db_conn:
            prices = []
            for date in dates:
                price = DbAccessor._fetch_and_store_price_helper(db_conn, ticker, date)
                prices.append(price)
            return prices
        
    @staticmethod
    def fetch_and_store_price(ticker, date: str):
        with sqlite3.connect("portfolio.db") as db_conn:
            price = DbAccessor._fetch_and_store_price_helper(db_conn, ticker, date)
            return price
        
    @staticmethod
    def get_cash_balance():
        with sqlite3.connect("portfolio.db") as db_conn:
            cash_balance = db_conn.execute("""
                SELECT ROUND(cash_balance, 2) 
                FROM daily_cash 
                WHERE date = (SELECT MAX(date) FROM daily_cash)
            """).fetchone()
            return cash_balance[0] if cash_balance else 0.0
    
    @staticmethod
    def get_cash_balance_on_date(date):
        with sqlite3.connect("portfolio.db") as db_conn:
            cash_balance = db_conn.execute("""
                SELECT cash_balance
                FROM daily_cash 
                WHERE date <= ?
                ORDER BY date DESC LIMIT 1
            """, (date,)).fetchone()
            return cash_balance[0] if cash_balance else 0.0

    @staticmethod
    def get_realized_gain(ticker, date):
        with sqlite3.connect("portfolio.db") as db_conn:
            # Get the realized gain for the ticker on or before the date
            query = """
                SELECT gain FROM realized_gains 
                WHERE ticker = ? AND date <= ?
                ORDER BY date DESC LIMIT 1
            """
            result = db_conn.execute(query, (ticker, date)).fetchone()
            if not result:
                return 0
            return result[0] 

    @staticmethod
    def delete_daily_price(date):
        with sqlite3.connect("portfolio.db") as db_conn:
            x = db_conn.execute("DELETE FROM daily_prices WHERE date = ?", (date,))
            if x.rowcount == 0:
                print(f"No daily prices found for date: {date}")
            else:
                print(f"Deleted {x.rowcount} daily prices for date: {date}")
            db_conn.commit()