from const import *
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

from iPortfolio_util import Util
from iPortfolio_dbAccessor import DbAccessor

class Plotter:
    def __init__(self):
        pass

    def _plot_line_chart_util(self, latest_cost, total_profits, dates, file_name, time_str):
        '''
        The logic is using the latest cost as the base cost, and adding the profit to the total value.
        '''
        total_values = [profit + latest_cost for profit in total_profits]

        # 绘制线性图
        plt.figure(figsize=(18, 9))
        plt.plot(dates, total_values, label="Total Asset Value (Excluding cash)", linestyle='-')

        colors = ['blue', 'green', 'purple']
        # 在每个点上标注数值
        for i, (x, y_value) in enumerate(zip(dates, total_values)):
            color = colors[i % len(colors)]
            y_format = f"{y_value / 1_000:.1f}K"
            plt.text(x, y_value, f"{y_format}", fontsize=16, ha='center', va='bottom', color=color)  # 标注总资产值

        # Calculate and show percentage of profit increase        
        last_value = total_values[-1]
        start_value = total_values[0]
        profit_increase_percentage = (last_value - start_value) / start_value * 100 if start_value != 0 else 0

        # 设置 x 轴为日期格式
        plt.gcf().autofmt_xdate()  # 自动调整日期显示的角度

        # 保存/显示线性图
        plt.xlabel("Date")
        plt.ylabel("Value")
        plt.title(f"Portfolio Asset Value ({time_str}), from {dates[0]} to {dates[-1]}")
        plt.legend()

        # Show percentage of profit increase under the legend
        plt.text(0.5, 0.95, f"Profit Increase: {round(last_value - start_value, 2):,} ({profit_increase_percentage:.2f}%)", fontsize=18, ha='center', va='center', transform=plt.gca().transAxes, color='purple', fontweight='bold')

        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(file_name)
        plt.show()
        plt.close()

    def plot_line_chart(self, file_name, end_date, time_period, time_str, number_of_points=NUM_OF_PLOT):
        total_values = []
        total_costs = []
        total_profits = []

        # calculate dates from ytd
        if time_period == "YTD":
            time_period = Util.calculate_ytd_date_delta(end_date)

        # 获取所有出现过的ticker列表
        tickers = DbAccessor.get_all_tickers()

        # Get dates
        dates = Util.get_evenly_spaced_dates(start_date = end_date - timedelta(days=time_period),
                                                                end_date=end_date,
                                                                num_dates=number_of_points)
        for i, date in enumerate(dates):
            day_profit = 0
            day_cost = 0
            day_value = 0
            for ticker in tickers:
                # Get prices, quantity, and cost basis
                quantity = DbAccessor.get_stock_quantity(ticker=ticker,
                                                    date=date)
                cost_basis = DbAccessor.get_cost_basis(ticker=ticker,
                                                date=date)
                
                # skip if quantity is 0
                if quantity == 0:
                    continue

                price = DbAccessor.fetch_and_store_price(ticker=ticker, date=date)
                
                value = price * quantity
                cost = cost_basis * quantity
                profit = value - cost
                day_profit += profit
                day_cost += cost
                day_value += value

            total_values.append(day_value)
            total_costs.append(day_cost)
            total_profits.append(day_profit)

            latest_cost = total_costs[-1]

        self._plot_line_chart_util(latest_cost, total_profits, dates, file_name, time_str)

    def plot_ticker_line_chart(self, file_name, ticker, time_period, time_str, number_of_points=NUM_OF_PLOT):
        total_values = []
        total_costs = []
        total_profits = []

        # calculate dates from ytd
        if time_period == "YTD":
            time_period = Util.calculate_ytd_date_delta_ends_today()

        # Get dates
        today = Util.get_today_est_dt()
        dates = Util.get_evenly_spaced_dates(start_date = today - timedelta(days=time_period),
                                                                end_date=today,
                                                                num_dates=number_of_points)
        emtpy_dates = []
        for i, date in enumerate(dates):
            # Get prices, quantity, and cost basis
            quantity = DbAccessor.get_stock_quantity(ticker=ticker, 
                                                date=date)
            cost_basis = DbAccessor.get_cost_basis(ticker=ticker,
                                            date=date)
            
            # skip if quantity is 0
            if quantity == 0:
                emtpy_dates.append(date)
                continue

            price = DbAccessor.fetch_and_store_price(ticker=ticker, date=date)

            value = price * quantity
            cost = cost_basis * quantity
            profit = value - cost

            total_values.append(value)
            total_costs.append(cost)
            total_profits.append(profit)
            latest_cost = total_costs[-1]
        
        dates = [date for date in dates if date not in emtpy_dates]
        self._plot_line_chart_util(latest_cost, total_profits, dates, file_name, time_str)

    def plot_line_chart_ends_at_today(self, file_name, time_period, time_str, number_of_points=NUM_OF_PLOT):
        self.plot_line_chart(file_name, Util.get_today_est_dt(), time_period, time_str, number_of_points)