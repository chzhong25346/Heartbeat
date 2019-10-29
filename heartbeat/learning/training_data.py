import time
import numpy as np
import pandas as pd
from datetime import timedelta
from ..models import Quote,Report,Tdata,Findex
from ..db.mapping import map_tdata
from ..db.write import insert_onebyone
import sys


def collect_tdata(s_dic):
    # s_f = s_dic['financials']
    s_l = s_dic['learning']
    s_f = s_dic['financials']

    tdata = pd.read_sql(s_l.query(Tdata).statement, s_l.bind, index_col='id')

    for db_name in ['tsxci','nasdaq100','sp100']:
    # for db_name in ['nasdaq100']:
    # for db_name in ['learning']:
        print('Processing db "%s"...' % db_name)
        s = s_dic[db_name]

        report = get_report(s, tdata, db_name)

        df = fact_check(s, report)

        if(db_name == 'tsxci'):
            df['symbol'] = df['symbol'] + '.TO'

        df = map_code(s_f, df)

        models = map_tdata(df)
        insert_onebyone(s_l, models)
        print('Completed writing "%s".' % db_name)


def ema(df, span):
    # df = df.sort_index(ascending=True)[-378:] #.last("18M")
    # df = df['adjusted'].ewm(span=span, adjust=False).mean()
    return df['adjusted'].ewm(span=span, adjust=False).mean()[-378:]


def slice_datetime(df, rdate, span, ptype):
    df = df.reset_index()
    start = int(df[df['date'] == rdate].index.values)
    end = start + span + 1
    if end in df.index:
        df = df.iloc[start:end]
        price = df.iloc[-1][ptype]
        return price


def get_report(s, tdata, db_name):
    df = pd.read_sql(s.query(Report).statement, s.bind, index_col='id')
    # Copy tlatest that has latest tdata rows
    tlatest = tdata.sort_values('date', ascending=False).drop_duplicates(['symbol'])
    # Drop rows that are False in all columns
    df.drop(df.index[df['yr_high'] == 0] & df.index[df['yr_low'] == 0] &
            df.index[df['downtrend'] == 0] & df.index[df['uptrend'] == 0] &
            df.index[df['high_volume'] == 0]  & df.index[df['rsi'] == '0'] & df.index[df['macd'] == '0'] &
            df.index[df['volume_price'] == 0], inplace=True)
    # make a copy of orginal columns
    df.reset_index(inplace=True)
    cols = df.columns.values
    # Copy symbol column
    if db_name == 'tsxci':
        df['symbol2'] = df['symbol']
        df['symbol'] = df['symbol'] + '.TO'
    # Choose reports newer than latest date in Tdata
    df = df.merge(tlatest, on='symbol', suffixes={'','_y'}).query('date > date_y') ######### ALL TDATA UPDATE
    # Restore symbol without .TO
    if db_name == 'tsxci':
        df['symbol'] = df['symbol2']
    # Restore orginal report columns
    df.set_index('id', inplace=True, drop=False)
    df = df[cols].drop('id', axis=1)
    # Add tdata columns
    df['buy'] = np.nan
    df['hold'] = np.nan
    df['sell'] = np.nan
    df['rating'] = np.nan
    return df


def fact_check(s, df):
    for index, row in df.iterrows():
        ticker = row['symbol']
        # print('--> %s' % ticker)
        rdate = row['date']
        quote = pd.read_sql(s.query(Quote).filter(Quote.symbol == ticker).statement, s.bind, index_col='date').sort_index(ascending=True)
        rema5 = ema(quote,5)
        rema21 = ema(quote,21)
        ref = oneyear_ref(rdate, quote)
        try:
            rprice = quote.loc[rdate]['close'] # recorded price when event happened
            fprice_21 = slice_datetime(quote, rdate, 21, 'close') # price of 21 days after recorded price
            rprice_ema5 = rema5.loc[rdate] # ema5 price at recorded date
            rprice_ema21 = rema21.loc[rdate] # ema21 price at recorded date
            fprice_ema5 = slice_datetime(rema5, rdate, 5, 'adjusted') # price at 5 days moving forward from recorded ema5
            fprice_ema21 = slice_datetime(rema21, rdate, 21, 'adjusted') # price at 21 days moving forward from recorded ema5
            # Delta prices
            # print(fprice_21, fprice_ema5, fprice_ema21 )
            delta_ema5 = (fprice_ema5 / rprice_ema5 - 1) * 100
            delta_ema21 = (fprice_ema21 / rprice_ema21 - 1) * 100
            delta_price21 = (fprice_21 / rprice - 1) * 100
            # Rating
            rating = cal_rating(ref, delta_price21)
            #
            if(delta_ema5 >= 0 and delta_ema21 >= 0):
                df.ix[index, 'rating'] = rating
                if(rating == 0.5):
                    df.ix[index, 'hold'] = True
                else:
                    df.ix[index, 'buy'] = True
            elif(delta_ema5 < 0 or delta_ema21 < 0):
                df.ix[index, 'rating'] = rating*-1
                df.ix[index, 'sell'] = True
        # except Exception as e:
        except:
            # exc_type, exc_obj, exc_tb = sys.exc_info()
            # print('(%s)' % ticker)
            # print(e, exc_tb.tb_lineno)
            pass
    # remove all buy/sell/hold all is False and do clearning
    df.dropna(subset=['buy', 'sell', 'hold'],how='all', inplace =True)
    df.reset_index(inplace=True)
    df.fillna(False, inplace=True)
    df = df.drop('id', axis=1)
    return df


def oneyear_ref(rdate, df):
    df = df.sort_index(ascending=True)
    oneyear = df.loc[:rdate][-254:]
    min = float(oneyear['close'].min())
    max = float(oneyear['close'].max())
    if min > 0:
        ref = abs((max/min-1)/6*100)
        return ref
    else:
        return None

def cal_rating(ref, delta_price21):
    p21 = abs(delta_price21)
    if 0 <= p21 <= ref*0.5:
        return 0.5
    elif ref*0.5 < p21 <= ref:
        return 1
    elif ref < p21 <= ref*2:
        return 2
    elif ref*2 < p21:
        return 3


def map_code(s, df):
    findex = pd.read_sql(s.query(Findex).statement, s.bind, index_col='Symbol')
    df['secode'] = df['symbol'].map(findex['Secode'])
    df['indcode'] = df['symbol'].map(findex['Indcode'])
    return df
