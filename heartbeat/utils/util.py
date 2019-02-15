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


def model_dicL(model_list):
    list = []
    for model in model_list:
        list.append(model.__dict__)
    return list


def beautify_dict(dict):
    str = ''
    for key, value in dict.items():
        str += ("{} ({}), ".format(key, value))
    return str
