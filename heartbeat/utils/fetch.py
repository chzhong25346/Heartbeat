import urllib3,certifi
import pandas as pd
import json
import time
import os
from ..utils.util import normalize_Todash
from datetime import datetime as dt
from alpha_vantage.timeseries import TimeSeries
import logging
logger = logging.getLogger('main.fetch')


def fetch_index(index_name):
    path = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(path, index_name+'.csv')
    try:
        if (index_name == 'nasdaq100'):
            data = pd.read_csv(filename)
            data.columns = ['symbol', 'company', 'lastsale', 'netchange', 'netchange', 'share_volume', 'Nasdaq100_points','Unnamed: 7']
            data = data.drop(['company', 'lastsale', 'netchange', 'netchange', 'share_volume', 'Nasdaq100_points', 'Unnamed: 7'], axis=1)
            data.index.name = 'symbol'
            data = normalize_Todash(data)
            return data
        elif (index_name == 'tsxci' or index_name == 'sp100'):
            data = pd.read_csv(filename, na_filter = False)
            data.columns = ['symbol', 'company']
            # data = normalize_Todash(data)
            return data
    except Exception as e:
        logger.error('Unable to fetch index! {%s}' % e)


# def fetch_index():
#     page= 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
#     https = urllib3.PoolManager( cert_reqs='CERT_REQUIRED', ca_certs=certifi.where(),)
#     try:
#         url = https.urlopen('GET',page)
#         page_d = pd.read_html(url.data,header=0,keep_default_na=False) # NA -> NaN is National Bank of Canada
#         page_d[0].columns = ['symbol', 'company', 'Fillings', 'sector', 'industry', 'Location', 'First Added', 'CIK', 'Founded']
#         data = page_d[0]
#         data = data.drop(['Fillings', 'Location', 'First Added', 'CIK', 'Founded'], axis=1)
#         data.index.name = 'symbol'
#         data = normalize_Todash(data)
#         return data
#     except Exception as e:
#         logger.error('Unable to fetch index! {%s}' % e)


def get_daily_adjusted(config,ticker,size,today_only,index_name):
    key = config.AV_KEY
    ts = TimeSeries(key)
    try:
        time.sleep(15)
        if(index_name == 'tsxci'):
            data, meta_data = ts.get_daily_adjusted(ticker+'.TO',outputsize=size)
        else:
            data, meta_data = ts.get_daily_adjusted(ticker,outputsize=size)
        df = pd.DataFrame.from_dict(data).T
        df = df.drop(["7. dividend amount","8. split coefficient"], axis=1)
        df.columns = ["open","high","low","close","adjusted close","volume"]
        if today_only:
            df = df.loc[df.index.max()].to_frame().T
            df.index.name = 'date'
            df = df.reset_index()
            return df
        else:
            df.index.name = 'date'
            df = df.reset_index()
            return df
    except Exception as e:
        logger.error(e)
