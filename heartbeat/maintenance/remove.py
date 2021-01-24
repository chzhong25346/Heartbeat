from ..models import Index, Quote, Report, Findex

def delete_ticker(dbname, s_dic, ticker):
    s = s_dic[dbname]
    sf = s_dic['financials']
    before = s.query(Index).filter(Index.symbol == ticker).first()
    s.query(Quote).filter(Quote.symbol==ticker).delete()
    s.query(Report).filter(Report.symbol==ticker).delete()
    s.query(Index).filter(Index.symbol==ticker).delete()
    s.commit()
    if dbname in ('tsxci', 'TSXCI'):
        sf.query(Findex).filter(Findex.Symbol==ticker+'.TO').filter(Findex.Index==dbname).delete()
    else:
        sf.query(Findex).filter(Findex.Symbol==ticker).filter(Findex.Index==dbname).delete()
    sf.commit()
    after = s.query(Index).filter(Index.symbol == ticker).first()
    if (before and after == None):
        print('%s (%s) is removed!\n' % (ticker, before.company))
    elif before == None:
        print('%s not exist!\n' % ticker)
