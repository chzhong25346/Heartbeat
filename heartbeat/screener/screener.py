import collections
import pandas as pd
import numpy as np
from ..models import Income, BalanceSheet, Cashflow, Keystats
from ..report.fundamental import get_ratios, intrinsic_value
from ..utils.fetch import get_keyStats


def screen_full(s):
    print('Processing...')
    bs_ann = pd.read_sql(s.query(BalanceSheet).filter(BalanceSheet.period == "annual").statement, s.bind, index_col='symbol')
    bs_quart = pd.read_sql(s.query(BalanceSheet).filter(BalanceSheet.period == "quarterly").statement, s.bind, index_col='symbol')
    ic_ann = pd.read_sql(s.query(Income).filter(Income.period == "annual").statement, s.bind, index_col='symbol')
    ic_quart = pd.read_sql(s.query(Income).filter(Income.period == "quarterly").statement, s.bind, index_col='symbol')
    cf_ann = pd.read_sql(s.query(Cashflow).filter(Cashflow.period == "annual").statement, s.bind, index_col='symbol')
    cf_quart = pd.read_sql(s.query(Cashflow).filter(Cashflow.period == "quarterly").statement, s.bind, index_col='symbol')

    vigilance_L = vigilance([bs_ann, bs_quart])
    prospects_L = prospects([ic_ann, ic_quart])
    fidelity_L = fidelity([cf_ann, cf_quart])

    list = vigilance_L + prospects_L + fidelity_L
    picks = [item for item, count in collections.Counter(list).items() if count > 2]
    print(40*'-' + '\n' + 15*' ' +"Screening Picks" + "\n" + 40*'-')
    print(intrinsicValue(s, picks))

    print(40*'-' + '\n' + 10*' ' + "Undervalued (PE,PB)" + "\n" + 40*'-')
    print((', '.join(underValued(picks))))


def vigilance(df_list):
    # D/E < 1(includes companys no debt) and CR >1.5 and Debt change within 10%
    list = []
    for df in df_list:
        df.fillna(0, inplace=True)
        for ticker in df.index.unique().tolist():
            longTermDebt = df.iloc[df.index == ticker]['longTermDebt'].mean()
            shortLongTermDebt = df.iloc[df.index == ticker]['shortLongTermDebt'].mean()
            totalStockholderEquity = df.iloc[df.index == ticker]['totalStockholderEquity'].mean()
            totalCurrentAssets = df.iloc[df.index == ticker]['totalCurrentAssets'].mean()
            totalCurrentLiabilities = df.iloc[df.index == ticker]['totalCurrentLiabilities'].mean()
            totalDebt = (df.iloc[df.index == ticker].sort_values(by='date')['longTermDebt']
                        + df.iloc[df.index == ticker].sort_values(by='date')['shortLongTermDebt'])
            totalDebt = totalDebt.pct_change(periods=1).dropna()
            DE = (longTermDebt+shortLongTermDebt) / totalStockholderEquity
            CR = totalCurrentAssets / totalCurrentLiabilities
            if( DE < 1 and CR > 1.5 and all(totalDebt < 1) and all(totalDebt > -1)):
                list.append(ticker)
    return [item for item, count in collections.Counter(list).items() if count > 1]


def prospects(df_list):
    # Revenue, Opt Income & Gross profit change within 10% and all positive Opt Income & EBIT margin,
    list = []
    for df in df_list:
        df.fillna(0, inplace=True)
        for ticker in df.index.unique().tolist():
            operatingIncome_pct = df.iloc[df.index == ticker].sort_values(by='date')['operatingIncome'].pct_change(periods=1).dropna()
            totalRevenue_pct = df.iloc[df.index == ticker].sort_values(by='date')['totalRevenue'].pct_change(periods=1).dropna()
            totalRevenue = df.iloc[df.index == ticker].sort_values(by='date')['totalRevenue']
            grossProfit = df.iloc[df.index == ticker].sort_values(by='date')['grossProfit']
            grossProft_pct = (grossProfit/totalRevenue*100).pct_change(periods=1).dropna()
            incomeBeforeTax = df.iloc[df.index == ticker].sort_values(by='date')['incomeBeforeTax']
            EBITmargin = (incomeBeforeTax/totalRevenue*100)
            if(all(df.iloc[df.index == ticker]['operatingIncome'] > 0) and all(EBITmargin > 0) and
                all(operatingIncome_pct < 1) and all(operatingIncome_pct > -1) and
                all(totalRevenue_pct < 1) and all(totalRevenue_pct > -1) and
                all(grossProft_pct < 1) and all(grossProft_pct > -1)):
                list.append(ticker)
    return [item for item, count in collections.Counter(list).items() if count > 1]


def fidelity(df_list):
    # Cash from Operating - capitalExpenditures positive
    # Cash from Operating postive and Cash from Investing/Financing negative
    list = []
    for df in df_list:
        df.fillna(0, inplace=True)
        for ticker in df.index.unique().tolist():
            operating = df.iloc[df.index == ticker].sort_values(by='date')['totalCashFromOperatingActivities']
            investing = df.iloc[df.index == ticker].sort_values(by='date')['totalCashflowsFromInvestingActivities']
            financing = df.iloc[df.index == ticker].sort_values(by='date')['totalCashFromFinancingActivities']
            capex = abs(df.iloc[df.index == ticker].sort_values(by='date')['capitalExpenditures'])
            if(all(operating-capex > 0) and all(operating > 0) and all(investing < 0) and all(financing < 0)):
                list.append(ticker)
    return [item for item, count in collections.Counter(list).items() if count > 1]


def intrinsicValue(s, tickerL):
    # Calculate IV/ps with filterd list
    dic = {}
    for ticker in tickerL:
        # df = get_keyStats(ticker)   ---- web way
        df = pd.read_sql(s.query(Keystats).filter(Keystats.symbol == ticker).statement, s.bind, index_col='date')
        df = df.replace([0], [np.nan])
        IVps = intrinsic_value(df)
        dic.update({ticker:IVps})
    result = pd.DataFrame.from_dict(dic,orient='index')
    result.columns = ['IV/s']
    return result


def underValued(tickerL):
    # PE * PB < 22.5 for now
    list = []
    for ticker in tickerL:
        pe, pb = get_ratios(ticker)
        if ((pe != None) or (pb != None)):
            if (pe < 15 and pb < 1.5):
                list.append(ticker)
    return list



# def return_on_equity(df_ic,df_bs):
#     ic_ticker_L = df_ic.index.unique().tolist()
#     bs_ticker_L = df_bs.index.unique().tolist()
#     ticker_L = [item for item, count in collections.Counter(ic_ticker_L + bs_ticker_L).items() if count > 1]
#     df_ic.fillna(0, inplace=True)
#     df_bs.fillna(0, inplace=True)
#     list = []
#     for ticker in ticker_L:
#         netIncome = df_ic.iloc[df_ic.index == ticker].sort_values(by='date')['netIncome']
#         totalStockholderEquity = df_bs.iloc[df_bs.index == ticker].sort_values(by='date')['totalStockholderEquity']
#         roe = netIncome/totalStockholderEquity*100
#         if(all(roe > 7)):
#             list.append(ticker)
#     return list
