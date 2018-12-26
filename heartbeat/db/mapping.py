import pandas as pd
import datetime as dt
from datetime import datetime
from ..utils.fetch import fetch_index, get_daily_adjusted
from ..utils.util import gen_id
from ..models import Income,BalanceSheet,Cashflow
import re


def map_income(df):
    df_records = df.to_dict('r')
    model_instnaces = [Income(
        id = gen_id(r['symbol']+r['period']+str(r['endDate'])),
        symbol = r['symbol'],
        period = r['period'],
        date = datetime.fromtimestamp(r['endDate']).strftime("%Y-%m-%d"),
        researchDevelopment = r['researchDevelopment'],
        effectOfAccountingCharges = r['effectOfAccountingCharges'],
        incomeBeforeTax = r['incomeBeforeTax'],
        minorityInterest = r['minorityInterest'],
        netIncome = r['netIncome'],
        sellingGeneralAdministrative = r['sellingGeneralAdministrative'],
        grossProfit = r['grossProfit'],
        ebit = r['ebit'],
        operatingIncome = r['operatingIncome'],
        otherOperatingExpenses = r['otherOperatingExpenses'],
        interestExpense = r['interestExpense'],
        extraordinaryItems = r['extraordinaryItems'],
        nonRecurring = r['nonRecurring'],
        otherItems = r['otherItems'],
        incomeTaxExpense = r['incomeTaxExpense'],
        totalRevenue = r['totalRevenue'],
        totalOperatingExpenses = r['totalOperatingExpenses'],
        costOfRevenue = r['costOfRevenue'],
        totalOtherIncomeExpenseNet = r['totalOtherIncomeExpenseNet'],
        discontinuedOperations = r['discontinuedOperations'],
        netIncomeFromContinuingOps = r['netIncomeFromContinuingOps'],
        netIncomeApplicableToCommonShares = r['netIncomeApplicableToCommonShares'],
    ) for r in df_records]
    return model_instnaces


def map_balancesheet(df):
    df_records = df.to_dict('r')
    model_instnaces = [BalanceSheet(
        id = gen_id(r['symbol']+r['period']+str(r['endDate'])),
        symbol = r['symbol'],
        period = r['period'],
        date = datetime.fromtimestamp(r['endDate']).strftime("%Y-%m-%d"),
        capitalSurplus = r['capitalSurplus'],
        totalLiab = r['totalLiab'],
        totalStockholderEquity = r['totalStockholderEquity'],
        minorityInterest = r['minorityInterest'],
        otherCurrentLiab = r['otherCurrentLiab'],
        totalAssets = r['totalAssets'],
        commonStock = r['commonStock'],
        otherCurrentAssets = r['otherCurrentAssets'],
        retainedEarnings = r['retainedEarnings'],
        otherLiab = r['otherLiab'],
        otherAssets = r['otherAssets'],
        totalCurrentLiabilities = r['totalCurrentLiabilities'],
        shortLongTermDebt = r['shortLongTermDebt'],
        propertyPlantEquipment = r['propertyPlantEquipment'],
        totalCurrentAssets = r['totalCurrentAssets'],
        netTangibleAssets = r['netTangibleAssets'],
        netReceivables = r['netReceivables'],
        longTermDebt = r['longTermDebt'],
        accountsPayable = r['accountsPayable'],
		treasuryStock = r['treasuryStock'],
		goodWill = r['goodWill'],
		otherStockholderEquity = r['otherStockholderEquity'],
		intangibleAssets = r['intangibleAssets'],
		deferredLongTermAssetCharges = r['deferredLongTermAssetCharges'],
		deferredLongTermLiab = r['deferredLongTermLiab'],
		cash = r['cash'],
		inventory = r['inventory'],
		longTermInvestments = r['longTermInvestments'],
		shortTermInvestments = r['shortTermInvestments'],
    ) for r in df_records]
    return model_instnaces


def map_cashflow(df):
    df_records = df.to_dict('r')
    model_instnaces = [Cashflow(
        id = gen_id(r['symbol']+r['period']+str(r['endDate'])),
        symbol = r['symbol'],
        period = r['period'],
        date = datetime.fromtimestamp(r['endDate']).strftime("%Y-%m-%d"),
        totalCashFromFinancingActivities = r['totalCashFromFinancingActivities'],
		netBorrowings = r['netBorrowings'],
		changeToOperatingActivities = r['changeToOperatingActivities'],
		depreciation = r['depreciation'],
		issuanceOfStock = r['issuanceOfStock'],
		changeToLiabilities = r['changeToLiabilities'],
		capitalExpenditures = r['capitalExpenditures'],
		effectOfExchangeRate = r['effectOfExchangeRate'],
		dividendsPaid = r['dividendsPaid'],
		totalCashFromOperatingActivities = r['totalCashFromOperatingActivities'],
		changeToNetincome = r['changeToNetincome'],
		otherCashflowsFromInvestingActivities = r['otherCashflowsFromInvestingActivities'],
		investments = r['investments'],
		changeToAccountReceivables = r['changeToAccountReceivables'],
		changeInCash = r['changeInCash'],
		otherCashflowsFromFinancingActivities = r['otherCashflowsFromFinancingActivities'],
		netIncome = r['netIncome'],
		totalCashflowsFromInvestingActivities = r['totalCashflowsFromInvestingActivities'],
		changeToInventory = r['changeToInventory'],
		repurchaseOfStock = r['repurchaseOfStock'],
    ) for r in df_records]
    return model_instnaces
