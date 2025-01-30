from __future__ import unicode_literals
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit import PromptSession
from prompt_toolkit.validation import Validator
from prompt_toolkit.completion import WordCompleter
from .utils.config import Config
from .utils.normalize import generate_tickerL
from .utils.fetch import fetch_index, fetch_findex
from .utils.util import is_db, close_alldb
from .report.technical import technical_output
from .report.fundamental import fundamental_output
from .financials.update import update_financials
from .screener.screener import screen_full
from .screener.screener_bycode import screen_bycode
from .learning.training_data import collect_tdata
from .learning.find5yLow import find5yLow
from .learning.findWeeklyCross import findWeeklyCross
from .learning.deep_learning import learning_hub
from .maintenance.remove import delete_ticker
from .maintenance.keep_latest import keep_latest, renew_findex, ticker_counter
from .db.db import Db
from .models import Income,BalanceSheet,Cashflow,Keystats,Findex,Tdata,Shares_outstanding
import sys

cmd_completer = WordCompleter(['exit'])

def is_number(text):
    return text.isdigit()

validator = Validator.from_callable(
    is_number,
    error_message='This input contains non-numeric characters',
    move_cursor_to_end=True)


def bottom_toolbar(mode, submode=None):
    if(submode != None):
        return HTML(' <b><style bg="ansired">Heartbeat</style></b> > %s > %s' % (mode, submode))
    elif(mode != None):
        return HTML(' <b><style bg="ansired">Heartbeat</style></b> > %s' % mode)
    else:
        return HTML(' Welcome to Project <b><style bg="ansired">Heartbeat</style></b>!')


