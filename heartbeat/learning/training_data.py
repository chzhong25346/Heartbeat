import time
import numpy as np
import pandas as pd
from datetime import timedelta
from ..models import Quote,Report
from ..db.mapping import map_tdata
from ..db.write import bulk_save, bulk_update


def collect_tdata(s_dic):
    # s_f = s_dic['financials']
    s_l = s_dic['learning']

    for db_name in ['sp100','tsxci','nasdaq100']:
        print('Processing db "%s"...' % db_name)
        s = s_dic[db_name]
        report = get_report(s)
        df = fact_check(s, report)
        if(db_name == 'tsxci'):
            df['symbol'] = df['symbol'] + '.TO'
        models = map_tdata(df)
        bulk_save(s_l, models)


def ema(df, span):
    df = df.sort_index(ascending=True).last("18M")
    df = df['adjusted'].ewm(span=span, adjust=False).mean()
    return df


def slice_datetime(df, rdate, span, ptype):
    df = df.reset_index()
    start = int(df[df['date'] == rdate].index.values)
    end = start + span + 1
    if end in df.index:
        df = df.iloc[start:end]
        price = df.iloc[-1][ptype]
        return price


def get_report(s):
    df = pd.read_sql(s.query(Report).statement, s.bind, index_col='id')
    df['pattern'] = df['pattern'] != '0' # Pattern vlaues to True/False
    # Drop rows that are False in all columns
    df.drop(df.index[df['yr_high'] == 0] & df.index[df['yr_low'] == 0] &
            df.index[df['downtrend'] == 0] & df.index[df['uptrend'] == 0] &
            df.index[df['high_volume'] == 0] & df.index[df['low_volume'] == 0] &
            df.index[df['support'] == 0] & df.index[df['pattern'] == 0] &
            df.index[df['volume_price'] == 0], inplace=True)
    df['buy'] = np.nan
    df['hold'] = np.nan
    df['sell'] = np.nan
    return df


def fact_check(s, df):
    for index, row in df.iterrows():
        ticker = row['symbol']
        rdate = row['date']
        quote = pd.read_sql(s.query(Quote).filter(Quote.symbol == ticker).statement, s.bind, index_col='date')
        rema5 = ema(quote,5)
        rema21 = ema(quote,21)
        try:
            rprice = quote.loc[rdate]['close'] # recorded price when event happened
            fprice_21 = slice_datetime(quote.sort_index(ascending=True), rdate, 21, 'close') # price of 21 days after recorded price
            rprice_ema5 = rema5.loc[rdate] # ema5 price at recorded date
            rprice_ema21 = rema21.loc[rdate] # ema21 price at recorded date
            fprice_ema5 = slice_datetime(rema5, rdate, 5, 'adjusted') # price at 5 days moving forward from recorded ema5
            fprice_ema21 = slice_datetime(rema21, rdate, 21, 'adjusted') # price at 21 days moving forward from recorded ema5
            # Delta prices
            delta_ema5 = (fprice_ema5 / rprice_ema5 - 1) * 100
            delta_ema21 = (fprice_ema21 / rprice_ema21 - 1) * 100
            delta_price21 = (fprice_21 / rprice - 1) * 100
            if(delta_ema5 < 0 or delta_ema21 < 0):
                df.ix[index, 'sell'] = True
            elif(delta_ema5 > 0 and delta_ema21 > 0):
                if(delta_price21 >= 6):
                    df.ix[index, 'buy'] = True
                else:
                    df.ix[index, 'hold'] = True
            print('--> %s' % ticker)
        except:
            print('(%s)' % ticker)
            pass
    # remove all buy/sell/hold all is False and do clearning
    df.dropna(subset=['buy', 'sell', 'hold'],how='all', inplace =True)
    df.reset_index(inplace=True)
    df.fillna(False, inplace=True)
    df = df.drop('id', axis=1)
    return df
