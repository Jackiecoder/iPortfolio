import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta


class PortfolioDisplayerUtil:
    def __init__(self, db_name="portfolio.db"):
        self.conn = sqlite3.connect(db_name)

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
    
