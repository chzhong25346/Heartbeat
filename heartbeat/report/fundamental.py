import pandas as pd
import numpy as np
from ..utils.locate_db import locate_session
from ..utils.normalize import rename,pick_stats
from ..utils.fetch import get_keyStats
from ..models import Income, BalanceSheet, Cashflow, Keystats, Findex
from bs4 import BeautifulSoup
from datetime import datetime
import requests
import re


def fundamental_output(s, ticker):
    df = pd.read_sql(s.query(Findex).filter(Findex.Symbol == ticker).statement,
                        s.bind, index_col='Symbol')
    tickerL = df.index.tolist()
    output = ''
    try:
        if(len(tickerL) == 0):
            print('Searching external sources...')
            ticker = ticker.upper()
            print(40*'-' + '\n' + ticker + ' - ' "\n" + 40*'-')
            get_statistics(ticker, s, 'external')
        else:
            print('Found in local Database.')
            ticker = tickerL[0]
            company = df.loc[ticker]['Name']
            print(40*'-' + '\n' + ticker + ' - ' + company + "\n" + 40*'-')
            get_statistics(ticker, s, 'local')
            get_news(company)
            get_Indinfo(ticker, s)
    except Exception as e:
        # print(e)
        print('If %s is a Canadian stock, please suffix .TO' % ticker)
        print("Unable to search! Try again.")


def get_statistics(ticker, s, type):
    ticker = ticker.upper()
    # Intrinsic Value
    if(type == 'local'):
        df = pd.read_sql(s.query(Keystats).filter(Keystats.symbol == ticker).statement, s.bind, index_col='date')
        df = df.replace([0], [np.nan])
    elif(type == 'external'):
        df = get_keyStats(ticker)
    IVps = intrinsic_value(df)
    # YoY_financials
    yoy = yoy_financials(df)
    # Net Trade Cyclce
    NTC = netTradeCycle(s, ticker)
    # fetching key-stats from Yahoo
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
    # print(df.columns)
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
    list = ['Beta (3Y Monthly)', '52-Week Change 3']
    price_his = pick_stats(df, list, 'Price History') ###
    print(35*'-' + '\n' + 'Financial Statistics' + '\n'+ 35*'-' + '\n' )
    if (yoy is not None):
        print(yoy)
    print('Intrinsic Value Per Share: %s' % IVps)
    if (NTC is not None):
        print('\n' + '------ Net Trading Cycle ------')
        print(NTC)
    print(valuation, profitability, manag_eff, inc_stat, balance_sheet, cash_flow, dividends, price_his,  sep='\n')


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
    # print(ticker) #CHECKPOINT
    if(dic['Forward P/E 1'] != 'N/A' and '-' not in dic['Forward P/E 1'] and dic['Price/Book (mrq)'] != 'N/A'):
        try:
            pe = float(dic['Trailing P/E'])
            pb = float(dic['Price/Book (mrq)'])
        except:
            pe = float(dic['Forward P/E 1'])
            pb = float(dic['Price/Book (mrq)'])
        return pe,pb
    else:
        return None, None


def intrinsic_value(df):
    # http://news.morningstar.com/classroom2/course.asp?docId=145102&page=1&CN=sample
    try:
        FCF = df['freeCashFlow'].dropna() # Free cash flow
        nic = df['netIncome'].dropna()
        shares = df['shares'].dropna()
    except:
        FCF = df['FreeCashFlow'].dropna() # Free cash flow
        nic = df['NetIncome'].dropna()
        shares = df['Shares'].dropna()
        pass
    g = 0.03 # Inflation rate 3% as the perpetuity growth rate, which is close to the historical average growth rate of the U.S. economy
    R = 0.1 # Required Return (Discount Rate)
    avg_FCF = FCF.mean() # Average Free cash flow
    begining = int(round(nic[nic.index.min()])) # begining income
    ending = int(round(nic[nic.index.max()])) # ending income
    klength = len(FCF) # number of years in Free Cash Flow
    avg_growth_rate = (((ending/begining)**(1/klength))-1).real # average income growth rate
    CFn = {} #  Cash Flow in the Last Individual Year Estimated, in this case Year 10 cash flow
    temp = None
    for k in range(1, klength+1):
        if(k == 1):
            temp = round(avg_FCF*(1+avg_growth_rate),2)
            CFn.update({k:temp})
        else:
            temp = round(temp*(1+avg_growth_rate),2)
            CFn.update({k:temp})
    DFCF = {} # Discounted Free Cash Flow
    for key, value in CFn.items():
        DF = round((1+R)**key,2)
        DFCF.update({key:round(value*DF,0)})
    sum_DFCF = sum(DFCF.values()) # Discounted Free Cash Flow, Years 1-N
    N = max(k for k, v in CFn.items()) # Most recent year
    CFlast = CFn[N]  # FCF in most recent year
    perV = round((CFlast*(1+g)/(R-g)),2) # Perpetuity Value
    PVPV = round(perV/(1+R)**N,2) # Present Value of Perpetuity Value (Present Value of Cash Flow in Year N)
    intrinsic_value = sum_DFCF + PVPV
    sharesLast = shares[shares.index.max()] # latest year the number of shares
    IVps = round(intrinsic_value/sharesLast,2)
    if(IVps > 0):
        return IVps
    else:
        return None


