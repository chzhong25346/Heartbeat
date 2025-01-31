import pandas as pd
from ..models import Quote, Index
import numpy as np


def findBuyNegative(s_dic):
    """Find stocks meeting weekly MACD conditions across multiple databases."""
    print("\nCondition 1: MACD and Signal Line both below zero.\n"
          "Condition 2: MACD has yet crossed above Signal Line.\n"
          "Condition 3: Histogram increasing for 3 weeks.\n"
          "Condition 4: Any of the last 5 weeks has a long lower shadow.\n"
          "Condition 5: Histogram has 1 wave pattern.")
    for db_name in ['tsxci', 'nasdaq100', 'sp100', 'eei']:

        print(f'\nFive Weekly Buy Negative Company(s) in {db_name}:')
        print('----------------------------------------')
        s = s_dic[db_name]  # Get SQLAlchemy session
        indexes = pd.read_sql(s.query(Index).statement, s.bind)  # Fetch stock symbols

        for ticker in indexes['symbol'].tolist():
            # if ticker == "TD":  # Only process SAP (adjust as needed)
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


def check_histogram_wave(df_hist):
    df_hist = df_hist.to_frame().copy()

    # Identify separate negative periods by assigning a unique group ID
    df_hist['negative_sequence'] = (df_hist['Hist'] >= 0).astype(int).diff().ne(0).cumsum()

    # Reset index to make 'date' a column
    df_hist_reset = df_hist.reset_index()

    # Filter negative values and group by sequence
    negative_sequences = df_hist_reset[df_hist_reset['Hist'] < 0].groupby('negative_sequence').agg(
        start=('date', 'min'),
        end=('date', 'max')
    ).reset_index()

    # Find the most recent negative sequence
    latest_negative_period = negative_sequences.iloc[-1]

    # Filter for the most recent continuous negative period
    df_filtered = df_hist_reset[
        (df_hist_reset['negative_sequence'] == latest_negative_period['negative_sequence'])
    ].copy()  # Explicit copy to avoid SettingWithCopyWarning

    # Identify direction changes
    df_filtered.loc[:, 'diff'] = df_filtered['Hist'].diff()

    # Determine trend direction (+1 for increasing, -1 for decreasing, 0 for no change)
    df_filtered.loc[:, 'trend'] = np.sign(df_filtered['diff'])

    # Count waves: A wave occurs when 3+ consecutive downs are followed by 3+ consecutive ups (or vice versa)
    wave_count = 0
    streak = 1
    last_trend = None  # Track last trend direction
    consecutive_downs = 0
    consecutive_ups = 0

    for i in range(1, len(df_filtered)):
        current_trend = df_filtered.iloc[i]['trend']

        if current_trend == df_filtered.iloc[i - 1]['trend']:
            streak += 1
        else:
            # Check if we have a valid downward or upward trend
            if last_trend == -1 and consecutive_downs >= 3 and consecutive_ups >= 3:
                wave_count += 1  # Count one complete wave (down + up)
                consecutive_downs = 0
                consecutive_ups = 0

            # Reset streak tracking
            streak = 1

        # Count consecutive trends
        if current_trend == -1:
            consecutive_downs += 1
        elif current_trend == 1:
            consecutive_ups += 1

        last_trend = current_trend

    # Final wave check in case the last trend completes a wave
    if last_trend == -1 and consecutive_downs >= 3 and consecutive_ups >= 3:
        wave_count += 1
    # print(df_filtered)
    # print(wave_count)
    return wave_count

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
    condition_1 = df_weekly['MACD'].iloc[-1] < 0 and df_weekly['Signal'].iloc[-1] < 0

    # Condition 2: MACD has yet crossed above Signal Line
    condition_2 = (
            df_weekly['MACD'].iloc[-1] < df_weekly['Signal'].iloc[-1]
    )

    # Condition 3: Histogram increasing for 3 weeks
    condition_3 = (
            last_three_hist.iloc[0] < last_three_hist.iloc[1] < last_three_hist.iloc[2]
    )

    # Condition 4: Any of the last 5 weeks has a long lower shadow
    condition_4 = any(last_five['Lower_Shadow'] > (last_five['high'] - last_five['low']) * 0.4)

    # Condition 5: Histogram has 1 wave pattern
    condition_5 = check_histogram_wave(df_weekly['Hist'])


    return condition_1 and condition_2 and condition_3 and condition_4 and condition_5