def main(argv):
    mode = None
    submode = None
    while True:
        try:
            if(mode == None):
                dic = {1:'Technical Analysis', 2:'Fundamental Analysis', 3:'Update Financials', 4:'Screener', 5:'Learning',  6:'Maintenance', 0:'End Program'}
                print('\n', 9*'-',"Modules", 9*'-', '\n', '\n '.join('{} - {}'.format(key, value) for key, value in dic.items()), '\n',27 *'-')
                key = int(prompt('Your choice: ', validator=validator, bottom_toolbar=bottom_toolbar(mode) ))
                if(key not in list(dic.keys()) ):
                    print('Invalid option!')
                elif(key == 0):
                    sys.exit()
                else:
                    mode = dic[key]
            if(mode == 'Technical Analysis'): #### Option 1
                ticker = prompt('Enter ticker: ', bottom_toolbar=bottom_toolbar(mode), completer=cmd_completer).replace(" ", "")
                if(ticker == 'exit'):
                    mode = None
                if(ticker != '' and ticker != 'exit'):
                    reporting_technical(ticker)
            if(mode == 'Fundamental Analysis'): #### Option 2
                ticker = prompt('Enter ticker(.TO): ', bottom_toolbar=bottom_toolbar(mode), completer=cmd_completer).replace(" ", "")
                if(ticker == 'exit'):
                    mode = None
                elif(ticker != '' and ticker != 'exit'):
                    reporting_fundamental(ticker)
            if(mode == 'Update Financials'): #### Option 3
                updating_financials()
                mode = None
            if(mode == 'Screener'): #### Option 4
                if(submode == None):
                    code = ''
                    dic = {1:'Full', 2:'By Sector', 3:'By Industry', 0:'Return'}
                    print('\n', 5*'-',"Screening Mode", 5*'-', '\n', '\n '.join('{} - {}'.format(key, value) for key, value in dic.items()), '\n',25*'-')
                    key = int(prompt('Your choice: ', validator=validator, bottom_toolbar=bottom_toolbar(mode, submode)))
                    if(key not in list(dic.keys()) ):
                        print('Invalid option!')
                    else:
                        submode = dic[key]
                    if(submode == 'Full'):  #### Option 4-1
                        screening_full()
                        submode = None
                    elif(submode == 'By Sector'): #### Option 4-2
                        while True:
                            code = prompt('Sector code: ', bottom_toolbar=bottom_toolbar(mode, submode), completer=cmd_completer).replace(" ", "")
                            if (code == 'exit'):
                                submode = None
                                break
                            else:
                                screening_bycode(code, 'Secode')
                    elif(submode == 'By Industry'): #### Option 4-3
                        while True:
                            code = prompt('Industry code: ', bottom_toolbar=bottom_toolbar(mode, submode), completer=cmd_completer).replace(" ", "")
                            if (code == 'exit'):
                                submode = None
                                break
                            else:
                                screening_bycode(code, 'Indcode')
                    elif(submode == 'Return'): #### Option 4-0
                        submode = None
                        mode = None
            if(mode == 'Learning'): #### Option 5
                if(submode == None):
                    code = ''
                    dic = {1:'Renew data', 2:'Learning', 3:'Find 5-Year Low', 4:'Find Weekly Cross', 0:'Return'}
                    print('\n', 5*'-',"Learning Mode", 5*'-', '\n', '\n '.join('{} - {}'.format(key, value) for key, value in dic.items()), '\n',25*'-')
                    key = int(prompt('Your choice: ', validator=validator, bottom_toolbar=bottom_toolbar(mode, submode)))
                    if(key not in list(dic.keys()) ):
                        print('Invalid option!')
                    else:
                        submode = dic[key]
                    if(submode == 'Renew data'):  #### Option 5-1
                        renew_tdata()
                        submode = None
                    elif(submode == 'Learning'): #### Option 5-2
                        machine_learning()
                        submode = None
                    elif(submode == 'Find 5-Year Low'): #### Option 5-3
                        FiveYearLow()
                        submode = None
                    elif(submode == 'Find Weekly Cross'): #### Option 5-4
                        WeeklyCross()
                        submode = None
                    elif(submode == 'Return'): #### Option 5-0
                        submode = None
                        mode = None
            if(mode == 'Maintenance'): #### Option 6
                if(submode == None):
                    code = ''
                    dic = {1:'Remove Ticker',2:'Keep Latest', 3:'Update Findex', 4:'Ticker Summary', 0:'Return'}
                    print('\n', 5*'-',"Maintenance Mode", 5*'-', '\n', '\n '.join('{} - {}'.format(key, value) for key, value in dic.items()), '\n',25*'-')
                    key = int(prompt('Your choice: ', validator=validator, bottom_toolbar=bottom_toolbar(mode, submode)))
                    if(key not in list(dic.keys()) ):
                        print('Invalid option!')
                    else:
                        submode = dic[key]
                    if(submode == 'Remove Ticker'):  #### Option 6-1
                        while True:
                            dbname = prompt('Database name: ', bottom_toolbar=bottom_toolbar(mode, submode), completer=cmd_completer).replace(" ", "")
                            db_exist = is_db(dbname)
                            if db_exist and dbname != 'exit':
                                ticker = prompt('Ticker(' + dbname +'): ', bottom_toolbar=bottom_toolbar(mode, submode), completer=cmd_completer).replace(" ", "")
                                if ticker and ticker != 'exit':
                                    purge_ticker(dbname, ticker)
                                elif ticker == 'exit':
                                    submode = None
                                    break
                            elif dbname == 'exit':
                                submode = None
                                break
                    elif(submode == 'Keep Latest'):  #### Option 6-2
                        while True:
                            dbname = prompt('Database name: ', bottom_toolbar=bottom_toolbar(mode, submode), completer=cmd_completer).replace(" ", "")
                            db_exist = is_db(dbname)
                            if db_exist and dbname != 'exit':
                                keep_udpate(dbname)
                            elif dbname == 'exit':
                                submode = None
                                break
                    elif(submode == 'Update Findex'):  #### Option 6-3
                        udpate_findex()
                        submode = None
                    elif(submode == 'Ticker Summary'):  #### Option 6-3
                        total_ticker()
                        submode = None
                    elif(submode == 'Return'): #### Option 6-0
                        submode = None
                        mode = None
        except KeyboardInterrupt:
            continue
        except EOFError:
            break


