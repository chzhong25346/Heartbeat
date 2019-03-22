from ..models import Tdata
import numpy as np
import pandas as pd

def learning_hub(s_dic):
    s_f = s_dic['financials']
    s_l = s_dic['learning']
    try:
        tdata = pd.read_sql(s_l.query(Tdata).statement, s_l.bind, index_col='id')
    except:
        print('\nUnable to read Training Data. Check DB!')
    print('\n' + 35*'-' + '\n' + 'Naive Bayes classifier' + "\n" + 35*'-')
    sig_L = ['volume_price', 'yr_low']
    pbuy, psell, phold = classifyNB(tdata,sig_L)
    print(', '.join(sig_L) + ": \nbuy: %s sell: %s hold: %s" % (pbuy, psell, phold))
    sig_L = ['downtrend']
    pbuy, psell, phold = classifyNB(tdata,sig_L)
    print('\n' + ', '.join(sig_L) + ": \nbuy: %s sell: %s hold: %s" % (pbuy, psell, phold))


def classifyNB(df, sig_L):
    condp_buyL = []
    condp_sellL = []
    condp_holdL = []
    for sig in sig_L:
        condp_buy = cond_prob(sig, True, 'buy', df)
        condp_sell = cond_prob(sig, True, 'sell', df)
        condp_hold = cond_prob(sig, True, 'hold', df)
        condp_buyL.append(condp_buy)
        condp_sellL.append(condp_sell)
        condp_holdL.append(condp_hold)
    pbuy = round(np.prod(condp_buyL) * prob('buy', df) * 100  ,3)
    psell = round(np.prod(condp_sellL) * prob('sell', df) * 100 ,3)
    phold = round(np.prod(condp_holdL) * prob('hold', df) * 100 ,3)
    return pbuy, psell, phold


def cond_prob(aname, avalue, bname, df):
    return len(df[ (df[aname] == avalue) & (df[bname] == True) ]) / len(df[df[bname] == True])


def prob(a, df):
    return len(df[df[a] == True])/len(df)
