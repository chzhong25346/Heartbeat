import pandas as pd
import datetime as dt
from ..utils.fetch import fetch_index, get_daily_adjusted
from ..utils.util import gen_id
from ..models import Index, Quote, Report, Transaction, Holding


def map_index(index_name):
    df = fetch_index(index_name)
    df_records = df.to_dict('records')
    model_instnaces = [Index(
        symbol = record['symbol'],
        company = record['company'],
        # sector = record['sector'],
        # industry = record['industry']
    ) for record in df_records]

    return model_instnaces


def map_quote(config,ticker,size,today_only,index_name):
    df = get_daily_adjusted(config,ticker,size,today_only,index_name)
    df_records = df.to_dict('records')
    model_instnaces = [Quote(
        id = gen_id(ticker+str(record['date'])),
        symbol = ticker,
        date = record['date'],
        open = record['open'],
        high = record['high'],
        low = record['low'],
        close = record['close'],
        adjusted = record['adjusted close'],
        volume = record['volume']
    ) for record in df_records]

    return model_instnaces


def map_report(config,df):
    date = dt.datetime.today().strftime("%Y-%m-%d")
    df_records = df.to_dict('records')
    model_instnaces = [Report(
        symbol = record['symbol'],
        date = date,
        id = gen_id(record['symbol']+str(date)),
        yr_high = record['yr_high'],
        yr_low = record['yr_low'],
        downtrend = record['downtrend'],
        uptrend = record['uptrend'],
        high_volume = record['high_volume'],
        low_volume = record['low_volume'],
        pattern = record['pattern'],
        support = record['support']
    ) for record in df_records]
    logger.info('Mapping completed.')

    return model_instnaces


def map_transaction(df):
    date = dt.datetime.today().strftime("%Y-%m-%d")
    df_records = df.to_dict('records')
    model_instnaces = [Transaction(
        id = gen_id(record['symbol'] + record['type'] + str(date)),
        date = date,
        symbol = record['symbol'],
        price = record['price'],
        quantity = record['quantity'],
        settlement = record['settlement'],
        type = record['type'],
    ) for record in df_records]
    logger.info('Mapping completed.')

    return model_instnaces


def map_holding(df):
    df_records = df.to_dict('records')
    model_instnaces = [Holding(
        symbol = record['symbol'],
        avg_cost  = record['avg_cost'],
        quantity = record['quantity'],
        book_value  = record['book_value'],
        change_dollar  = record['change_dollar'],
        change_percent  = record['change_percent'],
        mkt_price  = record['mkt_price'],
        mkt_value  = record['mkt_value'],
        note  = record['note'],
    ) for record in df_records]
    logger.info('Mapping completed.')

    return model_instnaces
