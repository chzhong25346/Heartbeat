import collections
import pandas as pd
import numpy as np
from ..models import Income, BalanceSheet, Cashflow, Keystats, Findex
from ..report.fundamental import get_ratios, intrinsic_value
from ..utils.fetch import get_keyStats
from ..utils.util import beautify_dict
from .screener import underValued, intrinsicValue


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
        bs_ann,bs_quart,ic_ann,ic_quart,cf_ann,cf_quart = query_financials(s, tickerL)
        CR = current_ratio([bs_ann,bs_quart])
        DE = debt_to_equity_ratio([bs_ann,bs_quart])
        si_ann,si_qtr = steady_income([ic_ann,ic_quart])
        lq_ann,lq_qtr = liquidity([cf_ann,cf_quart])
        chosenL = set(CR+DE+si_ann+si_qtr+lq_ann+lq_qtr)
        uv = underValued(chosenL)
        ivps = intrinsicValue(s, chosenL)
        ### PRINTS #####
        print(50*'-' + '\n' + 10*' ' + business + "\n" + 50*'-')
        print(', '.join(tickerL) + "\n" + 50*'-')
        print('\n' + 8*'-' + 'Current Ratio' + 8*'-' )
        print(', '.join(CR))
        print('\n' + 10*'-'  + 'D/E Ratio' + 10*'-' )
        print(', '.join(DE))
        print('\n' + 8*'-'  + 'Steady Income' + 8*'-' )
        print('Annually: ' + ', '.join(si_ann))
        print('Quarterly: ' + ', '.join(si_qtr))
        print('\n' + 10*'-'  + 'Liquidity' + 10*'-' )
        print('Annually: ' + ', '.join(lq_ann))
        print('Quarterly: ' + ', '.join(lq_qtr))
        print('\n' + 10*'-'  + 'Undervalued' + 10*'-' )
        print(', '.join(uv))
        print('\n' + 8*'-'  + 'Intrinsic Value' + 8*'-' )
        print(ivps)


def query_financials(s, list):
    bs_ann = pd.read_sql(s.query(BalanceSheet).filter(BalanceSheet.symbol.in_(list)).filter(BalanceSheet.period == "annual").statement, s.bind, index_col='symbol').fillna(0)
    bs_quart = pd.read_sql(s.query(BalanceSheet).filter(BalanceSheet.symbol.in_(list)).filter(BalanceSheet.period == "quarterly").statement, s.bind, index_col='symbol').fillna(0)
    ic_ann = pd.read_sql(s.query(Income).filter(Income.symbol.in_(list)).filter(Income.period == "annual").statement, s.bind, index_col='symbol').fillna(0)
    ic_quart = pd.read_sql(s.query(Income).filter(Income.symbol.in_(list)).filter(Income.period == "quarterly").statement, s.bind, index_col='symbol').fillna(0)
    cf_ann = pd.read_sql(s.query(Cashflow).filter(Cashflow.symbol.in_(list)).filter(Cashflow.period == "annual").statement, s.bind, index_col='symbol').fillna(0)
    cf_quart = pd.read_sql(s.query(Cashflow).filter(Cashflow.symbol.in_(list)).filter(Cashflow.period == "quarterly").statement, s.bind, index_col='symbol').fillna(0)
    return bs_ann,bs_quart,ic_ann,ic_quart,cf_ann,cf_quart


def current_ratio(df_list):
    picks = []
    for df in df_list:
        cr = df['totalCurrentAssets']/df['totalCurrentLiabilities']
        for ticker in set(cr.index.tolist()):
            if(all(cr.loc[ticker] > 1)):
                picks.append(ticker)
    return  [item for item, count in collections.Counter(picks).items() if count > 1]


def debt_to_equity_ratio(df_list):
    picks =[]
    for df in df_list:
        df['totaldebt'] = df['shortLongTermDebt']+df['longTermDebt']
        de = df['totaldebt']/df['totalStockholderEquity']
        for ticker in set(de.index.tolist()):
            if(all(de.loc[ticker] < 1)):
                picks.append(ticker)
    return  [item for item, count in collections.Counter(picks).items() if count > 1]


def steady_income(df_list):
    annual = []
    quarter  = []
    for seq,df in enumerate(df_list):
        for ticker in set(df.index.tolist()):
            operatingIncome_pct = df.loc[ticker].sort_values(by='date')['operatingIncome'].pct_change(periods=1).dropna() * 100
            netIncome_pct = df.loc[ticker].sort_values(by='date')['netIncome'].pct_change(periods=1).dropna() * 100
            if(all(operatingIncome_pct >= 0) and all(netIncome_pct > -5)):
                if(seq == 0):
                    annual.append(ticker)
                elif(seq == 1):
                    quarter.append(ticker)
    return annual, quarter


def liquidity(df_list):
    annual = []
    quarter  = []
    for seq,df in enumerate(df_list):
        for ticker in set(df.index.tolist()):
            operating = df.loc[ticker].sort_values(by='date')['totalCashFromOperatingActivities']
            capex = abs(df.loc[ticker].sort_values(by='date')['capitalExpenditures'])
            investing = df.loc[ticker]['totalCashflowsFromInvestingActivities']
            financing = df.loc[ticker]['totalCashFromFinancingActivities']
            fcf = operating - capex
            if(all(fcf >= 0) and all(investing < 0) and all(financing < 0)):
                if(seq == 0):
                    annual.append(ticker)
                elif(seq == 1):
                    quarter.append(ticker)
    return  annual, quarter