def netTradeCycle(s, ticker):
    try:
        bs = pd.read_sql(s.query(BalanceSheet).filter(BalanceSheet.period == "annual").statement, s.bind, index_col='symbol')
        ic = pd.read_sql(s.query(Income).filter(Income.period == "annual").statement, s.bind, index_col='symbol')
        bs.fillna(0, inplace=True)
        ic.fillna(0, inplace=True)
        netReceivables = bs.iloc[bs.index == ticker].sort_values(by='date')['netReceivables']
        inventory = bs.iloc[bs.index == ticker].sort_values(by='date')['inventory']
        accountsPayable = bs.iloc[bs.index == ticker].sort_values(by='date')['accountsPayable']
        totalRevenue = ic.iloc[ic.index == ticker].sort_values(by='date')['totalRevenue']
        costOfRevenue = ic.iloc[ic.index == ticker].sort_values(by='date')['costOfRevenue']
        if (all(totalRevenue != 0) and all(costOfRevenue != 0)):
            DSO = round(netReceivables/totalRevenue*360, 2)
            DIO = round(inventory/costOfRevenue*360, 2)
            DPO = round(accountsPayable/costOfRevenue*360, 2)
            NTC = DSO + DIO - DPO
            df = pd.concat([DSO, DIO, DPO, NTC], axis=1).reset_index()
            df.rename(index=str, columns={0: "DSO", 1: "DIO", 2: "DPO", 3: "N-T-C"}, inplace=True)
            df = df[['DSO', 'DIO', 'DPO', 'N-T-C']]
            df.index  = bs.iloc[bs.index == ticker]['date'].sort_values().tolist()
            df.index = df.index.strftime("%Y")
            return df
        else:
            return None
    except:
        return None


def yoy_financials(df):
    try:
        df = df[['revenue','netIncome','operatingIncome','grossMargin','operatingMargin',
                'freeCashFlow','earningsPerShare','bookValuePerShare']].fillna('-')
        df.index = df.index.strftime('%Y')
        df.sort_index(inplace=True)
        df = df.tail(6)
        df.columns = ['Revenue','Net-Income','Opt-Income','Gross-Margin','Opt-Margin','FCF','EPS','BVPS']
        return df.T
    except:
        df = df[['Revenue','NetIncome','OperatingIncome','GrossMargin','OperatingMargin',
                'FreeCashFlow','EarningsPerShare','BookValuePerShare']].fillna('-')
        df.index = df.index.strftime('%Y')
        df.sort_index(inplace=True)
        df = df.tail(6)
        df.columns = ['Revenue','Net-Income','Opt-Income','Gross-Margin','Opt-Margin','FCF','EPS','BVPS']
        return df.T



def get_Indinfo(ticker, s):
    try:
        df = pd.read_sql(s.query(Findex).filter(Findex.Symbol == ticker).statement, s.bind, index_col='Symbol')
        indcode = df.loc[ticker]['Indcode']
        ind_tick = pd.read_sql(s.query(Findex).filter(Findex.Indcode == indcode).statement, s.bind, index_col='Symbol').index.tolist()
        print('\n'+ 35*'-' + '\n' + 'Industry Info' + '\n'+ 35*'-' )
        # print('Company Name: %s' % df.loc[ticker]['Name'])
        print('Sector: %s' % df.loc[ticker]['Sector'])
        print('Industry: %s' % df.loc[ticker]['Industry'])
        print('Peers in industry: %s' % ', '.join(ind_tick))
    except Exception as e:
        print(e)
        pass
