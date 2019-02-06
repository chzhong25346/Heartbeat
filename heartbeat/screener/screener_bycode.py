import collections
import pandas as pd
import numpy as np
from ..models import Income, BalanceSheet, Cashflow, Keystats, Findex
from ..report.fundamental import get_ratios, intrinsic_value
from ..utils.fetch import get_keyStats
# from sqlalchemy import and_, or_, not_


def screen_bycode(s, code, type):
    findex = pd.read_sql(s.query(Findex).filter(getattr(Findex, type) == code).statement, s.bind, index_col='Symbol')
    tickerL = findex.index.tolist()
    if(len(tickerL) == 0):
        print('%s: %s is invalid!' % (type, code))
    else:
        if(type=='Secode'):
            business = findex.Sector.values[0]
        if(type=='Indcode'):
            business = findex.Industry.values[0]
        print(50*'-' + '\n' + 10*' ' + business + "\n" + 50*'-')
        bs_ann,bs_quart,ic_ann,ic_quart,cf_ann,cf_quart = query_financials(s, tickerL)
        current_ratio([bs_ann])


def query_financials(s, list):
    bs_ann = pd.read_sql(s.query(BalanceSheet).filter(BalanceSheet.symbol.in_(list)).filter(BalanceSheet.period == "annual").statement, s.bind, index_col='symbol').fillna(0)
    bs_quart = pd.read_sql(s.query(BalanceSheet).filter(BalanceSheet.symbol.in_(list)).filter(BalanceSheet.period == "quarterly").statement, s.bind, index_col='symbol').fillna(0)
    ic_ann = pd.read_sql(s.query(Income).filter(Income.symbol.in_(list)).filter(Income.period == "annual").statement, s.bind, index_col='symbol').fillna(0)
    ic_quart = pd.read_sql(s.query(Income).filter(Income.symbol.in_(list)).filter(Income.period == "quarterly").statement, s.bind, index_col='symbol').fillna(0)
    cf_ann = pd.read_sql(s.query(Cashflow).filter(Cashflow.symbol.in_(list)).filter(Cashflow.period == "annual").statement, s.bind, index_col='symbol').fillna(0)
    cf_quart = pd.read_sql(s.query(Cashflow).filter(Cashflow.symbol.in_(list)).filter(Cashflow.period == "quarterly").statement, s.bind, index_col='symbol').fillna(0)
    return bs_ann,bs_quart,ic_ann,ic_quart,cf_ann,cf_quart


def current_ratio(df_list):
    CR_L = []
    for df in df_list:
        df['CR'] = df['totalCurrentAssets']/df['totalCurrentLiabilities']
        top = df['CR'].groupby(df.index).mean().sort_values(ascending=False).head(5)#.index.tolist()


    # print(CR_L)
