import pandas as pd
from ..utils.util import groupby_na_to_zero
from ..utils.locate_db import locate_session
from ..utils.fetch import get_keyStats
from ..db.read import read_ticker
from ..models import Index, Quote
from .volume_price import volume_price,today_price,fiftytwo_week
from .fundamental import intrinsic_value


def technical_output(s_dic, s_fin, ticker):
    output = ''
    try:
        s, db_name, ticker, company_name = locate_session(s_dic, ticker)
        df = get_quote(s, ticker)
        today = today_price(df)
        ft_max, ft_min, ft_delta = fiftytwo_week(df)
        df_pv = volume_price(df)
        print(35*'-' + '\n' + ticker + ' - ' + company_name + "\n" + 35*'-')
        ticker = ticker.upper()
        if(db_name == 'tsxci'):
            ticker = ticker+'.TO'
        try:
            ks = get_keyStats(ticker)
            IVps = intrinsic_value(ks)
            print('IVps: ' + str(IVps))
        except:
            pass
        print('close: ' + str(today.close) + ', open: ' + str(today.open) + '\n'
              + 'high: ' + str(today.high) + ', low: ' + str(today.low) + '\n' + 35*'-')
        print("52-week high: " + ft_max
                + "\n52-week low: " + ft_min
                + "\n52-week change: " + ft_delta + "\n" + 35*'-')
        print(df_pv)
    except Exception as e:
        print("Unable to search! Try again.")


def get_quote(s, ticker):
    '''
    get quote by ticker from sesssion and sort and drop 0
    '''
    df = pd.read_sql(s.query(Quote).filter(Quote.symbol == ticker).statement, s.bind, index_col='date')
    # sort by old to new
    df.sort_index(inplace=True)
    # drop rows have 0
    df = df[(df != 0).all(1)]
    return df
