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
