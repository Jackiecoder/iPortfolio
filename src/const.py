# input data    
TRANSACTIONS_PATH = "input_transactions/"
CASH_PATH = f"{TRANSACTIONS_PATH}cash/cash.csv"

# output data
OUTPUT_PATH = "results/"
ROR_TABLE_PATH = f"{OUTPUT_PATH}ror_table/"
ROR_TOTAL_TABLE_PATH = f"{ROR_TABLE_PATH}ror_total_table/"
ROR_SUMMARY_TABLE_PATH = f"{ROR_TABLE_PATH}ror_summary_table/"
CHART_PATH = f"{OUTPUT_PATH}plot_line_chart/"
DBVIEWER_PATH = f"{OUTPUT_PATH}dbviewer/"
TICKER_CHART_PATH = f"{OUTPUT_PATH}plot_ticker_line_chart/"

# plotter
NUM_OF_PLOT = 16

# date match
DATES = {
    "1D": (1, 0),
    "3D": (3, 0),
    "1W": (7, 1),
    "2W": (14, 1),
    "1M": (30, 2),
    "3M": (90, 2),
    "6M": (180, 2),
    "1Y": (365, 3),
    "YTD": ("YTD", 3)
}

# Title ==
title_line = "=============================="

# Debug mode
DBUG = False
