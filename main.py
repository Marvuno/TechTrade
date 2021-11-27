import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta, datetime
import pandas_market_calendars as mcal
import openpyxl
import time

KEY = "K22TH1A5A9LN8LCB"  # Alpha Vantage API Key
URL = "https://www.alphavantage.co/query?"


def algorithm(stock):
    try:
        params = {"function": "TIME_SERIES_DAILY_ADJUSTED",
                  "symbol": stock,
                  "interval": "",
                  "apikey": "KEY"}
        data = requests.get(url=URL, params=params).json()

        # Retrieve given number of the most recent dates that the stock market opens
        dates = []
        period = 98  # default: 9 weeks of data
        schedule = mcal.get_calendar("NYSE").valid_days(start_date='2021-1-1',
                                                        end_date=datetime.now() - timedelta(days=1, hours=4))
        for i in schedule[::-1]:
            dates.append(i.strftime("%Y-%m-%d"))
            if len(dates) > period:
                break

        # Some basic info of the stock in the Dataframe
        df = pd.DataFrame()
        stock_daily = data['Time Series (Daily)']
        df_variables = ['Open', 'Close', 'High', 'Low', 'Volume', 'Dividend', 'Split']
        data_variables = ['1. open', '5. adjusted close', '2. high', '3. low', '6. volume', '7. dividend amount',
                          '8. split coefficient']
        df['Date'] = [x for x in dates]
        for i in range(len(df_variables)):
            df[df_variables[i]] = [float(stock_daily[dates[x]][data_variables[i]]) for x in range(period + 1)]

        # Technical Indicator - KDJ
        kdj_period = 9  # Default: 9 days
        df['Returns'] = (df['Close'] - df['Close'].shift(-1)) / df['Close'].shift(-1) * 100
        df['k_high'] = df['High'].rolling(kdj_period).max().shift(- kdj_period + 1)
        df['k_low'] = df['Low'].rolling(kdj_period).min().shift(- kdj_period + 1)
        df['RSV'] = (df['Close'] - df['k_low']) * 100 / (df['k_high'] - df['k_low'])
        # Note that the first few entries will be largely inaccurate
        df.loc[period - kdj_period + 1, 'K'] = 50  # For the first value, assume it is 50
        for i in range(period - kdj_period, -1, -1):
            df.loc[i, 'K'] = df.loc[i + 1, 'K'] * 2 / 3 + df.loc[i, 'RSV'] / 3
        df.loc[period - kdj_period + 1, 'D'] = 50  # For the first value, assume it is 50
        for i in range(period - kdj_period, -1, -1):
            df.loc[i, 'D'] = df.loc[i + 1, 'D'] * 2 / 3 + df.loc[i, 'K'] / 3
        df['J'] = df['K'] * 3 - df['D'] * 2
        # Dropping columns that are meant for calculation only
        df.drop(columns=['k_high', 'k_low', 'RSV'], inplace=True)

        # Technical Indicator - MACD
        # Using ewm for EMA calculation
        # Shorter and more precise version of MACD
        # Optimized values
        macd_slow, macd_fast, macd_mid = 22, 4, 3
        df = df.iloc[::-1]
        df['EMA_12'] = df['Close'].ewm(span=macd_fast, adjust=False, min_periods=macd_fast).mean()
        df['EMA_26'] = df['Close'].ewm(span=macd_slow, adjust=False, min_periods=macd_slow).mean()
        df['DIF'] = df['EMA_12'] - df['EMA_26']
        df['DEA'] = df['DIF'].ewm(span=macd_mid, adjust=False, min_periods=macd_mid).mean()
        df['MACD'] = (df['DIF'] - df['DEA']) * 2
        df = df.iloc[::-1].drop(columns=['EMA_12', 'EMA_26'])

        return df

    except:
        return None


def plot(stock):
    df = algorithm(stock)
    if df is None:
        return False
    df.dropna(subset=['K', 'D', 'J']).iloc[::-1].plot(x='Date', y=['K', 'D', 'J'], figsize=(10, 4),
                                                      title=f"{stock} KDJ Plot")
    plt.show()
    ax = df.dropna(subset=['DIF', 'DEA']).iloc[::-1].plot(x='Date', y=['DIF', 'DEA'], kind='line', figsize=(10, 4),
                                                          title=f"{stock} MACD Plot")
    df.dropna(subset=['MACD']).iloc[::-1].plot(x='Date', y='MACD', kind='bar', ax=ax)
    plt.show()
    print(df.to_string())


def suggest(stock):
    df = algorithm(stock)
    if df is None:
        return False

    buy = df['MACD'][0] > 0 and \
          df['MACD'][0] > df['MACD'][1] > df['MACD'][2] and \
          df['K'][0] > df['D'][0] and \
          df['J'][1] < max(df['K'][1], df['D'][1]) and \
          df['J'][0] > max(df['K'][0], df['D'][0])

    sell = df['MACD'][0] < 0 and \
           df['MACD'][0] < df['MACD'][1] < df['MACD'][2] and \
           df['K'][0] < df['D'][0] and \
           df['J'][1] > max(df['K'][1], df['D'][1]) and \
           df['J'][0] < max(df['K'][0], df['D'][0])

    if buy:
        return "Buy"
    elif sell:
        return "Sell"
    else:
        return False


# Retrieving S&P 500 stock for measurement
constituents = (pd.read_excel("Constituents.xlsx"))
symbols = [symbol for symbol in constituents['Symbol']]
# Free version of Alpha Vantage only allows 500 requests per day
symbols = symbols[:500]
# Suggestion to buy/sell stock
stock_assessed = []
stock_buy = []
stock_sell = []
for i in symbols:
    decision = suggest(i)
    if decision == "Buy":
        stock_buy.append(i)
    elif decision == "Sell":
        stock_sell.append(i)
    print(i)
    stock_assessed.append(i)
    # Free version of Alpha Vantage only allows 5 requests per minute
    if len(stock_assessed) % 5 == 0:
        time.sleep(60)
print(f"BUY: {stock_buy}")
print(f"Sell: {stock_sell}")
