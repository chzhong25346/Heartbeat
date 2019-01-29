from ..utils.fetch import get_financials, get_keyStats, fetch_findex
from ..utils.normalize import normalize_financials, reindex_missing
from ..db.mapping import map_income, map_balancesheet, map_cashflow, map_keystats, map_findex
from ..db.write import bulk_save
from ..db.read import has_table
from ..models import Findex
import time
import pandas as pd


def update_financials(s):
    # list = ['AAL']  ## Testing
    if (has_table(s, Findex) is None):
        print('Creating Index in financials db.')
        mapping_findex(s)
    list = pd.read_sql(s.query(Findex).statement, s.bind)['Symbol'].tolist()
    for ticker in list:
        print('--> %s' % ticker)
        time.sleep(10)
        fin_data = get_financials(ticker)
        try:
            income, balancesheet, cashflow = classify_findata(fin_data, ticker)
            mapping_write(s, income, 'income')
            mapping_write(s, balancesheet, 'balancesheet')
            mapping_write(s, cashflow, 'cashflow')
            # update keystats
            mapping_keystats(s, ticker)
        except Exception as e:
            print(e)
            pass


def classify_findata(data, ticker):
    incstat_yr = data['incomeStatementHistory']['incomeStatementHistory']
    incstat_qtrs = data['incomeStatementHistoryQuarterly']['incomeStatementHistory']
    balancesheet_yr = data['balanceSheetHistory']['balanceSheetStatements']
    balancesheet_qtrs = data['balanceSheetHistoryQuarterly']['balanceSheetStatements']
    cashflow_yr = data['cashflowStatementHistory']['cashflowStatements']
    cashflow_qtrs = data['cashflowStatementHistoryQuarterly']['cashflowStatements']

    incstat_yr_L = normalize_financials(incstat_yr, ticker, 'annual')
    incstat_qtrs_L = normalize_financials(incstat_qtrs, ticker, 'quarterly')
    income = reindex_missing(incstat_yr_L + incstat_qtrs_L, 'income')

    balancesheet_yr_L = normalize_financials(balancesheet_yr, ticker, 'annual')
    balancesheet_qtrs_L = normalize_financials(balancesheet_qtrs, ticker, 'quarterly')
    balancesheet = reindex_missing(balancesheet_yr_L + balancesheet_qtrs_L, 'balancesheet')

    cashflow_yr_L = normalize_financials(cashflow_yr, ticker, 'annual')
    cashflow_qtrs_L = normalize_financials(cashflow_qtrs, ticker, 'quarterly')
    cashflow = reindex_missing(cashflow_yr_L + cashflow_qtrs_L, 'cashflow')

    return income, balancesheet, cashflow


def mapping_write(s, list, type):
    if (type == 'income'):
        for df in list:
            models = map_income(df)
            bulk_save(s, models)
    elif (type == 'balancesheet'):
        for df in list:
            models = map_balancesheet(df)
            bulk_save(s, models)
    elif (type == 'cashflow'):
        for df in list:
            models = map_cashflow(df)
            bulk_save(s, models)


def mapping_keystats(s, ticker):
    df = get_keyStats(ticker.replace("-", ".")).fillna(0)
    df['date'] = df.index
    df['symbol'] = ticker
    for d in df.to_dict(orient='records'):
        models = map_keystats(pd.DataFrame.from_dict(d,orient='index').T)
        bulk_save(s, models)


def mapping_findex(s):
    df = fetch_findex()
    models = map_findex(df)
    bulk_save(s, models)
