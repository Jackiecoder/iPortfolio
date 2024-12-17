# input data    
TRANSACTIONS_PATH = "transactions/"
CASH_PATH = "transactions/cash/cash.csv"

# output data
ROR_TABLE_PATH = "results/ror_table/"
CHART_PATH = "results/line_charts/"
DBVIEWER_PATH = "results/dbviewer/"
TICKER_CHART_PATH = "results/ticker_line_chart/"

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
