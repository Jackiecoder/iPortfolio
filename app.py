import yfinance as yf

def main():
    ticker = yf.Ticker("AAPL")
    print(ticker.info)

if __name__ == "__main__":
    main()