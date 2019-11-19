import pandas as pd
from ..models import Index

def keep_latest(s):
    # before = s.query(Index).filter(Index.symbol == ticker).first()
    # s.query(Quote).filter(Quote.symbol==ticker).delete()
    # s.query(Report).filter(Report.symbol==ticker).delete()
    # s.query(Index).filter(Index.symbol==ticker).delete()
    # s.commit()
    # after = s.query(Index).filter(Index.symbol == ticker).first()
    # if (before and after == None):
    #     print('%s (%s) is removed!\n' % (ticker, before.company))
    # elif before == None:
    #     print('%s not exist!\n' % ticker)
    # print('keep latest...')
    #csi300_url = "https://zh.wikipedia.org/wiki/%E6%B2%AA%E6%B7%B1300"

    dbname = s.bind.url.database
    sp100_url = "https://en.wikipedia.org/wiki/S%26P_100"
    nasdaq100_url = "https://en.wikipedia.org/wiki/NASDAQ-100"
    tsxci_url = "https://en.wikipedia.org/wiki/S%26P/TSX_Composite_Index"
    if dbname == 'sp100':
        df = pd.read_html(sp100_url,header=0)[2].rename(columns={"Symbol": "symbol","Name":"company"})
    elif dbname == 'nasdaq100':
        df = pd.read_html(nasdaq100_url,header=0)[2].rename(columns={"Ticker": "symbol","Company":"company"})
    elif dbname == 'tsxci':
        df = pd.read_html(tsxci_url,header=0)[0].rename(columns={"Symbol": "symbol","Company":"company"})
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
