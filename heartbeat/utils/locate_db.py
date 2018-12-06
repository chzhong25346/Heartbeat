import pandas as pd
from ..models import Index, Quote, Report

def locate_session(s_dic, ticker):
    '''
    locate which session in session list contains ticker.
    output text symbol and company name
    '''
    for name, s in s_dic.items():
        df = pd.read_sql(s.query(Index).filter(Index.symbol == ticker).statement, s.bind)
        if not df.empty:
            return s, name, df.symbol[0], df.company[0]
