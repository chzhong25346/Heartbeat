def pick_stats(df, list, index_name):
    df = df[list]
    df.index=[index_name]
    df = df.T
    return df


def rename(df):
    df.columns = ['Market Cap (intraday)', 'Enterprise Value', 'Trailing P/E',
    'Forward P/E', 'PEG Ratio (5 yr expected)', 'Price/Sales (ttm)',
    'Price/Book (mrq)', 'Enterprise Value/Revenue',
    'Enterprise Value/EBITDA', 'Fiscal Year Ends',
    'Most Recent Quarter (mrq)', 'Profit Margin', 'Operating Margin (ttm)',
    'Return on Assets (ttm)', 'Return on Equity (ttm)', 'Revenue (ttm)',
    'Revenue Per Share (ttm)', 'Quarterly Revenue Growth (yoy)',
    'Gross Profit (ttm)', 'EBITDA', 'Net Income Avi to Common (ttm)',
    'Diluted EPS (ttm)', 'Quarterly Earnings Growth (yoy)',
    'Total Cash (mrq)', 'Total Cash Per Share (mrq)', 'Total Debt (mrq)',
    'Total Debt/Equity (mrq)', 'Current Ratio (mrq)',
    'Book Value Per Share (mrq)', 'Operating Cash Flow (ttm)',
    'Levered Free Cash Flow (ttm)', 'Beta (3Y Monthly)', '52-Week Change',
    'S&P500 52-Week Change', '52 Week High', '52 Week Low',
    '50-Day Moving Average', '200-Day Moving Average',
    'Avg Vol (3 month)', 'Avg Vol (10 day)', 'Shares Outstanding',
    'Float', '% Held by Insiders', '% Held by Institutions',
    'Shares Short (Nov 1, 2018)', 'Short Ratio (Nov 1, 2018)',
    'Short % of Float (Nov 1, 2018)',
    'Short % of Shares Outstanding (Nov 1, 2018)',
    'Shares Short (prior month Oct 1, 2018)',
    'Forward Annual Dividend Rate', 'Forward Annual Dividend Yield',
    'Trailing Annual Dividend Rate', 'Trailing Annual Dividend Yield',
    '5 Year Average Dividend Yield', 'Payout Ratio', 'Dividend Date',
    'Ex-Dividend Date', 'Last Split Factor (new per old)',
    'Last Split Date']
    return df
