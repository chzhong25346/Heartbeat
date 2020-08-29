import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from ..models import Index, Findex


def keep_latest(s):
    dbname = s.bind.url.database
    sp100_url = "https://en.wikipedia.org/wiki/S%26P_100"
    nasdaq100_url = "https://en.wikipedia.org/wiki/NASDAQ-100"
    tsxci_url = "https://en.wikipedia.org/wiki/S%26P/TSX_Composite_Index"
    if dbname == 'sp100':
        df = pd.read_html(sp100_url,header=0)[2].rename(columns={"Symbol": "symbol","Name":"company"})
    elif dbname == 'nasdaq100':
        df = pd.read_html(nasdaq100_url,header=0)[3].rename(columns={"Ticker": "symbol","Company":"company"})
    elif dbname == 'tsxci':
        df = pd.read_html(tsxci_url, header=0, keep_default_na=False)[1].rename(columns={"Symbol": "symbol","Company":"company"})
        df['symbol'] = df.replace({'symbol': r'\.'}, {'symbol': '-'}, regex=True)
    else:
        return None
    df1 = df[['symbol','company']]
    df2 = pd.read_sql(s.query(Index).statement, s.bind)
    # common = df.merge(df2,on=['symbol'])
    missing = df1.merge(df2.drop_duplicates(), on=['symbol'],
                   how='left', indicator=True)
    retired = df1.merge(df2.drop_duplicates(), on=['symbol'],
                   how='right', indicator=True)

    missing = missing[(missing['_merge']=='left_only')][['symbol','company_x']]
    retired = retired[(retired['_merge']=='right_only')]['symbol'].tolist()
    print('### Missing Symbols ### \n')
    print(missing)
    print('\n### Retired Symbols ###')
    print(','.join(retired))



def renew_findex(s_dic):
    df_csi300 = pd.read_sql(s_dic['csi300'].query(Index).statement, s_dic['csi300'].bind)

    df_sp100 = pd.read_sql(s_dic['sp100'].query(Index).statement, s_dic['sp100'].bind)
    df_sp100['symbol'].replace(regex={r'\.': '-'}, inplace=True)

    df_nasdaq100 = pd.read_sql(s_dic['nasdaq100'].query(Index).statement, s_dic['nasdaq100'].bind)
    df_nasdaq100['symbol'].replace(regex={r'\.': '-'}, inplace=True)

    df_tsxci = pd.read_sql(s_dic['tsxci'].query(Index).statement, s_dic['tsxci'].bind)
    df_tsxci['symbol'].replace(regex={r'\.': '-'}, inplace=True)
    df_tsxci['symbol'] = df_tsxci['symbol'] + ".TO"

    df_financials = pd.read_sql(s_dic['financials'].query(Findex).statement, s_dic['financials'].bind)

    df_all_index =  pd.concat([df_sp100, df_nasdaq100, df_tsxci, df_csi300])
    df_all_index.rename(columns={"symbol": "Symbol", "company": "Name"}, inplace=True)

    retired = df_all_index.merge(df_financials.drop_duplicates(), on=['Symbol'], how='right', indicator=True)
    retired = retired[(retired['_merge']=='right_only')]
    retired = retired[~retired['Index'].str.contains('SP500', regex=True)][['Symbol','Name_y','Index']].set_index('Symbol')

    missing = df_all_index.merge(df_financials.drop_duplicates(), on=['Symbol'], how='left', indicator=True)
    missing = missing[(missing['_merge']=='left_only')][['Symbol','Name_x']]
    missing = missing[~missing['Name_x'].str.contains('BetaPro|ISHARES|POWERSHARES|FTSE|BetaPro|HORIZONS|VANGUARD', regex=True)]
    missing.set_index('Symbol', inplace=True)
    ticker_L = missing.index.tolist()

    print('\nThe Following tickers to be retired: \n')
    print(retired)

    print('\n-----------------------------\nFetching profile for %s tickers...\n'% len(ticker_L))
    for ticker in ticker_L:
        prof = get_profile(ticker)
        if prof:
            print(' | '.join([ticker, missing.loc[ticker]['Name_x'], prof[0], prof[1]]))
        time.sleep(2)


def get_profile(ticker):
    try:
        url = 'https://finance.yahoo.com/quote/'+ticker+'/profile?p='+ticker
        html = requests.get(url).text
        soup = BeautifulSoup(html,'html.parser')
        mydiv = soup.body.find("div", {"class": "Mb(25px)"})
        sector = mydiv.find(text='Sector').parent.find_next_siblings("span", {"class": "Fw(600)"})[0].text
        industry = mydiv.find(text='Industry').parent.find_next_siblings("span", {"class": "Fw(600)"})[0].text
        return [sector, industry]
    except:
        print('Fetching %s failed!' % ticker)
