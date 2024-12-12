#!/usr/local/bin/python3 
from app_util import *

yyyy_mm_dd = [ ("2024", "12", "12")]

def main():
    print("Welcome to Portfolio Manager!")
    '''Load Transactions from CSV'''
    # load_transactions()

    '''Download Database from SQLite'''
    # view_database()

    '''Plot line Chart'''
    # plot_chart()

    '''Show ROR'''
    # display_portfolio(yyyy_mm_dd)
    
    '''Show Ticker ROR'''
    # display_ticker_ror()

if __name__ == "__main__":
    main()