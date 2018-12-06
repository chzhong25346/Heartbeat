# -*- coding: utf-8 -*-

from .db.db import Db as db


class Index(db.Model):
    __tablename__ = 'index'
    symbol = db.Column(db.String(6), unique=True, nullable=False, primary_key=True)
    company = db.Column(db.String(60),nullable=False)
    # sector = db.Column(db.String(80),nullable=False)
    # industry = db.Column(db.String(60),nullable=False)
    quote = db.relationship('Quote', backref='quote', lazy=True)
    report = db.relationship('Report', backref='report', lazy=True)


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
    low_volume = db.Column(db.Boolean, nullable=True)
    support = db.Column(db.Boolean, nullable=True)
    pattern = db.Column(db.String(20), nullable=True)


class Holding(db.Model):
    __tablename__ = 'holding'
    symbol = db.Column(db.String(6), db.ForeignKey("index.symbol"), primary_key=True, nullable=False)
    avg_cost = db.Column(db.Float, nullable=True)
    book_value = db.Column(db.Float, nullable=True)
    change_dollar = db.Column(db.Float, nullable=True)
    change_percent = db.Column(db.Float, nullable=True)
    mkt_price = db.Column(db.Float, nullable=True)
    mkt_value = db.Column(db.Float, nullable=True)
    quantity = db.Column(db.BIGINT, nullable=True)
    note = db.Column(db.String(20), nullable=True)


class Transaction(db.Model):
    __tablename__ = 'transaction'
    id = db.Column(db.String(40), unique=True, nullable=False, primary_key=True)
    symbol = db.Column(db.String(6), db.ForeignKey("index.symbol"), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    price = db.Column(db.Float, nullable=True)
    quantity = db.Column(db.BIGINT, nullable=True)
    settlement = db.Column(db.Float, nullable=True)
    type = db.Column(db.String(6), nullable=False)
