#!/usr/local/bin/python3 
from app_util import *

yyyy_mm_dd = [ ("2024", "11", "01")]

def main():
    print("Welcome to Portfolio Manager")
    '''Load Transactions from CSV'''
    # load_transactions()

    '''Show ROR'''
    display_portfolio_ror(yyyy_mm_dd)
    
    '''Plot line Chart'''
    # plot_line_chart()

    '''Show Ticker ROR'''
    # plot_ticker_line_chart()

    '''Download Database from SQLite'''
    view_database()

    # test()

if __name__ == "__main__":
    main()