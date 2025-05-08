#!/usr/local/bin/python3 
from iPortfolio_client import *
import iPortfolio_client as ip_client
from iPortfolio_util import Util
import inspect
import sys

def daily_dashboard_and_line():
    Util.log_to_file(__file__, inspect.currentframe().f_lineno, "INFO", "Executing daily_dashboard_and_line")
    print("Welcome to Portfolio Manager")
    print("Start processing daily dashboard and line chart")
    '''Load Transactions from CSV'''
    ip_client.load_transactions()
    '''Download Database from SQLite'''
    ip_client.view_database()
    '''Show latest ror'''
    ip_client.display_portfolio_ror_latest()
    '''Plot line Chart'''
    ip_client.plot_line_chart()

def historical_ytd():
    Util.log_to_file(__file__, inspect.currentframe().f_lineno, "INFO", "Executing historical_ytd")
    print("Welcome to Portfolio Manager")
    print("Start processing historical YTD")
    '''Load Transactions from CSV'''
    ip_client.load_transactions()
    '''Download Database from SQLite'''
    ip_client.view_database()
    ip_client.plot_historical_line_chart()

def delete_record(date):
    Util.log_to_file(__file__, inspect.currentframe().f_lineno, "INFO", "Executing clear_record")
    print("Welcome to Portfolio Manager")
    print("Start processing clear record")
    ip_client.delete_daily_prices(date)
    ip_client.view_database()

def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "-d":
            Util.log_to_file(__file__, inspect.currentframe().f_lineno, "INFO", "Argument '-d' received")
            daily_dashboard_and_line()
        elif arg == "--ytd":
            Util.log_to_file(__file__, inspect.currentframe().f_lineno, "INFO", "Argument '--ytd' received")
            historical_ytd()
        elif arg == "--delete" or arg == "--del":
            Util.log_to_file(__file__, inspect.currentframe().f_lineno, "INFO", "Argument '--delete' received")
            date = sys.argv[2] if len(sys.argv) > 2 else None
            if date:
                Util.log_to_file(__file__, inspect.currentframe().f_lineno, "INFO", f"Deleting record for date: {date}")
                delete_record(date)
            else:
                Util.log_to_file(__file__, inspect.currentframe().f_lineno, "ERROR", "No date provided for deletion")
                print("No date provided for deletion. Use '--delete <date>' or '--del <date>'.")
        else:
            Util.log_to_file(__file__, inspect.currentframe().f_lineno, "ERROR", f"Invalid argument: {arg}")
            print("Invalid argument. Use '-d' or '--ytd'.")
    else:
        Util.log_to_file(__file__, inspect.currentframe().f_lineno, "ERROR", "No argument provided")
        print("No argument provided. Use '-d' or '--ytd'.")

if __name__ == "__main__":
    main()