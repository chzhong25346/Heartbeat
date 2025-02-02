import pandas as pd
from ..models import Quote, Index
import numpy as np


def findBuyPositive(s_dic):
    """Find stocks meeting weekly MACD conditions across multiple databases."""
    print("\nCondition 1: MACD and Signal Line both above zero.\n"
          "Condition 2: MACD has crossed above Signal Line.\n"
          "Condition 3: Histogram increasing for 3 weeks.\n"
          "Condition 4: Any of the last 5 weeks has a long lower shadow.\n"
          "(Caution - Slow line must be raising!)")
    for db_name in ['tsxci', 'nasdaq100', 'sp100', 'eei']:

        print(f'\nFive Weekly Buy Positive Company(s) in {db_name}:')
        print('----------------------------------------')
        s = s_dic[db_name]  # Get SQLAlchemy session
        indexes = pd.read_sql(s.query(Index).statement, s.bind)  # Fetch stock symbols

        for ticker in indexes['symbol'].tolist():
            # if ticker == "NPI":  # Only process SAP (adjust as needed)
            df = pd.read_sql(
                s.query(Quote).filter(Quote.symbol == ticker).statement,
                s.bind,
                index_col='date'
            ).sort_index(ascending=True)
            df = df.drop('adjusted', axis=1)
            df = df.drop('id', axis=1)

            if check_macd_conditions(df):
                corp_name = s.query(Index).filter(Index.symbol == ticker).first()
                print('%s (%s)' % (ticker, corp_name.company))

        s.close()  # Close the database session after processing all tickers


def calculate_macd(df):
    df = df.copy()
    df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    return df



def check_macd_conditions(df):

    # Convert to weekly data
    df_weekly = df.resample('W-MON', label='left', closed='left').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
    }).dropna()

    df_weekly = calculate_macd(df_weekly)  # Compute MACD values

    df_weekly['Lower_Shadow'] = df_weekly['close'].where(df_weekly['close'] < df_weekly['open'], df_weekly['open']) - df_weekly['low']

    if len(df_weekly) < 6:
        return False  # Not enough data

    last_five = df_weekly.iloc[-5:]  # Last 5 weeks
    last_three_hist = df_weekly['Hist'].iloc[-3:]  # Last 3 histogram values

    # Condition 1: MACD and Signal Line both below zero
    condition_1 = df_weekly['MACD'].iloc[-1] > 0 and df_weekly['Signal'].iloc[-1] > 0

    # Condition 2: MACD has crossed above Signal Line
    condition_2 = (
            df_weekly['MACD'].iloc[-1] > df_weekly['Signal'].iloc[-1]
    )

    # Condition 3: Histogram increasing for 3 weeks
    condition_3 = (
            last_three_hist.iloc[0] < last_three_hist.iloc[1] < last_three_hist.iloc[2]
    )

    # Condition 4: Any of the last 5 weeks has a long lower shadow
    condition_4 = any(last_five['Lower_Shadow'] > (last_five['high'] - last_five['low']) * 0.4)



    return condition_1 and condition_2 and condition_3 and condition_4


