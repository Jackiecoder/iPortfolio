#!/usr/local/bin/python3 
from iPortfolio_client import *
import iPortfolio_client as ip_client

def main():
    print("Welcome to Portfolio Manager")
    '''Load Transactions from CSV'''
    ip_client.load_transactions()

    '''Download Database from SQLite'''
    ip_client.view_database()

    '''Show ROR'''
    # display_portfolio_ror("", previous_range=3)

    '''Show latest ror'''
    ip_client.display_portfolio_ror_latest()
    
    '''Plot line Chart'''
    ip_client.plot_line_chart()

    '''Show Ticker ROR'''
    # plot_ticker_line_chart()


    # ======================================
    # Historical Line Chart and RoR table
    # ======================================
    '''Show historical RoR table'''
    # display_historical_portfolio_ror()

    '''Plot Historical Line Chart'''
    # plot_historical_line_chart()

    # test()


if __name__ == "__main__":
    main()