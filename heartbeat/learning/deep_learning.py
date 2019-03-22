from ..models import Tdata
import pandas as pd

def learning_hub(s_dic):
    s_f = s_dic['financials']
    s_l = s_dic['learning']

    tdata = pd.read_sql(s_l.query(Tdata).statement, s_l.bind, index_col='id')
    classifyNB(tdata)





def classifyNB(df):
    pbuy = prob('buy', df)
    psell = prob('sell', df)
    phold = prob('hold', df)


    p_vp = cond_prob('volume_price', True, 'hold', df)
    p_yl = cond_prob('yr_low', True, 'hold', df)
    p = p_vp * p_yl *  phold

    print(p * 100)



def cond_prob(aname, avalue, bname, df):
    return len(df[ (df[aname] == avalue) & (df[bname] == True) ]) / len(df[df[bname] == True])


def prob(a, df):
    return len(df[df[a] == True])/len(df)
