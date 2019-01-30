from __future__ import unicode_literals
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit import PromptSession
from prompt_toolkit.validation import Validator
from prompt_toolkit.completion import WordCompleter
from .utils.config import Config
from .utils.normalize import generate_tickerL
from .utils.fetch import fetch_index, fetch_findex
from .report.technical import technical_output
from .report.fundamental import fundamental_output
from .financials.update import update_financials
from .screener.screener import screening
from .db.db import Db
from .models import Income,BalanceSheet,Cashflow,Keystats,Findex
import sys

cmd_completer = WordCompleter(['exit'])

def is_number(text):
    return text.isdigit()

validator = Validator.from_callable(
    is_number,
    error_message='This input contains non-numeric characters',
    move_cursor_to_end=True)


def bottom_toolbar(mode):
    if(mode != None):
        return HTML(' <b><style bg="ansired">Heartbeat</style></b> > %s' % mode)
    else:
        return HTML(' Welcome to Project <b><style bg="ansired">Heartbeat</style></b>!')


def main(argv):
    mode = None
    while True:
        try:
            if(mode == None):
                dic = {1:'Technical Analysis', 2:'Fundamental Analysis', 3:'Update Financials', 4:'Screener', 0:'End Program'}
                print("Enter Module:\n" , '\n '.join('{} - {}'.format(key, value) for key, value in dic.items()))
                key = int(prompt('Your choice: ', validator=validator, bottom_toolbar=bottom_toolbar(mode) ))
                if(key not in list(dic.keys()) ):
                    print('Invalid option!')
                elif(key == 0):
                    sys.exit()
                else:
                    mode = dic[key]

            if(mode == 'Technical Analysis'):
                ticker = prompt('Enter ticker: ', bottom_toolbar=bottom_toolbar(mode), completer=cmd_completer).replace(" ", "")
                if(ticker == 'exit'):
                    mode = None
                if(ticker != '' and ticker != 'exit'):
                    technical_report(ticker)
            if(mode == 'Fundamental Analysis'):
                ticker = prompt('Enter ticker(.TO): ', bottom_toolbar=bottom_toolbar(mode), completer=cmd_completer).replace(" ", "")
                if(ticker == 'exit'):
                    mode = None
                elif(ticker != '' and ticker != 'exit'):
                    fundamental_report(ticker)
            if(mode == 'Update Financials'):
                financials()
                index = prompt('Enter index: ', bottom_toolbar=bottom_toolbar(mode), completer=cmd_completer).replace(" ", "")
                if(index == 'exit'):
                    mode = None
            if(mode == 'Screener'):
                screener()
                cmd = prompt('Command : ', bottom_toolbar=bottom_toolbar(mode), completer=cmd_completer).replace(" ", "")
                if(cmd == 'exit'):
                    mode = None
        except KeyboardInterrupt:
            continue
        except EOFError:
            break


def technical_report(ticker):
    db_name_list = ['nasdaq100','tsxci','sp100']
    s_dic = {}
    for name in db_name_list:
        Config.DB_NAME=name
        db_nasdaq = Db(Config)
        s = db_nasdaq.session()
        s_dic.update({name:s})
    Config.DB_NAME = 'financials'
    db = Db(Config)
    s = db.session()
    technical_output(s_dic, s, ticker) # .report.technical
    for name, s in s_dic.items():
        s.close()


def fundamental_report(ticker):
    Config.DB_NAME = 'financials'
    db = Db(Config)
    s = db.session()
    fundamental_output(s, ticker) # .report.fundamental
    s.close()


def financials():
    Config.DB_NAME = 'financials'
    db = Db(Config)
    s = db.session()
    db.create_all([Findex.__table__])
    db.create_all([Income.__table__])
    db.create_all([BalanceSheet.__table__])
    db.create_all([Cashflow.__table__])
    db.create_all([Keystats.__table__])
    update_financials(s)  # .financials.upate
    s.close()


def screener():
    Config.DB_NAME = 'financials'
    db = Db(Config)
    s = db.session()
    screening(s) # .screener.screener
    s.close()
