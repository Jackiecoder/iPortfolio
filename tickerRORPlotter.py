import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from portfolioDisplayer_util import PortfolioDisplayerUtil

class TickerRORPlotter:
    def __init__(self, db_name='portfolio.db'):
        self.conn = sqlite3.connect(db_name)

    def get_all_tickers(self):
        pf_util = PortfolioDisplayerUtil()
        tickers = pf_util.get_all_tickers()
        return tickers

    def fetch_ticker_data(self, ticker):
        query = """
            SELECT date, total_quantity, cost_basis 
            FROM stock_data 
            WHERE ticker = ? 
            ORDER BY date
        """
        df = pd.read_sql_query(query, self.conn, params=(ticker,))
        return df

    def fetch_daily_prices(self, ticker):
        query = """
            SELECT date, price 
            FROM daily_prices 
            WHERE ticker = ? 
            ORDER BY date
        """
        df = pd.read_sql_query(query, self.conn, params=(ticker,))
        return df
    
    def downsample_data(self, df, max_points=20):
        # if len(df) > max_points:
        #     step = len(df) / max_points
        #     indices = [int(i * step) for i in range(max_points)]
        #     df = df.iloc[indices]
        # return df
        if len(df) > max_points:
            # Always include the first and last points
            indices = [0] + [int(i * (len(df) - 1) / (max_points - 1)) for i in range(1, max_points - 1)] + [len(df) - 1]
            df = df.iloc[indices]
        return df

    def calculate_ror(self, ticker):
        stock_data = self.fetch_ticker_data(ticker)
        # print(ticker)
        # print(stock_data)
        daily_prices = self.fetch_daily_prices(ticker)

        if stock_data.empty or daily_prices.empty:
            print(f"No data available for ticker {ticker}")
            return None

        # Merge stock data with daily prices
        merged_data = pd.merge(stock_data, daily_prices, on='date')
        merged_data['total_value'] = merged_data['total_quantity'] * merged_data['price']
        merged_data['total_cost'] = merged_data['total_quantity'] * merged_data['cost_basis']
        merged_data['unrealized_gain'] = merged_data['total_value'] - merged_data['total_cost']
        merged_data['rate_of_return'] = (merged_data['unrealized_gain'] / merged_data['total_cost']) * 100
        print(f"Rate of return for {ticker}")
        print(merged_data)

        return merged_data

    def plot_ror(self, ticker):
        file_name=f"results/{ticker}_ror_chart.png"
        ror_data = self.calculate_ror(ticker)
        if ror_data is None:
            return
        
        # Downsample data to at most 20 points
        ror_data = self.downsample_data(ror_data)

        plt.figure(figsize=(12, 6))
        plt.plot(ror_data['date'], ror_data['rate_of_return'], marker='o', linestyle='-', color='b')
        plt.xlabel('Date')
        plt.ylabel('Rate of Return (%)')
        plt.title(f'Rate of Return for {ticker}')
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        # plt.savefig(file_name)
        plt.show()

    def plot_all_tickers(self):
        tickers = self.get_all_tickers()
        for ticker in tickers:
            self.plot_ror(ticker)

    def close(self):
        self.conn.close()

# Example usage
if __name__ == "__main__":
    plotter = TickerRORPlotter()
    plotter.plot_ror('AAPL')
    plotter.close()