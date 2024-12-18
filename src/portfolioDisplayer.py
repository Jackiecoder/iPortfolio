import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta
from portfolioDisplayer_util import PortfolioDisplayerUtil, Util

class Displayer(PortfolioDisplayerUtil):
    def __init__(self, db_name="portfolio.db", debug=False):
        self.conn = sqlite3.connect(db_name)
        self.debug = debug

    def calculate_annualized_return(self, start_date, end_date, value, cost):
        duration_years = max((datetime.strptime(end_date, "%Y-%m-%d") \
                            - datetime.strptime(start_date, "%Y-%m-%d")).days / 365.25, 1)  # 不足一年按一年算
        if cost > 0:
            annualized_return = ((value / cost) ** (1 / duration_years) - 1) * 100
        else:
            annualized_return = None

        return annualized_return

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


    def calculate_rate_of_return_v2(self, date):
        tickers = self.get_all_tickers()
        ror_data = []
        total_cost, total_value, total_unrealized_gain, total_realized_gain, total_profit = 0, 0, 0, 0, 0

        for ticker in tickers:
            quantity_ticker = self.get_stock_quantity(ticker=ticker, date=date)
            if quantity_ticker == 0:
                realized_gain = self.get_realized_gain(ticker, date=date)
                ror_data.append({
                    "Ticker": ticker,
                    "Latest Price": None,
                    "Ave Cost Basis": None,
                    "Total Holding": None,
                    "Total Value": 0,
                    "Total Cost": 0,
                    "Unrealized Gain": 0,
                    "Realized Gain": round(realized_gain, 2),
                    "Total Profit": round(realized_gain, 2),
                    "Rate of Return (%)": None,
                    "Portfolio (%)": None,
                    "First Date": None,
                    "Last Date": None,
                    "Annualized RoR (%)": None
                })
                total_realized_gain += realized_gain
                total_profit += realized_gain
                continue

            todays_price = Util.fetch_and_store_price(db_conn=self.conn, ticker=ticker, date=date)
            cost_basis = self.get_cost_basis(ticker=ticker, date=date)
            total_value_ticker = quantity_ticker * todays_price
            total_cost_ticker = cost_basis * quantity_ticker

            if quantity_ticker == 0:
                # No holding yet, skip this ticker
                continue

            unrealized_gain = total_value_ticker - total_cost_ticker
            realized_gain = self.get_realized_gain(ticker, date=date)

            profit = unrealized_gain + realized_gain
            rate_of_return = ((total_value_ticker / total_cost_ticker) - 1) * 100 if total_cost_ticker > 0 else None

            first_date, last_date = self.get_ticker_date_range(ticker)
            last_date = min(date, last_date) if last_date else date
            annualized_return = self.calculate_annualized_return(first_date, last_date, total_value_ticker, total_cost_ticker)

            ror_data.append({
                "Ticker": ticker,
                "Latest Price": round(todays_price, 2),
                "Ave Cost Basis": round(cost_basis, 2),
                "Total Holding": round(quantity_ticker, 2),
                "Total Value": round(total_value_ticker, 2),
                "Total Cost": round(total_cost_ticker, 2),
                "Unrealized Gain": round(unrealized_gain, 2),
                "Realized Gain": round(realized_gain, 2),
                "Total Profit": round(profit, 2),
                "Rate of Return (%)": round(rate_of_return, 2),
                "Portfolio (%)": None,  # 后续计算
                "First Date": first_date,
                "Last Date": last_date,
                "Annualized RoR (%)": round(annualized_return, 2)
            })

            # 累计总计数据
            total_cost += total_cost_ticker
            total_value += total_value_ticker
            total_unrealized_gain += unrealized_gain
            total_realized_gain += realized_gain
            total_profit += profit

        # Add cash to the total value
        latest_cash = self.get_cash(date=date)

        # Overall Total value
        overall_first_date, overall_last_date = self.get_overall_date_range()
        overall_last_date = min(date, overall_last_date) if overall_last_date else date
        overall_annualized_return = self.calculate_annualized_return(overall_first_date, overall_last_date, total_value, total_cost)
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
            "Unrealized Gain": None,
            "Realized Gain": None,
            "Total Profit": None,
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
            "Unrealized Gain": round(total_unrealized_gain, 2),
            "Realized Gain": round(total_realized_gain, 2),
            "Total Profit": round(total_profit, 2),
            "Rate of Return (%)": round(total_rate_of_return, 2),
            "Portfolio (%)": 100.0,  # 总计行为 100%
            "First Date": overall_first_date,
            "Last Date": overall_last_date,
            "Annualized RoR (%)": round(overall_annualized_return, 2)
        })

        # 转换为 DataFrame
        df = pd.DataFrame(ror_data)

        # 确保 Profit 列为浮点数，并填充空值
        df["Total Profit"] = pd.to_numeric(df["Total Profit"], errors='coerce').fillna(0)

        # 按 Profit 降序排序，保留 "Total" 行在最后
        sorted_df = pd.concat([
            df[df["Ticker"] != "Total (w/o Cash)"].sort_values(by="Total Profit", ascending=False),
            df[df["Ticker"] == "Total (w/o Cash)"]
        ], ignore_index=True)

        # 简化版表格
        summary_df = sorted_df[["Ticker", 
                                "Portfolio (%)", 
                                "Total Value",
                                "Total Cost",
                                "Total Profit",
                                "Rate of Return (%)",
                                "Annualized RoR (%)"]]

        # 合并 total_cost == 0 和 total_value == 0 的记录为一行 "Other"
        other_df = summary_df[(summary_df["Total Cost"] == 0) & (summary_df["Total Value"] == 0)]
        if not other_df.empty:
            other_row = other_df.sum(numeric_only=True)
            other_row["Ticker"] = "Other"
            other_row["Rate of Return (%)"] = None
            other_row["Portfolio (%)"] = None
            other_row["Annualized RoR (%)"] = None
            summary_df = summary_df[(summary_df["Total Cost"] != 0) | (summary_df["Total Value"] != 0)]
            other_row_df = pd.DataFrame([other_row]).dropna(axis=1, how='all')  # 排除所有空或全为 NA 的列
            summary_df = pd.concat([summary_df, other_row_df], ignore_index=True)

        # 按 Portfolio (%) 降序排序，保留 Total 行在最后
        summary_df = pd.concat([
            summary_df[summary_df["Ticker"] != "Total (w/o Cash)"].sort_values(by="Portfolio (%)", ascending=False),
            summary_df[summary_df["Ticker"] == "Total (w/o Cash)"]
        ], ignore_index=True)

        return sorted_df, summary_df
        

    def save_df_as_png(self, df, filename, title=""):
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

        # Set alternating row colors
        for _, key in enumerate(table.get_celld().keys()):
            cell = table.get_celld()[key]
            if key[0] == 0:
                cell.set_fontsize(12)
                cell.set_text_props(weight='bold')
            else:
                cell.set_fontsize(10)
                if key[0] % 2 == 0:
                    cell.set_facecolor('#f0f0f0')
                else:
                    cell.set_facecolor('#ffffff')

        # 调整字体大小
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.auto_set_column_width(col=list(range(len(df.columns))))

        # Add title
        plt.title(title, fontsize=16, weight='bold')    

        # 保存为 PNG
        plt.savefig(filename, bbox_inches='tight', dpi=300)
        plt.close(fig)

    def close(self):
        self.conn.close()
