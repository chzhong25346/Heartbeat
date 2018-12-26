from ..db.read import read_ticker
from ..db.db import Db
from .config import Config
from datetime import datetime
import pandas as pd
import numpy as np


def pick_stats(df, list, index_name):
    df = df[list]
    df.index=[index_name]
    df = df.T
    return df


def rename(df):
    df.columns = ['Market Cap (intraday)', 'Enterprise Value', 'Trailing P/E',
    'Forward P/E', 'PEG Ratio (5 yr expected)', 'Price/Sales (ttm)',
    'Price/Book (mrq)', 'Enterprise Value/Revenue',
    'Enterprise Value/EBITDA', 'Fiscal Year Ends',
    'Most Recent Quarter (mrq)', 'Profit Margin', 'Operating Margin (ttm)',
    'Return on Assets (ttm)', 'Return on Equity (ttm)', 'Revenue (ttm)',
    'Revenue Per Share (ttm)', 'Quarterly Revenue Growth (yoy)',
    'Gross Profit (ttm)', 'EBITDA', 'Net Income Avi to Common (ttm)',
    'Diluted EPS (ttm)', 'Quarterly Earnings Growth (yoy)',
    'Total Cash (mrq)', 'Total Cash Per Share (mrq)', 'Total Debt (mrq)',
    'Total Debt/Equity (mrq)', 'Current Ratio (mrq)',
    'Book Value Per Share (mrq)', 'Operating Cash Flow (ttm)',
    'Levered Free Cash Flow (ttm)', 'Beta (3Y Monthly)', '52-Week Change',
    'S&P500 52-Week Change', '52 Week High', '52 Week Low',
    '50-Day Moving Average', '200-Day Moving Average',
    'Avg Vol (3 month)', 'Avg Vol (10 day)', 'Shares Outstanding',
    'Float', '% Held by Insiders', '% Held by Institutions',
    'Shares Short (Nov 1, 2018)', 'Short Ratio (Nov 1, 2018)',
    'Short % of Float (Nov 1, 2018)',
    'Short % of Shares Outstanding (Nov 1, 2018)',
    'Shares Short (prior month Oct 1, 2018)',
    'Forward Annual Dividend Rate', 'Forward Annual Dividend Yield',
    'Trailing Annual Dividend Rate', 'Trailing Annual Dividend Yield',
    '5 Year Average Dividend Yield', 'Payout Ratio', 'Dividend Date',
    'Ex-Dividend Date', 'Last Split Factor (new per old)',
    'Last Split Date']
    return df


def generate_tickerL(index, index_L):
    ticker_L = []
    if (index in index_L):
        Config.DB_NAME = index
        db = Db(Config)
        s = db.session()
        ticker_L = read_ticker(s)
        if (index == 'tsxci'):
            ticker_L = [t + '.TO' for t in read_ticker(s)]
        s.close()
    else:
        print('%s not supported!'% index)
    return ticker_L


def normalize_financials(data, ticker, period):
    df_L = []
    for d in data:
        try:
            df = pd.DataFrame.from_dict(d, orient='columns')
            df.drop(['fmt','longFmt'], inplace=True)
            df.drop(['maxAge'], axis=1, inplace=True)
            exclude_L = ['endDate'] + df.columns[df.isnull().any()].tolist()
            df.loc[:, df.columns.difference(exclude_L).tolist()] = df.loc[:, df.columns.difference(exclude_L).tolist()].divide(1000, axis=1).astype(np.int64)
            df['symbol'] = ticker
            df['period'] = period
            df_L.append(df)
        except:
            pass
    return df_L


def reindex_missing(list, type):
    ic_cols = ['symbol','period','effectOfAccountingCharges', 'incomeTaxExpense','extraordinaryItems', 'interestExpense',
                'sellingGeneralAdministrative', 'netIncome', 'endDate', 'totalOtherIncomeExpenseNet', 'netIncomeFromContinuingOps',
                'totalRevenue', 'totalOperatingExpenses', 'netIncomeApplicableToCommonShares', 'minorityInterest', 'grossProfit','otherItems',
                'otherOperatingExpenses', 'nonRecurring', 'discontinuedOperations', 'researchDevelopment', 'ebit', 'operatingIncome', 'costOfRevenue', 'incomeBeforeTax']
    bs_cols = ['treasuryStock','commonStock','totalCurrentLiabilities','goodWill','otherStockholderEquity', 'totalAssets', 'propertyPlantEquipment',
                'intangibleAssets', 'accountsPayable', 'totalStockholderEquity','longTermDebt', 'capitalSurplus', 'retainedEarnings', 'otherCurrentLiab',
                'totalCurrentAssets','netReceivables', 'totalLiab', 'deferredLongTermAssetCharges','otherLiab', 'deferredLongTermLiab','otherCurrentAssets',
                'otherAssets','cash','minorityInterest','netTangibleAssets', 'inventory', 'longTermInvestments', 'shortLongTermDebt','endDate', 'shortTermInvestments',
                'symbol','period']
    cf_cols = ['totalCashFromFinancingActivities','netBorrowings','changeToOperatingActivities','depreciation','issuanceOfStock',
                'changeToLiabilities','capitalExpenditures','effectOfExchangeRate','dividendsPaid','totalCashFromOperatingActivities',
                'changeToNetincome','otherCashflowsFromInvestingActivities','investments','changeToAccountReceivables','changeInCash',
                'otherCashflowsFromFinancingActivities','endDate','netIncome','totalCashflowsFromInvestingActivities','changeToInventory',
                'repurchaseOfStock','symbol','period']
    df_L = []
    for df in list:
        if (type == 'income'):
            df = df.reindex(columns=ic_cols)
        elif (type == 'balancesheet'):
            df = df.reindex(columns=bs_cols)
        elif (type == 'cashflow'):
            df = df.reindex(columns=cf_cols)
        df = df.astype(object).where(pd.notnull(df), None)
        df_L.append(df)
    return df_L
