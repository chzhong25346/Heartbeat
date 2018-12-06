# import datetime as dt


def volume_price(df):
    # today = dt.datetime.today().strftime("%Y-%m-%d")
    ema21 = ema(df,21)
    ema5 = ema(df,5)
    df['ema_delta'] = round(((ema5/ema21)-1)*100,2)
    av90 = average_volume(df)
    df['volume_delta'] = round((df.volume/av90)-1,2)
    df = df[df['volume_delta']>=0.9]
    df = df[['ema_delta','volume_delta']]
    # print(today)
    # print(df.index[-1].strftime("%Y-%m-%d"))
    # print(today == df.index[-1].strftime("%Y-%m-%d"))
    return df


def today_price(df):
    df = df.iloc()[-1]
    return df


def fiftytwo_week(df):
    df = df.sort_index(ascending=True).last('52w')['close']
    # print(df.max())
    # print(df.min())
    return str(df.max()), str(df.min()),str(round((df.max()/df.min()-1)*100,2))+"%"


def ema(df, span):
    df = df.sort_index(ascending=True).last("18M")
    df = df['adjusted'].ewm(span=span, adjust=False).mean()
    return df


def average_volume(df):
    df = df.sort_index(ascending=True).last("18M")
    df = df['volume'].rolling(window=90).mean()
    return df
