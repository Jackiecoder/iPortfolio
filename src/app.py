#!/usr/local/bin/python3 
from app_util import *

def main():
    print("Welcome to Portfolio Manager")
    '''Load Transactions from CSV'''
    load_transactions()

    '''Download Database from SQLite'''
    view_database()

    '''Show ROR'''
    # display_portfolio_ror("", previous_range=3)

    '''Show latest ror'''
    display_portfolio_ror_latest()
    
    '''Plot line Chart'''
    plot_line_chart()

    '''Show Ticker ROR'''
    # plot_ticker_line_chart()


    # ======================================
    # Historical Line Chart and RoR table
    # ======================================
    '''Show historical RoR table'''
    display_historical_portfolio_ror()

    '''Plot Historical Line Chart'''
    # plot_historical_line_chart()

    # test()


if __name__ == "__main__":
    main()