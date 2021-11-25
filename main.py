import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta, datetime
import pandas_market_calendars as mcal
import openpyxl
import time

KEY = ""  # Alpha Vantage API Key
URL = "https://www.alphavantage.co/query?"


def algorithm(stock):
    try:
        params = {"function": "TIME_SERIES_DAILY_ADJUSTED",
                  "symbol": stock,
                  "interval": "",
                  "apikey": "KEY"}
        data = requests.get(url=URL, params=params).json()
    except:
        return None

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
    try:
        for i in range(len(df_variables)):
            df[df_variables[i]] = [float(stock_daily[dates[x]][data_variables[i]]) for x in range(period + 1)]
    except:
        return None

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
    df.drop(columns=['k_high', 'k_low', 'RSV'], inplace=True)  # Dropping columns that are meant for calculation only
    # df.dropna(subset=['K', 'D', 'J']).iloc[::-1].plot(x='Date', y=['K','D','J'], figsize=(10,4), title=f"{stock} KDJ Plot")
    # plt.show()

    # Technical Indicator - MACD
    # Using ewm for EMA calculation
    # Shorter and more precise version of MACD
    macd_slow, macd_fast, macd_mid = 26, 12, 9
    df = df.iloc[::-1]
    df['EMA_12'] = df['Close'].ewm(span=macd_fast, adjust=False, min_periods=macd_fast).mean()
    df['EMA_26'] = df['Close'].ewm(span=macd_slow, adjust=False, min_periods=macd_slow).mean()
    df['DIF'] = df['EMA_12'] - df['EMA_26']
    df['DEA'] = df['DIF'].ewm(span=macd_mid, adjust=False, min_periods=macd_mid).mean()
    df['MACD'] = (df['DIF'] - df['DEA']) * 2
    df = df.iloc[::-1].drop(columns=['EMA_12', 'EMA_26'])
    # print(df.to_string())
    # ax = df.dropna(subset=['DIF', 'DEA']).iloc[::-1].plot(x='Date', y=['DIF','DEA'], kind='line', figsize=(10,4), title=f"{stock} MACD Plot")
    # df.dropna(subset=['MACD']).iloc[::-1].plot(x='Date', y='MACD', kind='bar', ax=ax)
    # plt.show()

    # One of the interpretations of MACD
    # df['Average Index'] = (df['High'] + df['Low'] + df['Close'] * 2) / 4
    # for i in range(period - 12, -1, -1):
    #     df.loc[i, 'EMA_12'] = df.loc[i + 1, 'EMA_12'] + (df.loc[i, 'Average Index'] - df.loc[i + 1, 'EMA_12']) * 2 / (1 + 12)
    # df.loc[period - 26 + 1, 'EMA_26'] = df.loc[period - 26 + 1, 'Close']
    # for i in range(period - 26, -1, -1):
    #     df.loc[i, 'EMA_26'] = df.loc[i + 1, 'EMA_26'] + (df.loc[i, 'Average Index'] - df.loc[i + 1, 'EMA_26']) * 2 / (1 + 26)
    # df['DIF'] = df['EMA_12'] - df['EMA_26']
    # df.loc[period - 26 + 1, 'MACD'] = df.loc[period - 26 + 1, 'DIF']
    # for i in range(period - 26, -1, -1):
    #     df.loc[i, 'MACD'] = df.loc[i + 1, 'MACD'] + (df.loc[i, 'DIF'] - df.loc[i + 1, 'MACD']) * 2 / (1 + 26)

    # Authentic calculation of MACD
    # ema_smoothing = 2  # Default: 2
    # df.loc[period - 12 + 1, 'EMA_12'] = df.loc[period - 12 + 1, 'Close']
    # for i in range(period - 12, -1, -1):
    #     df.loc[i, 'EMA_12'] = df.loc[i + 1, 'EMA_12'] * (1 - ema_smoothing / (1 + 12)) + df.loc[i, 'Close'] * ema_smoothing / (1 + 12)
    # df.loc[period - 26 + 1, 'EMA_26'] = df.loc[period - 26 + 1, 'Close']
    # for i in range(period - 26, -1, -1):
    #     df.loc[i, 'EMA_26'] = df.loc[i + 1, 'EMA_26'] * (1 - ema_smoothing / (1 + 26)) + df.loc[i, 'Close'] * ema_smoothing / (1 + 26)
    # df['DIF2'] = df['EMA_12'] - df['EMA_26']
    # df.loc[period - 26 + 1, 'DEA2'] = df.loc[period - 26 + 1, 'DIF2']
    # for i in range(period - 26, -1, -1):
    #     df.loc[i, 'DEA2'] = df.loc[i + 1, 'DEA2'] * (1 - ema_smoothing / (1 + 9)) + df.loc[i, 'DIF2'] * ema_smoothing / (1 + 9)
    # df['MACD2'] = (df['DIF2'] - df['DEA2']) * 2

    return df


def plot(stock):
    df = algorithm(stock)
    if df is None:
        return "No Result"
    df.dropna(subset=['K', 'D', 'J']).iloc[::-1].plot(x='Date', y=['K','D','J'], figsize=(10,4), title=f"{stock} KDJ Plot")
    plt.show()
    ax = df.dropna(subset=['DIF', 'DEA']).iloc[::-1].plot(x='Date', y=['DIF','DEA'], kind='line', figsize=(10,4), title=f"{stock} MACD Plot")
    df.dropna(subset=['MACD']).iloc[::-1].plot(x='Date', y='MACD', kind='bar', ax=ax)
    plt.show()
    print(df.to_string())


def suggest(stock):
    df = algorithm(stock)
    if df is None:
        return False
    if df['MACD'][0] > 0 and df['MACD'][0] > df['MACD'][1] and df['K'][0] > df['D'][0] and df['J'][0] > df['J'][1]:
        return "Buy"
    elif df['MACD'][0] < 0 and df['MACD'][0] < df['MACD'][1] and df['K'][0] < df['D'][0] and df['J'][0] < df['J'][1]:
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
    if suggest(i) == "Buy":
        stock_buy.append(i)
    elif suggest(i) == "Sell":
        stock_sell.append(i)
    print(i)
    stock_assessed.append(i)
    if len(stock_assessed) % 5 == 0:
        # Free version of Alpha Vantage only allows 5 requests per minute
        time.sleep(60)
print("BUY: " + stock_buy)
print("Sell: " + stock_sell)
plot("AAPL")
