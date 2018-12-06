from __future__ import unicode_literals
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit import PromptSession
from prompt_toolkit.validation import Validator
from prompt_toolkit.completion import WordCompleter
from .utils.config import Config
from .report.technical import technical_output
from .report.fundamental import fundamental_output
from .db.db import Db

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
                dic = {1:'Technical Analysis', 2:'Fundamental Analysis'}
                print("Analysis Mode:\n" , '\n '.join('{} - {}'.format(key, value) for key, value in dic.items()))
                key = int(prompt('Your choice: ', validator=validator, bottom_toolbar=bottom_toolbar(mode) ))
                if(key != 0):
                    mode = dic[key]
            if(mode == 'Technical Analysis'):
                ticker = prompt('Enter ticker: ', bottom_toolbar=bottom_toolbar(mode), completer=cmd_completer)
                if(ticker == 'exit'):
                    mode = None
                if(ticker != '' and ticker != 'exit'):
                    technical_report(ticker)
            if(mode == 'Fundamental Analysis'):
                ticker = prompt('Enter ticker: ', bottom_toolbar=bottom_toolbar(mode), completer=cmd_completer)
                if(ticker == 'exit'):
                    mode = None
                elif(ticker != '' and ticker != 'exit'):
                    Fundamental_report(ticker)
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
    technical_output(s_dic, ticker)
    for name, s in s_dic.items():
        s.close()


def Fundamental_report(ticker):
    db_name_list = ['nasdaq100','tsxci','sp100']
    s_dic = {}
    for name in db_name_list:
        Config.DB_NAME = name
        db = Db(Config)
        s = db.session()
        s_dic.update({name:s})
    fundamental_output(s_dic, ticker)
    for name, s in s_dic.items():
        s.close()
