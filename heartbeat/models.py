# -*- coding: utf-8 -*-

from .db.db import Db as db


class Index(db.Model):
    __tablename__ = 'index'
    symbol = db.Column(db.String(6), unique=True, nullable=False, primary_key=True)
    company = db.Column(db.String(60),nullable=False)



class Quote(db.Model):
    __tablename__ = 'quote'
    id = db.Column(db.String(40), unique=True, nullable=False, primary_key=True)
    symbol = db.Column(db.String(6), db.ForeignKey("index.symbol"), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    open = db.Column(db.Float, nullable=True)
    high = db.Column(db.Float, nullable=True)
    low = db.Column(db.Float, nullable=True)
    close = db.Column(db.Float, nullable=True)
    adjusted = db.Column(db.Float, nullable=True)
    volume = db.Column(db.BIGINT, nullable=True)


class Report(db.Model):
    __tablename__ = 'report'
    id = db.Column(db.String(40), unique=True, nullable=False, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    symbol = db.Column(db.String(6), db.ForeignKey("index.symbol"), nullable=False)
    yr_high = db.Column(db.Boolean, nullable=True)
    yr_low = db.Column(db.Boolean, nullable=True)
    downtrend = db.Column(db.Boolean, nullable=True)
    uptrend = db.Column(db.Boolean, nullable=True)
    high_volume = db.Column(db.Boolean, nullable=True)
    # volume_price = db.Column(db.Boolean, nullable=True)
    rsi = db.Column(db.String(4), nullable=True)
    macd = db.Column(db.String(4), nullable=True)
    bolling = db.Column(db.String(10), nullable=True)


class Income(db.Model):
    __tablename__ = 'income'
    id = db.Column(db.String(40), unique=True, nullable=False, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    period = db.Column(db.String(9), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    researchDevelopment = db.Column(db.BIGINT, nullable=True)
    effectOfAccountingCharges = db.Column(db.BIGINT, nullable=True)
    incomeBeforeTax = db.Column(db.BIGINT, nullable=True)
    minorityInterest = db.Column(db.BIGINT, nullable=True)
    netIncome = db.Column(db.BIGINT, nullable=True)
    sellingGeneralAdministrative = db.Column(db.BIGINT, nullable=True)
    grossProfit = db.Column(db.BIGINT, nullable=True)
    ebit = db.Column(db.BIGINT, nullable=True)
    operatingIncome = db.Column(db.BIGINT, nullable=True)
    otherOperatingExpenses = db.Column(db.BIGINT, nullable=True)
    interestExpense = db.Column(db.BIGINT, nullable=True)
    extraordinaryItems = db.Column(db.BIGINT, nullable=True)
    nonRecurring = db.Column(db.BIGINT, nullable=True)
    otherItems = db.Column(db.BIGINT, nullable=True)
    incomeTaxExpense = db.Column(db.BIGINT, nullable=True)
    totalRevenue = db.Column(db.BIGINT, nullable=True)
    totalOperatingExpenses = db.Column(db.BIGINT, nullable=True)
    costOfRevenue = db.Column(db.BIGINT, nullable=True)
    discontinuedOperations = db.Column(db.BIGINT, nullable=True)
    totalOtherIncomeExpenseNet = db.Column(db.BIGINT, nullable=True)
    netIncomeFromContinuingOps = db.Column(db.BIGINT, nullable=True)
    netIncomeApplicableToCommonShares = db.Column(db.BIGINT, nullable=True)


class BalanceSheet(db.Model):
    __tablename__ = 'balancesheet'
    id = db.Column(db.String(40), unique=True, nullable=False, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    period = db.Column(db.String(9), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    capitalSurplus = db.Column(db.BIGINT, nullable=True)
    totalLiab = db.Column(db.BIGINT, nullable=True)
    totalStockholderEquity = db.Column(db.BIGINT, nullable=True)
    minorityInterest = db.Column(db.BIGINT, nullable=True)
    otherCurrentLiab = db.Column(db.BIGINT, nullable=True)
    totalAssets = db.Column(db.BIGINT, nullable=True)
    commonStock = db.Column(db.BIGINT, nullable=True)
    otherCurrentAssets = db.Column(db.BIGINT, nullable=True)
    retainedEarnings = db.Column(db.BIGINT, nullable=True)
    otherLiab = db.Column(db.BIGINT, nullable=True)
    otherAssets = db.Column(db.BIGINT, nullable=True)
    totalCurrentLiabilities = db.Column(db.BIGINT, nullable=True)
    shortLongTermDebt = db.Column(db.BIGINT, nullable=True)
    propertyPlantEquipment = db.Column(db.BIGINT, nullable=True)
    totalCurrentAssets = db.Column(db.BIGINT, nullable=True)
    netTangibleAssets = db.Column(db.BIGINT, nullable=True)
    netReceivables = db.Column(db.BIGINT, nullable=True)
    longTermDebt = db.Column(db.BIGINT, nullable=True)
    accountsPayable = db.Column(db.BIGINT, nullable=True)
    treasuryStock = db.Column(db.BIGINT, nullable=True)
    goodWill = db.Column(db.BIGINT, nullable=True)
    otherStockholderEquity = db.Column(db.BIGINT, nullable=True)
    intangibleAssets = db.Column(db.BIGINT, nullable=True)
    deferredLongTermAssetCharges = db.Column(db.BIGINT, nullable=True)
    deferredLongTermLiab = db.Column(db.BIGINT, nullable=True)
    cash = db.Column(db.BIGINT, nullable=True)
    inventory = db.Column(db.BIGINT, nullable=True)
    longTermInvestments = db.Column(db.BIGINT, nullable=True)
    shortTermInvestments = db.Column(db.BIGINT, nullable=True)


class Cashflow(db.Model):
    __tablename__ = 'cashflow'
    id = db.Column(db.String(40), unique=True, nullable=False, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    period = db.Column(db.String(9), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    changeToLiabilities = db.Column(db.BIGINT, nullable=True)
    totalCashflowsFromInvestingActivities = db.Column(db.BIGINT, nullable=True)
    netBorrowings = db.Column(db.BIGINT, nullable=True)
    totalCashFromFinancingActivities = db.Column(db.BIGINT, nullable=True)
    changeToOperatingActivities = db.Column(db.BIGINT, nullable=True)
    issuanceOfStock = db.Column(db.BIGINT, nullable=True)
    netIncome = db.Column(db.BIGINT, nullable=True)
    totalCashFromOperatingActivities = db.Column(db.BIGINT, nullable=True)
    depreciation = db.Column(db.BIGINT, nullable=True)
    otherCashflowsFromFinancingActivities = db.Column(db.BIGINT, nullable=True)
    changeToNetincome = db.Column(db.BIGINT, nullable=True)
    capitalExpenditures = db.Column(db.BIGINT, nullable=True)
    effectOfExchangeRate = db.Column(db.BIGINT, nullable=True)
    dividendsPaid = db.Column(db.BIGINT, nullable=True)
    otherCashflowsFromInvestingActivities = db.Column(db.BIGINT, nullable=True)
    investments = db.Column(db.BIGINT, nullable=True)
    changeToAccountReceivables = db.Column(db.BIGINT, nullable=True)
    changeInCash = db.Column(db.BIGINT, nullable=True)
    changeToInventory = db.Column(db.BIGINT, nullable=True)
    repurchaseOfStock = db.Column(db.BIGINT, nullable=True)


class Keystats(db.Model):
    __tablename__ = 'keystats'
    id = db.Column(db.String(40), unique=True, nullable=False, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    revenue = db.Column(db.Float, nullable=True)
    grossMargin = db.Column(db.Float, nullable=True)
    operatingIncome = db.Column(db.Float, nullable=True)
    operatingMargin = db.Column(db.Float, nullable=True)
    netIncome = db.Column(db.Float, nullable=True)
    earningsPerShare = db.Column(db.Float, nullable=True)
    dividends = db.Column(db.Float, nullable=True)
    payoutRatio = db.Column(db.Float, nullable=True)
    shares = db.Column(db.Float, nullable=True)
    bookValuePerShare = db.Column(db.Float, nullable=True)
    operatingCashFlow = db.Column(db.Float, nullable=True)
    capSpending = db.Column(db.Float, nullable=True)
    freeCashFlow = db.Column(db.Float, nullable=True)
    freeCashFlowPerShare = db.Column(db.Float, nullable=True)
    workingCapital = db.Column(db.Float, nullable=True)


class Findex(db.Model):
    # Financial Index wiht Sector and Industry Information
    __tablename__ = 'findex'
    Symbol = db.Column(db.String(10), unique=True, nullable=False, primary_key=True)
    Name = db.Column(db.String(60), nullable=False)
    Sector = db.Column(db.String(60), nullable=False)
    Industry = db.Column(db.String(60), nullable=False)
    Index = db.Column(db.String(20), nullable=False)
    Secode = db.Column(db.String(10), nullable=False)
    Indcode = db.Column(db.String(10), nullable=False)


class Tdata(db.Model):
    __tablename__ = 'tdata'
    id = db.Column(db.String(40), unique=True, nullable=False, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    yr_high = db.Column(db.Boolean, nullable=True)
    yr_low = db.Column(db.Boolean, nullable=True)
    downtrend = db.Column(db.Boolean, nullable=True)
    uptrend = db.Column(db.Boolean, nullable=True)
    high_volume = db.Column(db.Boolean, nullable=True)
    gap = db.Column(db.Boolean, nullable=True)
    # low_volume = db.Column(db.Boolean, nullable=True)
    # support = db.Column(db.Boolean, nullable=True)
    # pattern = db.Column(db.Boolean, nullable=True)
    rsi = db.Column(db.String(4), nullable=True)
    macd = db.Column(db.String(4), nullable=True)
    bolling = db.Column(db.String(10), nullable=True)
    # volume_price = db.Column(db.Boolean, nullable=True)
    buy = db.Column(db.Boolean, nullable=True)
    sell = db.Column(db.Boolean, nullable=True)
    hold = db.Column(db.Boolean, nullable=True)
    rating = db.Column(db.Float, nullable=True)
    # secode = db.Column(db.String(10), nullable=False)
    # indcode = db.Column(db.String(10), nullable=False)



class Shares_outstanding(db.Model):
    __tablename__ = 'shares_outstanding'
    symbol = db.Column(db.String(10), nullable=False, primary_key=True, unique=True)
    shares = db.Column(db.BIGINT, nullable=True)


class Gaps(db.Model):
    __tablename__ = 'gaps'
    id = db.Column(db.String(40), unique=True, nullable=False, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    index = db.Column(db.String(20), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    gap_high = db.Column(db.Float, nullable=True)
    gap_low = db.Column(db.Float, nullable=True)


class Rsi_predict(db.Model):
    __tablename__ = 'rsi_predict'
    id = db.Column(db.String(40), unique=True, nullable=False, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    index = db.Column(db.String(20), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    current_rsi = db.Column(db.Float, nullable=True)
    target_rsi = db.Column(db.Float, nullable=True)
    target_close = db.Column(db.Float, nullable=True)
    trend = db.Column(db.String(4), nullable=True)


class Rsi_predict_report(db.Model):
    __tablename__ = 'rsi_predict_report'
    id = db.Column(db.String(40), unique=True, nullable=False, primary_key=True)
    reached_date = db.Column(db.DateTime, nullable=False)
    predict_date = db.Column(db.DateTime, nullable=False)
    index = db.Column(db.String(20), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    high = db.Column(db.Float, nullable=True)
    low = db.Column(db.Float, nullable=True)
    current_rsi = db.Column(db.Float, nullable=True)
    target_rsi = db.Column(db.Float, nullable=True)
    target_close = db.Column(db.Float, nullable=True)
    trend = db.Column(db.String(4), nullable=True)
