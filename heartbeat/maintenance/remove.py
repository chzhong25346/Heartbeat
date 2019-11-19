from ..models import Index, Quote, Report

def delete_ticker(s, ticker):
    before = s.query(Index).filter(Index.symbol == ticker).first()
    s.query(Quote).filter(Quote.symbol==ticker).delete()
    s.query(Report).filter(Report.symbol==ticker).delete()
    s.query(Index).filter(Index.symbol==ticker).delete()
    s.commit()
    after = s.query(Index).filter(Index.symbol == ticker).first()
    if (before and after == None):
        print('%s (%s) is removed!\n' % (ticker, before.company))
    elif before == None:
        print('%s not exist!\n' % ticker)
