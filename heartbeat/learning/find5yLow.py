import time
import numpy as np
import pandas as pd
from datetime import timedelta
from ..models import Quote, Report, Tdata, Findex, Gaps, Index
from ..db.mapping import map_tdata
from ..db.write import insert_onebyone
import sys


def find5yLow(s_dic):

    for db_name in ['tsxci','nasdaq100','sp100','eei']:
        print('\nFive Year Low Company(s) in %s:' % db_name)
        print('----------------------------------------')
        s = s_dic[db_name]
        indexes = pd.read_sql(s.query(Index).statement, s.bind)
        for ticker in indexes['symbol'].tolist():
            if get_up_down_ratio(s, ticker):
                corp_name = s.query(Index).filter(Index.symbol == ticker).first()
                print('%s (%s)' % (ticker, corp_name.company))

def get_up_down_ratio(s, ticker):
    # Get Quote
    df = pd.read_sql(s.query(Quote).filter(Quote.symbol == ticker).statement, s.bind, index_col='date')
    s.close()
    df = df[(df != 0).all(1)]
    # Latest Close
    df = df.sort_index(ascending=True).drop(columns=['id'])
    df_latest = df.iloc[-1]
    latest_close = df_latest['close']

    # 5 Year Ratio
    total_5y = len(df.last('60m'))
    up_5y = len(df.last('60m')[df.last('60m')['close'] > latest_close])
    down_5y = len(df.last('60m')[df.last('60m')['close'] < latest_close])
    up_5y_ratio = int(round(up_5y/total_5y,2)*100)
    down_5y_ratio = int(round(down_5y/total_5y,2)*100)
    if up_5y_ratio == 100 and down_5y_ratio == 0:
        return (up_5y_ratio,down_5y_ratio)

