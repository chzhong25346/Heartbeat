import pandas as pd
import numpy as np
from ..utils.locate_db import locate_session
from ..utils.normalize import rename,pick_stats
import requests
from bs4 import BeautifulSoup
import re


def fundamental_output(s_dic, ticker):
    output = ''
    try:
        s, db_name, ticker, company_name = locate_session(s_dic, ticker)
        print(40*'-' + '\n' + ticker + ' - ' + company_name + "\n" + 40*'-')
        get_statistics(ticker,db_name)
        get_news(company_name)
    except Exception as e:
        # print(e)
        print("Failed to search! try again.")


def get_statistics(ticker, db_name):
    if(db_name == 'tsxci'):
        ticker = ticker+'.TO'
    url = 'https://finance.yahoo.com/quote/{0}/key-statistics?p={0}'.format(ticker)
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    dic = {}
    rows = soup.findAll('tr')
    for row in rows:
        cols = row.find_all('td')
        cols = [ele.text.strip() for ele in cols]
        dic.update(dict([cols]))
    df = pd.DataFrame(dic, index=[0])
    # df = rename(df)
    # df['Market Price(mrq)'] = float(df['Price/Book (mrq)']) * float(df['Book Value Per Share (mrq)'])
    list = ['Market Cap (intraday) 5', 'Enterprise Value 3', 'Trailing P/E',
            'Forward P/E 1', 'PEG Ratio (5 yr expected) 1', 'Price/Sales (ttm)',
            'Price/Book (mrq)']#, 'Market Price(mrq)']
    valuation = pick_stats(df, list, 'Valuation Measures') ###
    list = ['Profit Margin', 'Operating Margin (ttm)']
    profitability = pick_stats(df, list, 'Profitability') ###
    list = ['Return on Assets (ttm)', 'Return on Equity (ttm)']
    manag_eff = pick_stats(df, list, 'Management Effectiveness') ###
    list = ['Revenue (ttm)','Revenue Per Share (ttm)', 'Quarterly Revenue Growth (yoy)',
            'Gross Profit (ttm)', 'EBITDA', 'Quarterly Earnings Growth (yoy)']
    inc_stat = pick_stats(df, list, 'Income Statement') ###
    list = ['Total Debt (mrq)','Total Debt/Equity (mrq)',
            'Current Ratio (mrq)','Book Value Per Share (mrq)']
    balance_sheet = pick_stats(df, list, 'Balance Sheet') ###
    list = ['Operating Cash Flow (ttm)','Levered Free Cash Flow (ttm)']
    cash_flow = pick_stats(df, list, 'Cash Flow Statement') ###
    list = ['Forward Annual Dividend Yield 4','Trailing Annual Dividend Yield 3',
            'Payout Ratio 4']
    dividends = pick_stats(df, list, 'Dividends') ###
    print('\n'+ 35*'-' + '\n' + 'Financial Statistics' + '\n'+ 35*'-' + '\n' )
    print(valuation, profitability, manag_eff, inc_stat, balance_sheet, cash_flow, dividends,  sep='\n')


def get_news(text):
    tag_re = re.compile(r'(<!--.*?-->|<[^>]*>)')
    url = 'https://www.google.com/search?q={0}&source=lnms&tbm=nws'.format(text)
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    results = soup.find_all('div', class_='st')
    print('\n'+ 35*'-' + '\n' + 'Recent News' + '\n'+ 35*'-' )
    for h in results[0:5]:
        h = tag_re.sub('', str(h))
        print(">>> "+h)


def get_ratios(ticker):
    url = 'https://finance.yahoo.com/quote/{0}/key-statistics?p={0}'.format(ticker)
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    dic = {}
    rows = soup.findAll('tr')
    for row in rows:
        cols = row.find_all('td')
        cols = [ele.text.strip() for ele in cols]
        dic.update(dict([cols]))
    try:
        pe = float(dic['Trailing P/E'])
        pb = float(dic['Price/Book (mrq)'])
    except:
        pe = float(dic['Forward P/E 1'])
        pb = float(dic['Price/Book (mrq)'])
    return pe,pb


# def get_roe(ticker):
#     url = 'https://finance.yahoo.com/quote/{0}/key-statistics?p={0}'.format(ticker)
#     response = requests.get(url)
#     soup = BeautifulSoup(response.text, 'html.parser')
#     dic = {}
#     rows = soup.findAll('tr')
#     try:
#         for row in rows:
#             cols = row.find_all('td')
#             cols = [ele.text.strip() for ele in cols]
#             dic.update(dict([cols]))
#             roe = float(dic['Return on Equity (ttm)'][:-1])
#         return roe
#     except:
#         return None
