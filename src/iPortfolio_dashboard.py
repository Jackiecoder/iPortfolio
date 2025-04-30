from iPortfolio_dbAccessor import DbAccessor
from datetime import datetime
from iPortfolio_util import Util
import pandas as pd
import matplotlib.pyplot as plt

class AssetDashboard:
    
    def _calc_annualized_return(self, ticker, start_date, end_date):
        pass

    def _default_row_schema(self):
        return {
            "Ticker": None,
            "Latest Price": None,
            "1d%": None,
            "1dp": None,
            "3d%": None,
            "3dp": None,
            "7d%": None,
            "7dp": None,
            "30d%": None,
            "30dp": None,
            "YTD%": None,
            "YTDp": None,
            "Ave Cost Basis": None,
            "Total Holding": None,
            "Total Value": None,
            "Total Cost": None,
            "Unrealized Gain": None,
            "Realized Gain": None,
            "Total Profit": None,
            "Rate of Return (%)": None,
            "Portfolio (%)": None,
            "First Date": None,
            "Last Date": None,
            "Annualized RoR (%)": None
        }

    def _date_stockprice_and_profit(self, ticker: str, date: str):
        stock_price = DbAccessor.fetch_and_store_price(ticker, date)
        quantity = DbAccessor.get_stock_quantity(ticker, date)
        realized_gain = DbAccessor.get_realized_gain(ticker, date)
        cost_basis = DbAccessor.get_cost_basis(ticker, date)
        cost = quantity * cost_basis
        holding_value = quantity * stock_price if stock_price else 0
        unrealized_gain = holding_value - cost
        profit = unrealized_gain + realized_gain

        return stock_price, profit

    def _date_before_stockprice_and_profit(self, ticker: str, date: str, date_delta: int):
        previous_date = Util.get_date_before(date, date_delta)
        stock_price, profit = self._date_stockprice_and_profit(ticker, previous_date)

        return stock_price, profit

    def _calc_ror_helper(self, ticker: str, date: str) -> dict:
        stock_price = DbAccessor.fetch_and_store_price(ticker, date)
        stock_price_1d, profit_1d = self._date_before_stockprice_and_profit(ticker, date, 1)
        stock_price_3d, profit_3d = self._date_before_stockprice_and_profit(ticker, date, 3)
        stock_price_7d, profit_7d = self._date_before_stockprice_and_profit(ticker, date, 7)
        stock_price_30d, profit_30d = self._date_before_stockprice_and_profit(ticker, date, 30)
        year = int(date.split("-")[0])
        stock_price_ytd, profit_ytd = self._date_stockprice_and_profit(ticker, f'{year}-01-01')
        # ytd_delta = Util.calculate_ytd_date_delta(date)
        # stock_price_ytd, profit_ytd = self._date_before_stockprice_and_profit(ticker, date, ytd_delta)
        quantity = DbAccessor.get_stock_quantity(ticker, date)
        cost_basis = DbAccessor.get_cost_basis(ticker, date)
        realized_gain = DbAccessor.get_realized_gain(ticker, date)

        if quantity == 0:
            '''
            No holding for this ticker, return only realized gain and total profit
            '''
            row = self._default_row_schema()
            row["Ticker"] = ticker
            row["Realized Gain"] = round(realized_gain, 2)
            row["Total Profit"] = round(realized_gain, 2)
            row["Total Value"] = 0
            row["Total Cost"] = 0
            row["Unrealized Gain"] = 0
            return row

        '''
        Otherwise, calculate the holding value, cost, profit, and rate of return
        '''
        cost = quantity * cost_basis
        holding_value = quantity * stock_price if stock_price else 0
        unrealized_gain = holding_value - cost
        profit = unrealized_gain + realized_gain
        ror = (profit / cost) * 100 if cost > 0 else None

        first_date, last_date = DbAccessor.get_start_end_date(ticker)
        duration_years = max((datetime.strptime(last_date, "%Y-%m-%d") \
                                      - datetime.strptime(first_date, "%Y-%m-%d")).days / 365.25, 1)
        annualized_return = ((holding_value / cost) ** (1 / duration_years) - 1) * 100

        # get row
        row = self._default_row_schema()
        row["Ticker"] = ticker
        row["Latest Price"] = round(stock_price, 2)
        row["1d%"] = round((stock_price - stock_price_1d) / stock_price_1d * 100, 2) if stock_price_1d else None
        row["1dp"] = round(profit - profit_1d, 2) if stock_price_1d else None
        row["3d%"] = round((stock_price - stock_price_3d) / stock_price_3d * 100, 2) if stock_price_3d else None
        row["3dp"] = round(profit - profit_3d, 2) if stock_price_3d else None
        row["7d%"] = round((stock_price - stock_price_7d) / stock_price_7d * 100, 2) if stock_price_7d else None
        row["7dp"] = round(profit - profit_7d, 2) if stock_price_7d else None
        row["30d%"] = round((stock_price - stock_price_30d) / stock_price_30d * 100, 2) if stock_price_30d else None
        row["30dp"] = round(profit - profit_30d, 2) if stock_price_30d else None
        row["YTD%"] = round((stock_price - stock_price_ytd) / stock_price_ytd * 100, 2) if stock_price_ytd else None
        row["YTDp"] = round(profit - profit_ytd, 2) if stock_price_ytd else None
        row["Ave Cost Basis"] = round(cost_basis, 2)
        row["Total Holding"] = round(quantity, 3)
        row["Total Value"] = round(holding_value, 2)
        row["Total Cost"] = round(cost, 2)
        row["Unrealized Gain"] = round(unrealized_gain, 2)
        row["Realized Gain"] = round(realized_gain, 2)
        row["Total Profit"] = round(profit, 2)
        row["Rate of Return (%)"] = round(ror, 2)
        row["Portfolio (%)"] = None
        row["First Date"] = first_date
        row["Last Date"] = last_date
        row["Annualized RoR (%)"] = round(annualized_return, 2) if annualized_return else None

        return row

    def _calc_cash_helper(self, date: str) -> dict:
        cash = DbAccessor.get_cash_balance_on_date(date)
        row = self._default_row_schema()
        row["Ticker"] = "Cash"
        row["Total Value"] = round(cash, 2)
        return row

    def _populate_portfolio_percentage(self, data: list) -> list:
        # total_value = sum(item["Total Value"] for item in data if item["Total Value"] is not None)
        total_value = data[-1]["Total Value"]
        for item in data:
            if item["Total Value"] is not None:
                item["Portfolio (%)"] = round((item["Total Value"] / total_value) * 100, 2)
        return data

    def _populate_total_row(self, data: list) -> dict:
        total_value = sum(item["Total Value"] for item in data if item["Total Value"] is not None)
        total_cost = sum(item["Total Cost"] for item in data if item["Total Cost"] is not None)
        total_profit = sum(item["Total Profit"] for item in data if item["Total Profit"] is not None)
        total_unrealized_gain = sum(item["Unrealized Gain"] for item in data if item["Unrealized Gain"] is not None)
        total_realized_gain = sum(item["Realized Gain"] for item in data if item["Realized Gain"] is not None)
        total_ror = (total_profit / (total_value - total_profit)) * 100 if total_cost > 0 else None
        total_1d = sum(item["1dp"] for item in data if item["1dp"] is not None)
        total_3d = sum(item["3dp"] for item in data if item["3dp"] is not None)
        total_7d = sum(item["7dp"] for item in data if item["7dp"] is not None)
        total_30d = sum(item["30dp"] for item in data if item["30dp"] is not None)
        total_ytd = sum(item["YTDp"] for item in data if item["YTDp"] is not None)

        row = self._default_row_schema()
        row["Ticker"] = "Total (w/o Cash)"
        row["Latest Price"] = None
        row["Ave Cost Basis"] = None
        row["Total Holding"] = None
        row["Total Value"] = round(total_value, 2)
        row["Total Cost"] = round(total_cost, 2)
        row["Unrealized Gain"] = round(total_unrealized_gain, 2)
        row["Realized Gain"] = round(total_realized_gain, 2)
        row["Total Profit"] = round(total_profit, 2)
        row["Rate of Return (%)"] = round(total_ror, 2)
        row["Portfolio (%)"] = None
        row["First Date"] = None
        row["Last Date"] = None
        row["Annualized RoR (%)"] = None
        row["1dp"] = round(total_1d, 2)
        row["3dp"] = round(total_3d, 2)
        row["7dp"] = round(total_7d, 2)
        row["30dp"] = round(total_30d, 2)
        row["YTDp"] = round(total_ytd, 2)

        return row

    def _convert_data_to_df(self, data: list) -> pd.DataFrame:
        df = pd.DataFrame(data)
        df["Total Profit"] = pd.to_numeric(df["Total Profit"], errors='coerce').fillna(0)
        sorted_df = pd.concat([
            df[df["Ticker"] != "Total (w/o Cash)"].sort_values(by="Total Profit", ascending=False),
            df[df["Ticker"] == "Total (w/o Cash)"]
        ], ignore_index=True)       

        return sorted_df

    def _populate_total_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # Total DF
        total_df = df[["Ticker", 
                        "Latest Price",
                        "Ave Cost Basis",
                        "Total Holding",
                        "Total Value",
                        "Total Cost",
                        "Unrealized Gain",
                        "Realized Gain",
                        "Total Profit",
                        "Rate of Return (%)",
                        "Portfolio (%)",
                        "First Date",
                        "Last Date",
                        "Annualized RoR (%)"]]      
        return total_df     

    def _populate_summary_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # Summary DF  
        summary_df = df[["Ticker", 
                        "Portfolio (%)", 
                        "Total Value",
                        "Total Cost",
                        "Total Profit",
                        "Rate of Return (%)",
                        "Annualized RoR (%)"]]           
        other_df = summary_df[(summary_df["Total Cost"] == 0) & (summary_df["Total Value"] == 0)]
        if not other_df.empty:
            other_row = other_df.sum(numeric_only=True).round(2)
            other_row["Ticker"] = "Other"
            other_row["Rate of Return (%)"] = None
            other_row["Portfolio (%)"] = None
            other_row["Annualized RoR (%)"] = None
            summary_df = summary_df[(summary_df["Total Cost"] != 0) | (summary_df["Total Value"] != 0)]
            other_row_df = pd.DataFrame([other_row]).dropna(axis=1, how='all')  # 排除所有空或全为 NA 的列
            summary_df = pd.concat([summary_df, other_row_df], ignore_index=True)
    
        summary_df = pd.concat([
            summary_df[summary_df["Ticker"] != "Total (w/o Cash)"].sort_values(by="Portfolio (%)", ascending=False),
            summary_df[summary_df["Ticker"] == "Total (w/o Cash)"]
        ], ignore_index=True)

        return summary_df

    def _populate_category_df(self, df: pd.DataFrame) -> pd.DataFrame:
        cat_data = {}

        for row in df.itertuples(index=False):
            if row.Ticker == "Total (w/o Cash)" or row.Ticker == "Total":
                continue
            ticker = row.Ticker
            category = Util.get_cat_for_ticker(ticker)

            if category not in cat_data:
                cat_data[category] = {
                    "Portfolio (%)": 0,
                    "Total Value": 0,
                    "Total Cost": 0,
                    "Total Profit": 0,
                    "Rate of Return (%)": None,
                    "Annualized RoR (%)": None
                }

            cat_data[category]["Portfolio (%)"] += row._1 if row._1 else 0
            cat_data[category]["Total Value"] += row._2 if row._2 else 0
            cat_data[category]["Total Cost"] += row._3 if row._3 else 0
            cat_data[category]["Total Profit"] += row._4 if row._4 else 0

        # 保留两位小数
        for category, data in cat_data.items():
            for key in data:
                if data[key] is not None:
                    data[key] = round(data[key], 2)

        # 计算分类的收益率和年化收益率
        for category, data in cat_data.items():
            if data["Total Cost"] > 0:
                data["Rate of Return (%)"] = ((data["Total Value"] / data["Total Cost"]) - 1) * 100
                # data["Annualized RoR (%)"] = self.calculate_annualized_return(overall_first_date, overall_last_date, data["Total Value"], data["Total Cost"])

                data["Rate of Return (%)"] = round(data["Rate of Return (%)"], 2) if data["Rate of Return (%)"] is not None else None
                data["Annualized RoR (%)"] = round(data["Annualized RoR (%)"], 2) if data["Annualized RoR (%)"] is not None else None

        # 转换为 DataFrame
        cat_df = pd.DataFrame.from_dict(cat_data, orient='index').reset_index().rename(columns={"index": "Category"})

        # 按 Portfolio (%) 降序排序
        cat_df = cat_df.sort_values(by="Portfolio (%)", ascending=False).reset_index(drop=True)

        return cat_df        
  
    def _populate_compare_df(self, df: pd.DataFrame) -> pd.DataFrame:   
        compare_df = df[["Ticker", 
                        "Latest Price",
                        "1d%",
                        "1dp",
                        "3d%",
                        "3dp",
                        "7d%",
                        "7dp",
                        "30d%",
                        "30dp",
                        "YTD%",
                        "YTDp",
                        "Rate of Return (%)",
                        "Total Profit",
                        "Portfolio (%)", 
                        "Ave Cost Basis",
                        "Total Value",
                        "Total Cost",
                        "Annualized RoR (%)"]]       
        other_df = compare_df[(compare_df["Total Cost"] == 0) & (compare_df["Total Value"] == 0)]
        if not other_df.empty:
            other_row = other_df.sum(numeric_only=True).round(2)
            other_row["Ticker"] = "Other"
            other_row["Rate of Return (%)"] = None
            other_row["Portfolio (%)"] = None
            other_row["Annualized RoR (%)"] = None
            compare_df = compare_df[(compare_df["Total Cost"] != 0) | (compare_df["Total Value"] != 0)]
            other_row_df = pd.DataFrame([other_row]).dropna(axis=1, how='all')  # 排除所有空或全为 NA 的列
            compare_df = pd.concat([compare_df, other_row_df], ignore_index=True)
    
        compare_df = pd.concat([
            compare_df[compare_df["Ticker"] != "Total (w/o Cash)"].sort_values(by="Portfolio (%)", ascending=False),
            compare_df[compare_df["Ticker"] == "Total (w/o Cash)"]
        ], ignore_index=True)

        return compare_df


    def calculate_ror(self, date):
        tickers = DbAccessor.get_all_tickers()
        data = []

        # Iterate through each ticker and calculate the rate of return
        for ticker in tickers:
            data.append(self._calc_ror_helper(ticker, date))
        
        # add cash 
        data.append(self._calc_cash_helper(date))
        
        # Populate total row
        data.append(self._populate_total_row(data))

        # Populate portfolio percentage
        data = self._populate_portfolio_percentage(data)

        #========== Convert into dataframe
        # Populate total dataframe
        df = self._convert_data_to_df(data)

        # Populate total DataFrame
        total_df = self._populate_total_df(df)

        # Populate summary DataFrame
        summary_df = self._populate_summary_df(df)

        # Populate category DataFrame
        cat_df = self._populate_category_df(summary_df)

        # Populate compare DataFrame
        compare_df = self._populate_compare_df(df)

        return total_df, summary_df, cat_df, compare_df

    def save_df_as_png(self, ori_df, filename, title=""):
        """
        将 DataFrame 保存为 PNG 文件。

        Parameters:
        - df (pd.DataFrame): 要保存的 DataFrame。
        - filename (str): 保存的 PNG 文件名。
        """

        df = ori_df.copy()
        for column in df.columns:
            if pd.api.types.is_numeric_dtype(df[column]):
                # 保留两位小数并添加千分位分隔符
                df[column] = df[column].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")

        # 创建 Matplotlib 表格
        fig, ax = plt.subplots(figsize=(12, len(df) * 0.5))  # 动态调整高度
        ax.axis('tight')
        ax.axis('off')
        table = plt.table(cellText=df.values,
                          colLabels=df.columns,
                          loc='center',
                          cellLoc='center')

        # set *d% columns
        percent_columns = [col for col in df.columns if col.endswith("d%")]
        percent_columns += ["Rate of Return (%)", "Total Profit", "YTD%", "YTDp"]
        percent_columns += [col for col in df.columns if col.endswith("dp")]
        # 检查列是否存在
        percent_columns = [col for col in percent_columns if col in df.columns]

        percent_indices = [df.columns.get_loc(col) for col in percent_columns]


        # # Set alternating row colors
        for (row, col), cell in table.get_celld().items():
            if row == 0:  # 跳过标题行
                cell.set_fontsize(12)
                cell.set_text_props(weight='bold')
            else:
                cell.set_fontsize(10)
                if col in percent_indices:  # 如果是 *d% 列
                    value = df.iloc[row - 1, col]  # 获取对应的值
                    if pd.notnull(value) and value != '':  # 确保值不是 NaN
                        try:
                            numeric_value = float(value.replace(",", ""))  # 移除逗号并转换为浮点数
                            if numeric_value > 0:
                                cell.set_text_props(color="green")  # 正值为绿色
                            elif numeric_value < 0:
                                cell.set_text_props(color="red")  # 负值为红色
                        except ValueError:
                            pass  # 如果转换失败，跳过
                # 设置交替行背景色
                if row % 2 == 0:
                    cell.set_facecolor('#f0f0f0')
                    # cell.set_facecolor('#d9d9d9')  # 浅灰色
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


