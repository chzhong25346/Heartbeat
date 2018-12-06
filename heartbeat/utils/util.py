import hashlib


def gen_id(string):
    return int(hashlib.md5(str.encode(string)).hexdigest(), 16)


def normalize_Todash(data):
    data['symbol'] = data['symbol'].str.replace(".","-")
    return data


def groupby_na_to_zero(df, ticker):
    df = df.groupby(ticker).first()
    df.fillna(0, inplace=True)
    return df
