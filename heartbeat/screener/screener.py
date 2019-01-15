import collections
import pandas as pd
from ..models import Income, BalanceSheet, Cashflow
from ..report.fundamental import get_ratios


def screening(s):
    print('Processing...')
    bs_ann = pd.read_sql(s.query(BalanceSheet).filter(BalanceSheet.period == "annual").statement, s.bind, index_col='symbol')
    bs_quart = pd.read_sql(s.query(BalanceSheet).filter(BalanceSheet.period == "quarterly").statement, s.bind, index_col='symbol')
    ic_ann = pd.read_sql(s.query(Income).filter(Income.period == "annual").statement, s.bind, index_col='symbol')
    ic_quart = pd.read_sql(s.query(Income).filter(Income.period == "quarterly").statement, s.bind, index_col='symbol')
    cf_ann = pd.read_sql(s.query(Cashflow).filter(Cashflow.period == "annual").statement, s.bind, index_col='symbol')
    cf_quart = pd.read_sql(s.query(Cashflow).filter(Cashflow.period == "quarterly").statement, s.bind, index_col='symbol')

    vigilance_L = vigilance([bs_ann, bs_quart])
    prospects_L = prospects([ic_ann, ic_quart])
    liqudity_L = liqudity([cf_ann, cf_quart])

    list = vigilance_L + prospects_L + liqudity_L
    picks = [item for item, count in collections.Counter(list).items() if count > 2]
    print(40*'-' + '\n' + 15*' ' +"Screening Picks" + "\n" + 40*'-')
    print(', '.join(picks))

    print(40*'-' + '\n' + 15*' ' + "Undervalued" + "\n" + 40*'-')
    print(', '.join(undervalued(picks)))


def vigilance(df_list):
    # D/E < 0.5(includes companys no debt) and CR >1.5 and Debt change within 10%
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
            if( DE < 0.5 and CR > 1.5 and all(totalDebt < 1) and all(totalDebt > -1)):
                list.append(ticker)
    return [item for item, count in collections.Counter(list).items() if count > 1]


def prospects(df_list):
    # Revenue and Opt Income change within 10% and all positive Opt Income
    list = []
    for df in df_list:
        df.fillna(0, inplace=True)
        for ticker in df.index.unique().tolist():
            operatingIncome = df.iloc[df.index == ticker].sort_values(by='date')['operatingIncome'].pct_change(periods=1).dropna()
            totalRevenue = df.iloc[df.index == ticker].sort_values(by='date')['totalRevenue'].pct_change(periods=1).dropna()
            if(all(df.iloc[df.index == ticker]['operatingIncome'] > 0) and all(operatingIncome < 1) and all(operatingIncome > -1) and
                all(totalRevenue < 1) and all(totalRevenue > -1) ):
                list.append(ticker)
    return [item for item, count in collections.Counter(list).items() if count > 1]


def liqudity(df_list):
    # Cash from Operating postive and Cash from Investing/Financing negative
    list = []
    for df in df_list:
        df.fillna(0, inplace=True)
        for ticker in df.index.unique().tolist():
            operating = df.iloc[df.index == ticker].sort_values(by='date')['totalCashFromOperatingActivities']
            investing = df.iloc[df.index == ticker].sort_values(by='date')['totalCashflowsFromInvestingActivities']
            financing = df.iloc[df.index == ticker].sort_values(by='date')['totalCashFromFinancingActivities']
            if(all(operating > 0) and all(investing < 0) and all(financing < 0)):
                list.append(ticker)
    return [item for item, count in collections.Counter(list).items() if count > 1]


def undervalued(tickerL):
    # PE * PB < 22.5 for now
    list = []
    for ticker in tickerL:
        pe, pb = get_ratios(ticker)
        if (pe < 15 and pb < 1.5):
            list.append(ticker)
    return list