def reporting_technical(ticker):
    db_name_list = ['nasdaq100','tsxci','sp100']
    s_dic = {}
    for name in db_name_list:
        Config.DB_NAME = name
        s = Db(Config).session()
        s_dic.update({name:s})
    Config.DB_NAME = 'financials'
    db = Db(Config)
    s = db.session()
    technical_output(s_dic, s, ticker) # .report.technical
    for name, s in s_dic.items():
        s.close()


def reporting_fundamental(ticker):
    Config.DB_NAME = 'financials'
    db = Db(Config)
    s = db.session()
    fundamental_output(s, ticker) # .report.fundamental
    s.close()


def updating_financials():
    db_name_list = ['eei','financials',]
    s_dic = {}
    for name in db_name_list:
        Config.DB_NAME = name
        db = Db(Config)
        s = db.session()
        s_dic.update({name:s})
        if ('financials' in s_dic):
            db.create_all([Findex.__table__])
            db.create_all([Income.__table__])
            db.create_all([BalanceSheet.__table__])
            db.create_all([Cashflow.__table__])
            db.create_all([Keystats.__table__])
            db.create_all([Shares_outstanding.__table__])
    update_financials(s_dic)  # .financials.upate
    close_alldb(s_dic)


def screening_full():
    Config.DB_NAME = 'financials'
    db = Db(Config)
    s = db.session()
    screen_full(s) # .screener.screen_full
    s.close()


def screening_bycode(code, type):
    Config.DB_NAME = 'financials'
    db = Db(Config)
    s = db.session()
    screen_bycode(s, code, type) # .screener_bycode.screen_bycode
    s.close()


def renew_tdata():
    db_name_list = ['nasdaq100','tsxci','sp100','financials','learning','testing']
    s_dic = {}
    for name in db_name_list:
        Config.DB_NAME = name
        db = Db(Config)
        s = db.session()
        s_dic.update({name:s})
        if ('learning' in s_dic):
            db.create_all([Tdata.__table__])
    collect_tdata(s_dic) # .learning.update
    close_alldb(s_dic)


def machine_learning():
    db_name_list = ['learning','financials']
    s_dic = {}
    for name in db_name_list:
        Config.DB_NAME = name
        db = Db(Config)
        s = db.session()
        s_dic.update({name:s})
    learning_hub(s_dic) # .learning.deep_learning
    close_alldb(s_dic)


def FiveYearLow():
    db_name_list = ['nasdaq100','tsxci','sp100','eei']
    s_dic = {}
    for name in db_name_list:
        Config.DB_NAME = name
        db = Db(Config)
        s = db.session()
        s_dic.update({name:s})
    find5yLow(s_dic)
    close_alldb(s_dic)


def WeeklyCross():
    db_name_list = ['nasdaq100','tsxci','sp100','eei']
    s_dic = {}
    for name in db_name_list:
        Config.DB_NAME = name
        db = Db(Config)
        s = db.session()
        s_dic.update({name:s})
    findWeeklyCross(s_dic)
    close_alldb(s_dic)


def purge_ticker(dbname, ticker):
    db_name_list = [dbname, 'financials', 'learning']
    s_dic = {}
    for name in db_name_list:
        Config.DB_NAME = name
        db = Db(Config)
        s = db.session()
        s_dic.update({name:s})
    delete_ticker(dbname, s_dic, ticker.upper())
    close_alldb(s_dic)


def keep_udpate(dbname):
    Config.DB_NAME = dbname
    db = Db(Config)
    s = db.session()
    keep_latest(s)
    s.close()


def udpate_findex():
    db_name_list = ['nasdaq100','tsxci','sp100','csi300','financials']
    s_dic = {}
    for name in db_name_list:
        Config.DB_NAME = name
        db = Db(Config)
        s = db.session()
        s_dic.update({name:s})
    renew_findex(s_dic)
    close_alldb(s_dic)


def total_ticker():
    db_name_list = ['nasdaq100','tsxci','sp100','eei']
    s_dic = {}
    for name in db_name_list:
        Config.DB_NAME = name
        db = Db(Config)
        s = db.session()
        s_dic.update({name:s})
    ticker_counter(s_dic)
    close_alldb(s_dic)
