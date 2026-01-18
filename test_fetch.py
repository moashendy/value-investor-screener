import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'src'))
from data_fetcher import StockDataFetcher
import yfinance as yf

def test():
    fetcher = StockDataFetcher()
    yf.Ticker("MSFT").info
    data = fetcher.get_financial_data("AAPL")
    print("Data returned:", data is not None)
    if data is not None:
        print("annual_eps:", data.get('annual_eps'))
        print("annual_fcf:", data.get('annual_fcf'))
        
if __name__ == "__main__":
    test()
