import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta

class Displayer:
    def __init__(self, db_name="portfolio.db"):
        self.conn = sqlite3.connect(db_name)

    def get_latest_cash(self):
        query = "SELECT cash_balance FROM daily_cash ORDER BY date DESC LIMIT 1"
        result = self.conn.execute(query).fetchone()
        return result[0] if result else 0


    def get_latest_stock_quantity(self, ticker):
        query = "SELECT total_quantity FROM stock_data WHERE ticker = ? ORDER BY date DESC LIMIT 1"
        result = self.conn.execute(query, (ticker,)).fetchone()
        return result[0] if result else 0

    def get_all_tickers(self):
        query = "SELECT DISTINCT ticker FROM stock_data"
        result = self.conn.execute(query).fetchall()
        return [row[0] for row in result]

    def get_cost_basis(self, ticker):
        query = "SELECT cost_basis FROM stock_data WHERE ticker = ? ORDER BY date DESC LIMIT 1"
        result = self.conn.execute(query, (ticker,)).fetchone()
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

    def calculate_annualized_return(self, start_date, end_date, value, cost):
        duration_years = max((datetime.strptime(end_date, "%Y-%m-%d") \
                            - datetime.strptime(start_date, "%Y-%m-%d")).days / 365.25, 1)  # 不足一年按一年算
        if cost > 0:
            annualized_return = ((value / cost) ** (1 / duration_years) - 1) * 100
        else:
            annualized_return = None

        return annualized_return

    def calculate_overall_annualized_return(self, start_date, end_date, value, cost):
        duration_years = max((datetime.strptime(end_date, "%Y-%m-%d") \
                            - datetime.strptime(start_date, "%Y-%m-%d")).days / 365.25, 1)
        if duration_years >= 1 and cost > 0:
            overall_annualized_return = ((value / cost) ** (1 / duration_years) - 1) * 100
        else:
            overall_annualized_return = None

        return overall_annualized_return


    def fetch_and_store_price(self, ticker, date):
        """
        从 Yahoo Finance 获取指定日期的股票价格，并存储到 daily_prices 表。
        """
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


    def calculate_rate_of_return(self):
        """
        计算每个 ticker 和总资产的收益率，并返回表格格式的数据。

        返回列包括：
        - Latest Price: 最新价格
        - Total Holding: 总持仓数量
        - Total Value: 总价值 (最新价格 * 总持仓数量)
        - Total Cost: 总成本
        - Rate of Return: 总价值 / 总成本
        """
        tickers = set(row[0] for row in self.conn.execute("SELECT DISTINCT ticker FROM stock_data"))
        data = []

        total_cost = 0
        total_value = 0

        # 获取最新现金余额
        latest_cash_date = self.conn.execute("SELECT MAX(date) FROM daily_cash").fetchone()[0]
        cash_row = self.conn.execute("""
                SELECT cash_balance FROM daily_cash WHERE date = ?
            """, (latest_cash_date,)).fetchone()
        cash_balance = round(cash_row[0], 2) if cash_row else 0

        for ticker in tickers:
            # 获取最新价格并尝试存储到 daily_prices 表
            latest_price = self.fetch_and_store_latest_price(ticker)

            # 获取最新一天的持仓数量和成本基础
            stock_row = self.conn.execute("""
                SELECT total_quantity, cost_basis FROM stock_data WHERE ticker = ? ORDER BY date DESC LIMIT 1
            """, (ticker,)).fetchone()
            total_quantity_ticker = stock_row[0] if stock_row[0] else 0
            cost_basis = stock_row[1] if stock_row[1] else 0
            total_cost_ticker = cost_basis * total_quantity_ticker

            # 计算总价值和收益率
            total_value_ticker = (latest_price * total_quantity_ticker) if latest_price else 0
            profit = total_value_ticker - total_cost_ticker
            rate_of_return = ((total_value_ticker / total_cost_ticker) - 1 ) * 100 if total_cost_ticker > 0 else None

            # 获取日期范围
            date_range = self.conn.execute("""
                SELECT MIN(date), MAX(date) FROM stock_data WHERE ticker = ?
            """, (ticker,)).fetchone()
            first_date = date_range[0] if date_range and date_range[0] else None
            last_date = date_range[1] if date_range and date_range[1] else None

            # 格式化为 YYYY-MM-DD
            first_date = first_date[:10] if first_date else None
            last_date = last_date[:10] if last_date else None

            # 计算年均收益率
            date_range = self.conn.execute("""
                SELECT MIN(date), MAX(date) FROM stock_data WHERE ticker = ?
            """, (ticker,)).fetchone()
            if date_range and date_range[0] and date_range[1]:
                duration_years = max((datetime.strptime(date_range[1], "%Y-%m-%d") \
                                      - datetime.strptime(date_range[0], "%Y-%m-%d")).days / 365.25, 1)  # 不足一年按一年算
                if total_cost_ticker > 0:
                    annualized_return = ((total_value_ticker / total_cost_ticker) ** (1 / duration_years) - 1) * 100
                else:
                    annualized_return = None
            else:
                annualized_return = None

            # 保留两位小数
            latest_price = round(latest_price, 2)
            cost_basis = round(cost_basis, 2)
            total_quantity_ticker = round(total_quantity_ticker, 2)
            total_value_ticker = round(total_value_ticker, 2)
            total_cost_ticker = round(total_cost_ticker, 2)
            profit = round(profit, 2) if profit is not None else None
            rate_of_return = round(rate_of_return, 2) if rate_of_return is not None else None
            annualized_return = round(annualized_return, 2) if annualized_return is not None else None

            # 添加到结果中
            data.append({
                "Ticker": ticker,
                "Latest Price": latest_price,
                "Ave Cost Basis": cost_basis,
                "Total Holding": total_quantity_ticker,
                "Total Value": total_value_ticker,
                "Total Cost": total_cost_ticker,
                "Profit": profit,
                "Rate of Return (%)": rate_of_return,
                "Portfolio (%)": None,  # 后续计算
                "First Date": first_date,
                "Last Date": last_date,
                "Annualized RoR (%)": annualized_return
            })

            # 累计总计数据
            total_cost += total_cost_ticker
            total_value += total_value_ticker


        # 获取所有 tickers 的最早和最晚日期
        overall_date_range = self.conn.execute("""
            SELECT MIN(date), MAX(date) FROM stock_data
        """).fetchone()

        if overall_date_range and overall_date_range[0] and overall_date_range[1]:
            overall_first_date = overall_date_range[0]
            overall_last_date = overall_date_range[1]
            overall_first_date_dt = datetime.strptime(overall_first_date, "%Y-%m-%d")
            overall_last_date_dt = datetime.strptime(overall_last_date, "%Y-%m-%d")
            overall_duration_years = (overall_last_date_dt - overall_first_date_dt).days / 365.25
            if overall_duration_years >= 1 and total_cost > 0:
                overall_annualized_return = ((total_value / total_cost) ** (1 / overall_duration_years) - 1) * 100
            else:
                overall_annualized_return = None
        else:
            overall_annualized_return = None
        overall_first_date = overall_date_range[0][:10] if overall_date_range and overall_date_range[0] else None
        overall_last_date = overall_date_range[1][:10] if overall_date_range and overall_date_range[1] else None

        # 保留两位小数
        overall_annualized_return = round(overall_annualized_return, 2) if overall_annualized_return is not None else None

        # 计算总计行
        total_profit = total_value - total_cost
        total_rate_of_return = ((total_value / total_cost) - 1) * 100 if total_cost > 0 else None

        total_profit = round(total_profit, 2)
        total_rate_of_return = round(total_rate_of_return, 2) if total_rate_of_return is not None else None

        # 添加 Portfolio (%) 列
        for row in data:
            row["Portfolio (%)"] = round((row["Total Value"] / (total_value + cash_balance)) * 100, 2) if total_value > 0 else 0

        # 添加 Cash 行
        data.append({
            "Ticker": "Cash",
            "Latest Price": None,
            "Total Holding": None,
            "Ave Cost Basis": None,
            "Total Value": cash_balance,
            "Total Cost": None,
            "Profit": None,
            "Rate of Return (%)": None,
            "Portfolio (%)": round((cash_balance / (total_value + cash_balance)) * 100, 2) if cash_balance > 0 else 0,
            "First Date": None,
            "Last Date": None,
            "Annualized RoR (%)": None
        })

        data.append({
            "Ticker": "Total (w/o Cash)",
            "Latest Price": None,
            "Ave Cost Basis": None,
            "Total Holding": None,
            "Total Value": round(total_value, 2),
            "Total Cost": round(total_cost, 2),
            "Profit": total_profit,
            "Rate of Return (%)": total_rate_of_return,
            "Portfolio (%)": 100.0,  # 总计行为 100%
            "First Date": overall_first_date,
            "Last Date": overall_last_date,
            "Annualized RoR (%)": overall_annualized_return
        })


        # 转换为 DataFrame
        df = pd.DataFrame(data)

        # 确保 Profit 列为浮点数，并填充空值
        df["Profit"] = pd.to_numeric(df["Profit"], errors='coerce').fillna(0)

        # 按 Profit 降序排序，保留 "Total" 行在最后
        sorted_df = pd.concat([
            df[df["Ticker"] != "Total (w/o Cash)"].sort_values(by="Profit", ascending=False),
            df[df["Ticker"] == "Total (w/o Cash)"]
        ], ignore_index=True)

        # # 转换为 DataFrame
        # df = pd.DataFrame(data)

        # # 按 Profit 降序排序，保留 "Total" 行在最后
        # df["Profit"] = df["Profit"].astype(float)
        # sorted_df = pd.concat([
        #     df[df["Ticker"] != "Total"].sort_values(by="Profit", ascending=False, key=lambda col: col.astype(float)),
        #     df[df["Ticker"] == "Total"]
        # ], ignore_index=True)

        # 简化版表格
        summary_df = sorted_df[["Ticker", "Portfolio (%)", "Rate of Return (%)", "First Date", "Last Date", "Annualized RoR (%)"]]

        # 按 Portfolio (%) 降序排序，保留 Total 行在最后
        summary_df = pd.concat([
            summary_df[summary_df["Ticker"] != "Total (w/o Cash)"].sort_values(by="Portfolio (%)", ascending=False),
            summary_df[summary_df["Ticker"] == "Total (w/o Cash)"]
        ], ignore_index=True)

        return sorted_df, summary_df


    def calculate_rate_of_return_v2(self):
        tickers = self.get_all_tickers()
        ror_data = []
        total_cost, total_value = 0, 0

        for ticker in tickers:
            latest_quantity_ticker = self.get_latest_stock_quantity(ticker)
            todays_price = self.fetch_and_store_latest_price(ticker)
            latest_cash = self.get_latest_cash()

            total_value_ticker = latest_quantity_ticker * todays_price 
            cost_basis = self.get_cost_basis(ticker)
            total_cost_ticker = cost_basis * latest_quantity_ticker

            profit = total_value_ticker - total_cost_ticker
            rate_of_return = ((total_value_ticker / total_cost_ticker) - 1 ) * 100 if total_cost_ticker > 0 else None

            first_date, last_date = self.get_ticker_date_range(ticker)

            annualized_return = self.calculate_annualized_return(first_date, last_date, total_value_ticker, total_cost_ticker)

            ror_data.append({
                "Ticker": ticker,
                "Latest Price": round(todays_price, 2),
                "Ave Cost Basis": round(cost_basis, 2),
                "Total Holding": round(latest_quantity_ticker, 2),
                "Total Value": round(total_value_ticker, 2),
                "Total Cost": round(total_cost_ticker, 2),
                "Profit": round(profit, 2),
                "Rate of Return (%)": round(rate_of_return, 2),
                "Portfolio (%)": None,  # 后续计算
                "First Date": first_date,
                "Last Date": last_date,
                "Annualized RoR (%)": round(annualized_return, 2)
            })

            # 累计总计数据
            total_cost += total_cost_ticker
            total_value += total_value_ticker

        # Overall Total value
        overall_first_date, overall_last_date = self.get_overall_date_range()
        overall_annualized_return = self.calculate_overall_annualized_return(overall_first_date, overall_last_date, total_value, total_cost)
        overall_profit = total_value - total_cost
        total_rate_of_return = ((total_value / total_cost) - 1) * 100 if total_cost > 0 else None

        # 添加 Portfolio (%) 列
        for row in ror_data:
            row["Portfolio (%)"] = round((row["Total Value"] / (total_value + latest_cash)) * 100, 2) if total_value > 0 else 0

        # 添加 Cash 行
        ror_data.append({
            "Ticker": "Cash",
            "Latest Price": None,
            "Total Holding": None,
            "Ave Cost Basis": None,
            "Total Value": round(latest_cash, 2),
            "Total Cost": None,
            "Profit": None,
            "Rate of Return (%)": None,
            "Portfolio (%)": round((latest_cash / (total_value + latest_cash)) * 100, 2) if latest_cash > 0 else 0,
            "First Date": None,
            "Last Date": None,
            "Annualized RoR (%)": None
        })

        ror_data.append({
            "Ticker": "Total (w/o Cash)",
            "Latest Price": None,
            "Ave Cost Basis": None,
            "Total Holding": None,
            "Total Value": round(total_value, 2),
            "Total Cost": round(total_cost, 2),
            "Profit": round(overall_profit, 2),
            "Rate of Return (%)": round(total_rate_of_return, 2),
            "Portfolio (%)": 100.0,  # 总计行为 100%
            "First Date": overall_first_date,
            "Last Date": overall_last_date,
            "Annualized RoR (%)": round(overall_annualized_return, 2)
        })

        # 转换为 DataFrame
        df = pd.DataFrame(ror_data)

        # 确保 Profit 列为浮点数，并填充空值
        df["Profit"] = pd.to_numeric(df["Profit"], errors='coerce').fillna(0)

        # 按 Profit 降序排序，保留 "Total" 行在最后
        sorted_df = pd.concat([
            df[df["Ticker"] != "Total (w/o Cash)"].sort_values(by="Profit", ascending=False),
            df[df["Ticker"] == "Total (w/o Cash)"]
        ], ignore_index=True)

        # 简化版表格
        summary_df = sorted_df[["Ticker", "Portfolio (%)", "Rate of Return (%)", "First Date", "Last Date", "Annualized RoR (%)"]]

        # 按 Portfolio (%) 降序排序，保留 Total 行在最后
        summary_df = pd.concat([
            summary_df[summary_df["Ticker"] != "Total (w/o Cash)"].sort_values(by="Portfolio (%)", ascending=False),
            summary_df[summary_df["Ticker"] == "Total (w/o Cash)"]
        ], ignore_index=True)

        return sorted_df, summary_df
        

    def save_df_as_png(self, df, filename):
        """
        将 DataFrame 保存为 PNG 文件。

        Parameters:
        - df (pd.DataFrame): 要保存的 DataFrame。
        - filename (str): 保存的 PNG 文件名。
        """
        # 创建 Matplotlib 表格
        fig, ax = plt.subplots(figsize=(12, len(df) * 0.5))  # 动态调整高度
        ax.axis('tight')
        ax.axis('off')
        table = plt.table(cellText=df.values,
                          colLabels=df.columns,
                          loc='center',
                          cellLoc='center')

        # 调整字体大小
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.auto_set_column_width(col=list(range(len(df.columns))))

        # 保存为 PNG
        plt.savefig(filename, bbox_inches='tight', dpi=300)
        plt.close(fig)


    def close(self):
        self.conn.close()
