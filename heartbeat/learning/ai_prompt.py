from ..models import Index,  Quote, Quote_CSI300
import pandas as pd
import numpy as np
import json


def get_AI_Prompt(
    sdic,
    dbname,
    ticker
):
    """
    Load daily OHLCV data, convert it to weekly data,
    calculate weekly trend indicators, and return a
    structured JSON-compatible dictionary.

    Parameters
    ----------
    sdic : dict
        Dictionary containing SQLAlchemy sessions.

    dbname : str
        Database name, such as:
            csi300
            tsxci
            sp100
            nasdaq100
            eei

    ticker : str
        Stock ticker.

    Returns
    -------
    dict
        Weekly trend, support/resistance, chase-value,
        and buy-low-value analysis.
    """

    # --------------------------------------------------
    # 1. Validate database/session
    # --------------------------------------------------

    if dbname not in sdic:
        raise ValueError(
            f"Database session '{dbname}' "
            f"was not found in sdic."
        )

    session = sdic[dbname]

    # --------------------------------------------------
    # 2. Normalize ticker for the selected database
    # --------------------------------------------------

    # TSX database may store symbols without ".TO".
    query_ticker = (
        ticker.replace(".TO", "")
        if dbname == "tsxci"
        else ticker
    )

    # --------------------------------------------------
    # 3. Build SQL query
    # --------------------------------------------------

    if dbname == "csi300":
        query = (
            session.query(Quote_CSI300)
            .filter(
                Quote_CSI300.symbol
                == query_ticker
            )
        )

    else:
        query = (
            session.query(Quote)
            .filter(
                Quote.symbol
                == query_ticker
            )
        )

    # --------------------------------------------------
    # 4. Load daily data
    # --------------------------------------------------

    df_daily = pd.read_sql(
        query.statement,
        session.bind,
        index_col="date"
    )

    if df_daily is None or df_daily.empty:
        raise ValueError(
            f"No daily data found for "
            f"{ticker} in database '{dbname}'."
        )

    # --------------------------------------------------
    # 5. Clean daily dataframe
    # --------------------------------------------------

    df_daily = df_daily.copy()

    if not isinstance(
        df_daily.index,
        pd.DatetimeIndex
    ):
        df_daily.index = pd.to_datetime(
            df_daily.index,
            errors="coerce"
        )

    # Remove invalid datetime indexes.
    df_daily = df_daily[
        ~df_daily.index.isna()
    ]

    df_daily = df_daily.sort_index()

    df_daily.columns = [
        str(column).lower()
        for column in df_daily.columns
    ]

    required_daily_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]

    missing_daily_columns = [
        column
        for column in required_daily_columns
        if column not in df_daily.columns
    ]

    if missing_daily_columns:
        raise ValueError(
            f"Daily dataframe for {ticker} "
            f"is missing columns: "
            f"{missing_daily_columns}"
        )

    # Convert required columns to numeric.
    for column in required_daily_columns:
        df_daily[column] = pd.to_numeric(
            df_daily[column],
            errors="coerce"
        )

    df_daily = df_daily.dropna(
        subset=[
            "open",
            "high",
            "low",
            "close"
        ]
    )

    if df_daily.empty:
        raise ValueError(
            f"No valid OHLC data remains for "
            f"{ticker} after cleaning."
        )

    # --------------------------------------------------
    # 6. Convert daily data to weekly data
    # --------------------------------------------------

    df_weekly = to_weekly_df(
        df_daily
    )

    if df_weekly is None or df_weekly.empty:
        raise ValueError(
            f"No weekly data could be generated "
            f"for {ticker} in database '{dbname}'."
        )

    df_weekly = df_weekly.sort_index()

    # --------------------------------------------------
    # 7. Separate an incomplete current week
    # --------------------------------------------------
    # Formal weekly calculations use completed candles only. The partial
    # current week remains visible as a preview but cannot create temporary
    # candle, volume, MACD, support/resistance, or entry signals.
    latest_daily_date = pd.Timestamp(df_daily.index[-1]).normalize()
    latest_week_start = pd.Timestamp(df_weekly.index[-1]).normalize()
    latest_week_end = latest_week_start + pd.Timedelta(days=4)
    has_incomplete_week = bool(latest_daily_date < latest_week_end)

    incomplete_week_preview = None
    if has_incomplete_week:
        incomplete_week_preview = build_weekly_k(df_weekly=df_weekly)
        incomplete_week_preview["status"] = "PREVIEW_ONLY"
        incomplete_week_preview["official_score_usage"] = "EXCLUDED_FROM_FORMAL_ANALYSIS"
        df_analysis = df_weekly.iloc[:-1].copy()
    else:
        df_analysis = df_weekly.copy()

    if df_analysis.empty:
        raise ValueError("No completed weekly candle is available for formal analysis.")

    official_week_start = pd.Timestamp(df_analysis.index[-1]).normalize()
    official_week_end = official_week_start + pd.Timedelta(days=4)
    df_daily_analysis = df_daily[
        df_daily.index.normalize() <= official_week_end
    ].copy()

    # --------------------------------------------------
    # 8. Ensure enough completed weekly history
    # --------------------------------------------------

    # EMA50 needs at least 50 weeks.
    # MACD(14,56,5) benefits from more history.
    minimum_weekly_rows = 61

    if len(df_analysis) < minimum_weekly_rows:
        raise ValueError(
            f"At least {minimum_weekly_rows} "
            f"weekly candles are required for "
            f"EMA50 and MACD(14,56,5). "
            f"Only {len(df_analysis)} completed weeks "
            f"are available for {ticker}."
        )

    # --------------------------------------------------
    # 8. Build the latest weekly candle
    # --------------------------------------------------

    weekly_k = build_weekly_k(
        df_weekly=df_analysis
    )

    # --------------------------------------------------
    # 9. Build moving averages
    # --------------------------------------------------

    moving_averages = (
        build_moving_averages(
            df_weekly=df_analysis,
            flat_threshold_pct=0.05
        )
    )

    # --------------------------------------------------
    # 10. Build weekly MACD(14,56,5)
    # --------------------------------------------------

    macd = build_macd(
        df_weekly=df_analysis,
        fast_period=14,
        slow_period=56,
        signal_period=5,
        history_weeks=8,
        histogram_multiplier=1,
        flat_threshold=0.0001
    )

    # --------------------------------------------------
    # 11. Build weekly volume analysis
    # --------------------------------------------------

    volume_analysis = (
        build_volume_analysis(
            df_weekly=df_analysis,
            high_volume_threshold=1.20,
            history_weeks=8
        )
    )

    # --------------------------------------------------
    # 12. Build daily-gap analysis
    # --------------------------------------------------

    # Gap analysis must use original daily data.
    # Weekly resampling can hide daily gaps.
    gap = build_gap_analysis(
        df_daily=df_daily_analysis,
        current_price=float(
            df_analysis["close"].iloc[-1]
        ),
        lookback_days=252,
        minimum_gap_pct=0.30
    )

    # --------------------------------------------------
    # 13. Build short-term weekly structure
    # --------------------------------------------------

    short_term_structure = (
        build_short_term_structure(
            df_weekly=df_analysis,
            atr_period=14
        )
    )

    # --------------------------------------------------
    # 14. Build support/resistance candidates
    # --------------------------------------------------

    support_resistance = (
        build_support_resistance_candidates(
            weekly_k=weekly_k,
            moving_averages=moving_averages,
            gap=gap,
            short_term_structure=(
                short_term_structure
            ),
            atr=short_term_structure.get(
                "atr14"
            )
        )
    )

    # --------------------------------------------------
    # 15. Evaluate short-term chase value
    # --------------------------------------------------

    chase_analysis = (
        build_chase_analysis(
            weekly_k=weekly_k,
            moving_averages=moving_averages,
            macd=macd,
            volume_analysis=volume_analysis,
            gap=gap,
            short_term_structure=(
                short_term_structure
            ),
            support_resistance=(
                support_resistance
            )
        )
    )

    # --------------------------------------------------
    # 16. Evaluate short-term buy-low value
    # --------------------------------------------------

    buy_low_analysis = (
        build_buy_low_analysis(
            weekly_k=weekly_k,
            moving_averages=moving_averages,
            macd=macd,
            volume_analysis=volume_analysis,
            gap=gap,
            short_term_structure=(
                short_term_structure
            ),
            support_resistance=(
                support_resistance
            )
        )
    )

    # --------------------------------------------------
    # 17. Select preferred entry style
    # --------------------------------------------------

    preferred_entry_style = (
        choose_preferred_entry_style(
            chase_analysis=chase_analysis,
            buy_low_analysis=(
                buy_low_analysis
            )
        )
    )

    # --------------------------------------------------
    # 18. Build final JSON-compatible result
    # --------------------------------------------------

    result = {
        "symbol": ticker,
        "query_symbol": query_ticker,
        "database": dbname,

        "data_summary": {
            "daily_rows": int(
                len(df_daily)
            ),
            "weekly_rows": int(
                len(df_weekly)
            ),
            "completed_weekly_rows": int(
                len(df_analysis)
            ),
            "daily_start_date": (
                pd.Timestamp(
                    df_daily.index[0]
                ).strftime("%Y-%m-%d")
            ),
            "daily_end_date": (
                pd.Timestamp(
                    df_daily.index[-1]
                ).strftime("%Y-%m-%d")
            ),
            "weekly_start_date": (
                pd.Timestamp(
                    df_weekly.index[0]
                ).strftime("%Y-%m-%d")
            ),
            "weekly_end_date": (
                pd.Timestamp(
                    df_weekly.index[-1]
                ).strftime("%Y-%m-%d")
            ),
            "official_analysis_week_start": official_week_start.strftime("%Y-%m-%d"),
            "official_analysis_week_end": official_week_end.strftime("%Y-%m-%d"),
            "timeframe": "WEEKLY"
        },

        "analysis_status": (
            "LAST_COMPLETED_WEEK" if has_incomplete_week else "COMPLETED_WEEK"
        ),
        "score_usage": "FORMAL_COMPLETED_WEEK_ONLY",
        "recommended_action": (
            "REVIEW_COMPLETED_WEEK_SIGNAL; CURRENT_WEEK_IS_PREVIEW_ONLY"
            if has_incomplete_week
            else "USE_COMPLETED_WEEK_SIGNAL"
        ),
        "incomplete_week_preview": incomplete_week_preview,
        "weekly_k": weekly_k,

        "moving_averages":
            moving_averages,

        "macd": macd,

        "volume_analysis":
            volume_analysis,

        "gap": gap,

        "short_term_structure":
            short_term_structure,

        "support_resistance":
            support_resistance,

        "short_term_entry_analysis": {
            "chase": chase_analysis,

            "buy_low":
                buy_low_analysis,

            "preferred_entry_style":
                preferred_entry_style
        }
    }

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
            default=str

        )
    )


    return result

############################# Methods

def build_weekly_k(df_weekly):
    """
    Build the latest weekly candlestick summary.

    Required columns:
        open, high, low, close, volume
    """

    required_columns = ["open", "high", "low", "close", "volume"]

    missing_columns = [
        column
        for column in required_columns
        if column not in df_weekly.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Weekly dataframe is missing columns: {missing_columns}"
        )

    clean_df = (
        df_weekly
        .dropna(subset=["open", "high", "low", "close"])
        .sort_index()
    )

    if len(clean_df) < 2:
        raise ValueError(
            "At least two weekly candles are required."
        )

    current = clean_df.iloc[-1]
    previous = clean_df.iloc[-2]

    week_start = pd.Timestamp(clean_df.index[-1])
    week_end = week_start + pd.Timedelta(days=4)

    open_price = float(current["open"])
    high_price = float(current["high"])
    low_price = float(current["low"])
    close_price = float(current["close"])
    previous_close = float(previous["close"])

    volume = (
        int(current["volume"])
        if pd.notna(current["volume"])
        else None
    )

    weekly_change = close_price - previous_close

    weekly_change_pct = (
        weekly_change / previous_close * 100
        if previous_close != 0
        else None
    )

    price_range = high_price - low_price
    candle_body = abs(close_price - open_price)

    upper_shadow = max(
        0.0,
        high_price - max(open_price, close_price)
    )

    lower_shadow = max(
        0.0,
        min(open_price, close_price) - low_price
    )

    if price_range > 0:
        body_pct = candle_body / price_range * 100
        upper_shadow_pct = upper_shadow / price_range * 100
        lower_shadow_pct = lower_shadow / price_range * 100

        close_location = (
            close_price - low_price
        ) / price_range
    else:
        body_pct = 0.0
        upper_shadow_pct = 0.0
        lower_shadow_pct = 0.0
        close_location = 0.5

    if close_price > open_price:
        candle_type = "BULLISH"
    elif close_price < open_price:
        candle_type = "BEARISH"
    else:
        candle_type = "DOJI"

    if close_price > previous_close:
        weekly_direction = "UP"
    elif close_price < previous_close:
        weekly_direction = "DOWN"
    else:
        weekly_direction = "UNCHANGED"

    today = pd.Timestamp.now().normalize()

    # The weekly candle is considered complete after Friday.
    is_completed_week = today >= week_end.normalize()

    return {
        "week_start": week_start.strftime("%Y-%m-%d"),
        "week_end": week_end.strftime("%Y-%m-%d"),
        "is_completed_week": bool(is_completed_week),

        "open": round(open_price, 3),
        "high": round(high_price, 3),
        "low": round(low_price, 3),
        "close": round(close_price, 3),
        "previous_close": round(previous_close, 3),
        "volume": volume,

        "weekly_change": round(weekly_change, 3),

        "weekly_change_pct": (
            round(weekly_change_pct, 3)
            if weekly_change_pct is not None
            else None
        ),

        "candle_type": candle_type,
        "weekly_direction": weekly_direction,

        "price_range": round(price_range, 3),
        "body": round(candle_body, 3),
        "upper_shadow": round(upper_shadow, 3),
        "lower_shadow": round(lower_shadow, 3),

        "body_pct": round(body_pct, 3),
        "upper_shadow_pct": round(upper_shadow_pct, 3),
        "lower_shadow_pct": round(lower_shadow_pct, 3),

        # 0 means close at weekly low.
        # 1 means close at weekly high.
        "close_location": round(close_location, 3)
    }


def to_weekly_df(df):
    if df is None or df.empty:
        return df

    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    df = df.sort_index()
    df.columns = [column.lower() for column in df.columns]

    agg_map = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }

    if "adjusted" in df.columns:
        agg_map["adjusted"] = "last"

    df_weekly = (
        df.resample(
            "W-FRI",
            label="right",
            closed="right"
        )
        .agg(agg_map)
        .dropna(subset=["open", "high", "low", "close"])
    )

    if "symbol" in df.columns and not df["symbol"].dropna().empty:
        symbol = df["symbol"].dropna().iloc[-1]
        df_weekly.insert(0, "symbol", symbol)

    # Change weekly index from Friday to Monday
    df_weekly.index = (
        df_weekly.index - pd.Timedelta(days=4)
    )

    df_weekly.index.name = "week_start"

    return df_weekly

def build_moving_averages(
    df_weekly,
    flat_threshold_pct=0.05
):
    """
    Calculate weekly MA5, MA10, MA20 and EMA50.

    Parameters
    ----------
    df_weekly : pandas.DataFrame
        Weekly OHLCV dataframe.

    flat_threshold_pct : float
        If the absolute 1-week slope is smaller than this percentage,
        classify the moving average direction as FLAT.

        Example:
            0.05 means changes between -0.05% and +0.05%
            are classified as FLAT.

    Returns
    -------
    dict
        Moving average values, slopes, directions and price distances.
    """

    if df_weekly is None or df_weekly.empty:
        raise ValueError("Weekly dataframe is empty.")

    if "close" not in df_weekly.columns:
        raise ValueError(
            "Weekly dataframe is missing the close column."
        )

    clean_df = (
        df_weekly
        .dropna(subset=["close"])
        .sort_index()
        .copy()
    )

    # EMA50 can technically be calculated with fewer than 50 rows,
    # but at least 50 completed weekly candles gives a more stable value.
    if len(clean_df) < 50:
        raise ValueError(
            "At least 50 weekly candles are required "
            "to calculate EMA50 reliably."
        )

    close = clean_df["close"].astype(float)

    # Simple moving averages
    ma5_series = close.rolling(
        window=5,
        min_periods=5
    ).mean()

    ma10_series = close.rolling(
        window=10,
        min_periods=10
    ).mean()

    ma20_series = close.rolling(
        window=20,
        min_periods=20
    ).mean()

    # Exponential moving average
    ema50_series = close.ewm(
        span=50,
        adjust=False,
        min_periods=50
    ).mean()

    moving_average_series = {
        "ma5": ma5_series,
        "ma10": ma10_series,
        "ma20": ma20_series,
        "ema50": ema50_series
    }

    latest_close = float(close.iloc[-1])

    result = {}

    for name, series in moving_average_series.items():
        current_value = series.iloc[-1]
        previous_value = series.iloc[-2]

        if pd.isna(current_value) or pd.isna(previous_value):
            raise ValueError(
                f"Unable to calculate current or previous {name}."
            )

        current_value = float(current_value)
        previous_value = float(previous_value)

        if previous_value != 0:
            slope_pct_1w = (
                current_value / previous_value - 1
            ) * 100
        else:
            slope_pct_1w = None

        direction = get_ma_direction(
            slope_pct=slope_pct_1w,
            flat_threshold_pct=flat_threshold_pct
        )

        if current_value != 0:
            price_distance_pct = (
                latest_close / current_value - 1
            ) * 100
        else:
            price_distance_pct = None

        result[name] = round(current_value, 3)

        result[f"{name}_slope_pct_1w"] = (
            round(slope_pct_1w, 3)
            if slope_pct_1w is not None
            else None
        )

        result[f"{name}_direction"] = direction

        result[f"price_distance_{name}_pct"] = (
            round(price_distance_pct, 3)
            if price_distance_pct is not None
            else None
        )

    result["alignment"] = get_ma_alignment(
        close=latest_close,
        ma5=result["ma5"],
        ma10=result["ma10"],
        ma20=result["ma20"],
        ema50=result["ema50"]
    )

    return result


def get_ma_direction(
    slope_pct,
    flat_threshold_pct=0.05
):
    """
    Convert the moving-average slope into UP, FLAT or DOWN.
    """

    if slope_pct is None or pd.isna(slope_pct):
        return "UNKNOWN"

    if slope_pct > flat_threshold_pct:
        return "UP"

    if slope_pct < -flat_threshold_pct:
        return "DOWN"

    return "FLAT"


def get_ma_alignment(
    close,
    ma5,
    ma10,
    ma20,
    ema50
):
    """
    Identify the current weekly moving-average alignment.
    """

    values = {
        "PRICE": close,
        "MA5": ma5,
        "MA10": ma10,
        "MA20": ma20,
        "EMA50": ema50
    }

    sorted_items = sorted(
        values.items(),
        key=lambda item: item[1],
        reverse=True
    )

    return " > ".join(
        name for name, value in sorted_items
    )


def build_macd(
        df_weekly,
        fast_period=14,
        slow_period=56,
        signal_period=5,
        history_weeks=8,
        histogram_multiplier=1,
        flat_threshold=0.0001
):
    """
    Calculate MACD(14, 56, 5) from weekly closing prices.

    DIF = EMA14 - EMA56
    DEA = EMA5 of DIF
    Histogram = (DIF - DEA) * histogram_multiplier
    """

    if df_weekly is None or df_weekly.empty:
        raise ValueError("Weekly dataframe is empty.")

    if "close" not in df_weekly.columns:
        raise ValueError(
            "Weekly dataframe is missing the close column."
        )

    clean_df = (
        df_weekly
        .dropna(subset=["close"])
        .sort_index()
        .copy()
    )

    minimum_weeks = slow_period + signal_period

    if len(clean_df) < minimum_weeks:
        raise ValueError(
            f"At least {minimum_weeks} weekly candles are required "
            f"for MACD({fast_period},{slow_period},{signal_period}). "
            f"Only {len(clean_df)} weeks are available."
        )

    close = pd.to_numeric(
        clean_df["close"],
        errors="coerce"
    )

    ema_fast = close.ewm(
        span=fast_period,
        adjust=False
    ).mean()

    ema_slow = close.ewm(
        span=slow_period,
        adjust=False
    ).mean()

    dif = ema_fast - ema_slow

    dea = dif.ewm(
        span=signal_period,
        adjust=False
    ).mean()

    histogram = (
                        dif - dea
                ) * histogram_multiplier

    macd_df = pd.DataFrame(
        {
            "dif": dif,
            "dea": dea,
            "histogram": histogram
        },
        index=clean_df.index
    ).dropna()

    if len(macd_df) < 2:
        raise ValueError(
            "At least two valid weekly MACD records are required."
        )

    current = macd_df.iloc[-1]
    previous = macd_df.iloc[-2]

    current_dif = float(current["dif"])
    current_dea = float(current["dea"])
    current_histogram = float(current["histogram"])

    previous_dif = float(previous["dif"])
    previous_dea = float(previous["dea"])
    previous_histogram = float(previous["histogram"])

    history = []

    for week_date, row in macd_df.tail(history_weeks).iterrows():
        history.append(
            {
                "week_start": pd.Timestamp(
                    week_date
                ).strftime("%Y-%m-%d"),

                "dif": round(
                    float(row["dif"]),
                    4
                ),

                "dea": round(
                    float(row["dea"]),
                    4
                ),

                "histogram": round(
                    float(row["histogram"]),
                    4
                )
            }
        )

    return {
        "parameters": {
            "fast_period": fast_period,
            "slow_period": slow_period,
            "signal_period": signal_period,
            "histogram_multiplier": histogram_multiplier,
            "timeframe": "WEEKLY",
            "source": "calculated_from_weekly_close"
        },

        "dif": round(current_dif, 4),
        "dea": round(current_dea, 4),
        "histogram": round(current_histogram, 4),

        "previous_dif": round(previous_dif, 4),
        "previous_dea": round(previous_dea, 4),
        "previous_histogram": round(
            previous_histogram,
            4
        ),

        "dif_direction": get_indicator_direction(
            current_value=current_dif,
            previous_value=previous_dif,
            flat_threshold=flat_threshold
        ),

        "dea_direction": get_indicator_direction(
            current_value=current_dea,
            previous_value=previous_dea,
            flat_threshold=flat_threshold
        ),

        "histogram_direction": get_indicator_direction(
            current_value=current_histogram,
            previous_value=previous_histogram,
            flat_threshold=flat_threshold
        ),

        "dif_above_dea": bool(
            current_dif > current_dea
        ),

        "dif_above_zero": bool(
            current_dif > 0
        ),

        "dea_above_zero": bool(
            current_dea > 0
        ),

        "crossover": get_macd_crossover(
            current_dif=current_dif,
            current_dea=current_dea,
            previous_dif=previous_dif,
            previous_dea=previous_dea
        ),

        "state": get_macd_state(
            current_histogram=current_histogram,
            previous_histogram=previous_histogram,
            flat_threshold=flat_threshold
        ),

        "weeks_since_bullish_cross": get_weeks_since_cross(
            macd_df=macd_df,
            cross_type="BULLISH"
        ),

        "weeks_since_bearish_cross": get_weeks_since_cross(
            macd_df=macd_df,
            cross_type="BEARISH"
        ),

        "positive_histogram_weeks":
            count_consecutive_histogram_weeks(
                histogram_series=macd_df["histogram"],
                positive=True
            ),

        "negative_histogram_weeks":
            count_consecutive_histogram_weeks(
                histogram_series=macd_df["histogram"],
                positive=False
            ),

        "history_last_weeks": history
    }


def get_indicator_direction(
    current_value,
    previous_value,
    flat_threshold=0.0001
):
    change = current_value - previous_value

    if change > flat_threshold:
        return "UP"

    if change < -flat_threshold:
        return "DOWN"

    return "FLAT"


def get_macd_state(
    current_histogram,
    previous_histogram,
    flat_threshold=0.0001
):
    change = current_histogram - previous_histogram

    if previous_histogram <= 0 < current_histogram:
        return "ZERO_LINE_CROSS_UP"

    if previous_histogram >= 0 > current_histogram:
        return "ZERO_LINE_CROSS_DOWN"

    if abs(change) <= flat_threshold:
        return "FLAT"

    if current_histogram > 0:
        if current_histogram > previous_histogram:
            return "POSITIVE_EXPANDING"

        return "POSITIVE_NARROWING"

    if current_histogram < 0:
        if current_histogram > previous_histogram:
            return "NEGATIVE_NARROWING"

        return "NEGATIVE_EXPANDING"

    return "FLAT"


def get_macd_crossover(
    current_dif,
    current_dea,
    previous_dif,
    previous_dea
):
    previous_difference = previous_dif - previous_dea
    current_difference = current_dif - current_dea

    if previous_difference <= 0 < current_difference:
        return "BULLISH_CROSS"

    if previous_difference >= 0 > current_difference:
        return "BEARISH_CROSS"

    if current_difference > 0:
        return "BULLISH_NO_NEW_CROSS"

    if current_difference < 0:
        return "BEARISH_NO_NEW_CROSS"

    return "DIF_EQUALS_DEA"


def get_weeks_since_cross(macd_df, cross_type):
    difference = macd_df["dif"] - macd_df["dea"]

    if cross_type == "BULLISH":
        cross_mask = (
            (difference > 0)
            & (difference.shift(1) <= 0)
        )

    elif cross_type == "BEARISH":
        cross_mask = (
            (difference < 0)
            & (difference.shift(1) >= 0)
        )

    else:
        raise ValueError(
            "cross_type must be BULLISH or BEARISH."
        )

    positions = np.flatnonzero(
        cross_mask.fillna(False).to_numpy()
    )

    if len(positions) == 0:
        return None

    return int(
        len(macd_df) - 1 - positions[-1]
    )


def count_consecutive_histogram_weeks(
    histogram_series,
    positive=True
):
    count = 0

    for value in reversed(
        histogram_series.dropna().tolist()
    ):
        if positive and value > 0:
            count += 1
        elif not positive and value < 0:
            count += 1
        else:
            break

    return count


def build_volume_analysis(
    df_weekly,
    high_volume_threshold=1.20,
    history_weeks=8
):
    """
    Analyze weekly trading volume.

    Volume averages exclude the current week, so the current
    week's volume does not increase its own comparison baseline.

    Parameters
    ----------
    df_weekly : pandas.DataFrame
        Weekly OHLCV dataframe.

    high_volume_threshold : float
        Current volume must be at least this multiple of its
        previous 13-week average to count as high volume.

        Example:
            1.20 = at least 20% above average.

    history_weeks : int
        Number of recent weeks included in the output.

    Returns
    -------
    dict
        Weekly volume averages, ratios, direction and interpretation.
    """

    required_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df_weekly.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Weekly dataframe is missing volume-analysis columns: "
            f"{missing_columns}"
        )

    clean_df = (
        df_weekly[required_columns]
        .copy()
        .sort_index()
    )

    for column in required_columns:
        clean_df[column] = pd.to_numeric(
            clean_df[column],
            errors="coerce"
        )

    clean_df = clean_df.dropna(
        subset=["open", "high", "low", "close", "volume"]
    )

    if len(clean_df) < 41:
        raise ValueError(
            "At least 41 weekly candles are required to calculate "
            "the previous 40-week average volume."
        )

    volume = clean_df["volume"].astype(float)

    # shift(1) excludes the current week's volume
    volume_avg_4w = (
        volume.shift(1)
        .rolling(window=4, min_periods=4)
        .mean()
    )

    volume_avg_13w = (
        volume.shift(1)
        .rolling(window=13, min_periods=13)
        .mean()
    )

    volume_avg_20w = (
        volume.shift(1)
        .rolling(window=20, min_periods=20)
        .mean()
    )

    volume_avg_40w = (
        volume.shift(1)
        .rolling(window=40, min_periods=40)
        .mean()
    )

    analysis_df = clean_df.copy()

    analysis_df["volume_avg_4w"] = volume_avg_4w
    analysis_df["volume_avg_13w"] = volume_avg_13w
    analysis_df["volume_avg_20w"] = volume_avg_20w
    analysis_df["volume_avg_40w"] = volume_avg_40w

    analysis_df["volume_ratio_13w"] = (
        analysis_df["volume"]
        / analysis_df["volume_avg_13w"]
    )

    analysis_df["volume_ratio_20w"] = (
        analysis_df["volume"]
        / analysis_df["volume_avg_20w"]
    )

    analysis_df["weekly_change_pct"] = (
        analysis_df["close"]
        / analysis_df["close"].shift(1)
        - 1
    ) * 100

    price_range = (
        analysis_df["high"]
        - analysis_df["low"]
    )

    analysis_df["close_location"] = np.where(
        price_range > 0,
        (
            analysis_df["close"]
            - analysis_df["low"]
        ) / price_range,
        0.5
    )

    valid_df = analysis_df.dropna(
        subset=[
            "volume_avg_13w",
            "volume_avg_20w",
            "volume_avg_40w",
            "volume_ratio_13w"
        ]
    )

    if len(valid_df) < 2:
        raise ValueError(
            "Insufficient valid weekly volume-analysis records."
        )

    current = valid_df.iloc[-1]
    previous = valid_df.iloc[-2]

    current_volume = float(current["volume"])
    previous_volume = float(previous["volume"])

    avg_4w = float(current["volume_avg_4w"])
    avg_13w = float(current["volume_avg_13w"])
    avg_20w = float(current["volume_avg_20w"])
    avg_40w = float(current["volume_avg_40w"])

    ratio_13w = float(current["volume_ratio_13w"])
    ratio_20w = float(current["volume_ratio_20w"])

    weekly_change_pct = float(
        current["weekly_change_pct"]
    )

    close_location = float(
        current["close_location"]
    )

    volume_change_pct = (
        (current_volume / previous_volume - 1) * 100
        if previous_volume != 0
        else None
    )

    volume_direction = get_volume_direction(
        current_volume=current_volume,
        previous_volume=previous_volume
    )

    volume_level = get_volume_level(
        volume_ratio=ratio_13w
    )

    price_volume_state = get_price_volume_state(
        weekly_change_pct=weekly_change_pct,
        volume_ratio=ratio_13w,
        close_location=close_location
    )

    consecutive_high_volume_weeks = (
        count_consecutive_high_volume_weeks(
            analysis_df=analysis_df,
            threshold=high_volume_threshold
        )
    )

    consecutive_volume_increase_weeks = (
        count_consecutive_volume_increase_weeks(
            volume_series=valid_df["volume"]
        )
    )

    history = []

    for week_date, row in valid_df.tail(history_weeks).iterrows():
        history.append(
            {
                "week_start": pd.Timestamp(
                    week_date
                ).strftime("%Y-%m-%d"),

                "volume": int(row["volume"]),

                "volume_avg_13w": round(
                    float(row["volume_avg_13w"]),
                    0
                ),

                "volume_ratio_13w": round(
                    float(row["volume_ratio_13w"]),
                    3
                ),

                "weekly_change_pct": round(
                    float(row["weekly_change_pct"]),
                    3
                ),

                "close_location": round(
                    float(row["close_location"]),
                    3
                )
            }
        )

    return {
        "current_volume": int(current_volume),
        "previous_week_volume": int(previous_volume),

        "volume_avg_4w": round(avg_4w, 0),
        "volume_avg_13w": round(avg_13w, 0),
        "volume_avg_20w": round(avg_20w, 0),
        "volume_avg_40w": round(avg_40w, 0),

        "volume_ratio_13w": round(ratio_13w, 3),
        "volume_ratio_20w": round(ratio_20w, 3),

        "volume_change_pct_1w": (
            round(volume_change_pct, 3)
            if volume_change_pct is not None
            else None
        ),

        "volume_direction": volume_direction,
        "volume_level": volume_level,

        "high_volume_threshold": high_volume_threshold,

        "is_high_volume": bool(
            ratio_13w >= high_volume_threshold
        ),

        "consecutive_high_volume_weeks":
            consecutive_high_volume_weeks,

        "consecutive_volume_increase_weeks":
            consecutive_volume_increase_weeks,

        "price_volume_state": price_volume_state,

        "history_last_weeks": history
    }


def get_volume_direction(
    current_volume,
    previous_volume,
    flat_threshold_pct=5.0
):
    """
    Compare current volume with previous week's volume.
    """

    if previous_volume <= 0:
        return "UNKNOWN"

    change_pct = (
        current_volume / previous_volume - 1
    ) * 100

    if change_pct > flat_threshold_pct:
        return "UP"

    if change_pct < -flat_threshold_pct:
        return "DOWN"

    return "FLAT"


def get_volume_level(volume_ratio):
    """
    Classify current volume relative to the previous
    13-week average volume.
    """

    if volume_ratio < 0.80:
        return "LOW"

    if volume_ratio < 1.20:
        return "NORMAL"

    if volume_ratio < 1.50:
        return "MODERATELY_HIGH"

    if volume_ratio < 2.00:
        return "HIGH"

    return "EXTREMELY_HIGH"


def get_price_volume_state(
    weekly_change_pct,
    volume_ratio,
    close_location
):
    """
    Classify the relationship between weekly price action
    and weekly trading volume.
    """

    high_volume = volume_ratio >= 1.20
    strong_volume = volume_ratio >= 1.50

    if weekly_change_pct > 0:
        if volume_ratio < 0.80:
            return "PRICE_UP_LOW_VOLUME"
        if strong_volume and close_location >= 0.70:
            return "BULLISH_HIGH_VOLUME_CLOSE"

        if high_volume and close_location < 0.40:
            return "HIGH_VOLUME_UPPER_REJECTION"

        if high_volume:
            return "BULLISH_VOLUME_EXPANSION"

        return "PRICE_UP_NORMAL_VOLUME"

    if weekly_change_pct < 0:
        if volume_ratio < 0.80:
            return "PRICE_DOWN_LOW_VOLUME"
        if strong_volume and close_location <= 0.30:
            return "BEARISH_HIGH_VOLUME_SELLING"

        if high_volume and close_location >= 0.60:
            return "HIGH_VOLUME_BUYING_SUPPORT"

        if high_volume:
            return "BEARISH_VOLUME_EXPANSION"

        return "PRICE_DOWN_NORMAL_VOLUME"

    if high_volume:
        return "HIGH_VOLUME_NO_PRICE_PROGRESS"

    return "NEUTRAL_VOLUME"


def count_consecutive_high_volume_weeks(
    analysis_df,
    threshold=1.20
):
    """
    Count consecutive weeks where volume was at least
    threshold times the previous 13-week average.
    """

    valid_ratios = (
        analysis_df["volume_ratio_13w"]
        .dropna()
        .tolist()
    )

    count = 0

    for ratio in reversed(valid_ratios):
        if ratio >= threshold:
            count += 1
        else:
            break

    return count


def count_consecutive_volume_increase_weeks(
    volume_series
):
    """
    Count how many consecutive weeks volume increased
    compared with the previous week.
    """

    values = (
        volume_series
        .dropna()
        .astype(float)
        .tolist()
    )

    if len(values) < 2:
        return 0

    count = 0

    for position in range(
        len(values) - 1,
        0,
        -1
    ):
        if values[position] > values[position - 1]:
            count += 1
        else:
            break

    return count


def build_gap_analysis(
    df_daily,
    current_price=None,
    lookback_days=252,
    minimum_gap_pct=0.30
):
    """
    Detect the nearest unfilled daily price gap for weekly trading.

    Up gap:
        current low > previous high

        gap_low  = previous high
        gap_high = current low

    Down gap:
        current high < previous low

        gap_low  = current high
        gap_high = previous low

    Parameters
    ----------
    df_daily : pandas.DataFrame
        Original daily OHLCV dataframe.

    current_price : float or None
        Latest weekly or daily closing price.

    lookback_days : int
        Number of recent trading days to inspect.

    minimum_gap_pct : float
        Minimum gap size as a percentage of the previous close.
        Smaller gaps are treated as market noise.

        Example:
            0.30 means the gap must be at least 0.30%.

    Returns
    -------
    dict
        Details of the nearest unfilled gap.
    """

    required_columns = [
        "high",
        "low",
        "close"
    ]

    if df_daily is None or df_daily.empty:
        return empty_gap_result()

    clean_df = df_daily.copy()

    clean_df.columns = [
        str(column).lower()
        for column in clean_df.columns
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in clean_df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Daily dataframe is missing gap-analysis columns: "
            f"{missing_columns}"
        )

    if not isinstance(clean_df.index, pd.DatetimeIndex):
        clean_df.index = pd.to_datetime(
            clean_df.index,
            errors="coerce"
        )

    clean_df = (
        clean_df
        .sort_index()
        .tail(lookback_days)
        .copy()
    )

    for column in required_columns:
        clean_df[column] = pd.to_numeric(
            clean_df[column],
            errors="coerce"
        )

    clean_df = clean_df.dropna(
        subset=required_columns
    )

    if len(clean_df) < 2:
        return empty_gap_result()

    if current_price is None:
        current_price = float(
            clean_df["close"].iloc[-1]
        )
    else:
        current_price = float(current_price)

    gaps = []

    for position in range(1, len(clean_df)):
        previous_row = clean_df.iloc[position - 1]
        current_row = clean_df.iloc[position]

        previous_high = float(
            previous_row["high"]
        )

        previous_low = float(
            previous_row["low"]
        )

        previous_close = float(
            previous_row["close"]
        )

        current_high = float(
            current_row["high"]
        )

        current_low = float(
            current_row["low"]
        )

        gap_date = pd.Timestamp(
            clean_df.index[position]
        )

        if previous_close == 0:
            continue

        gap_type = None
        gap_low = None
        gap_high = None

        # Upward gap
        if current_low > previous_high:
            gap_type = "GAP_UP"
            gap_low = previous_high
            gap_high = current_low

        # Downward gap
        elif current_high < previous_low:
            gap_type = "GAP_DOWN"
            gap_low = current_high
            gap_high = previous_low

        if gap_type is None:
            continue

        gap_size = gap_high - gap_low

        gap_size_pct = (
            gap_size / previous_close
        ) * 100

        if gap_size_pct < minimum_gap_pct:
            continue

        fill_result = evaluate_gap_fill(
            clean_df=clean_df,
            gap_position=position,
            gap_type=gap_type,
            gap_low=gap_low,
            gap_high=gap_high
        )

        age_in_trading_days = (
            len(clean_df) - 1 - position
        )

        weeks_ago = int(
            age_in_trading_days // 5
        )

        if current_price < gap_low:
            location = "ABOVE_PRICE"
            distance_to_gap_pct = (
                gap_low / current_price - 1
            ) * 100

        elif current_price > gap_high:
            location = "BELOW_PRICE"
            distance_to_gap_pct = (
                current_price / gap_high - 1
            ) * 100

        else:
            location = "PRICE_INSIDE_GAP"
            distance_to_gap_pct = 0.0

        gaps.append(
            {
                "gap_date": gap_date,
                "gap_type": gap_type,
                "gap_low": gap_low,
                "gap_high": gap_high,
                "gap_size": gap_size,
                "gap_size_pct": gap_size_pct,
                "days_ago": age_in_trading_days,
                "weeks_ago": weeks_ago,
                "location": location,
                "distance_to_gap_pct":
                    distance_to_gap_pct,
                "is_filled":
                    fill_result["is_filled"],
                "fill_pct":
                    fill_result["fill_pct"],
                "filled_date":
                    fill_result["filled_date"]
            }
        )

    unfilled_gaps = [
        gap
        for gap in gaps
        if not gap["is_filled"]
    ]

    if not unfilled_gaps:
        return {
            **empty_gap_result(),
            "total_gaps_detected": len(gaps),
            "unfilled_gap_count": 0
        }

    # Select the gap nearest to the current price.
    nearest_gap = min(
        unfilled_gaps,
        key=lambda gap: abs(
            gap["distance_to_gap_pct"]
        )
    )

    return {
        "exists": True,

        "gap_type":
            nearest_gap["gap_type"],

        "gap_date":
            nearest_gap["gap_date"].strftime(
                "%Y-%m-%d"
            ),

        "gap_low": round(
            nearest_gap["gap_low"],
            3
        ),

        "gap_high": round(
            nearest_gap["gap_high"],
            3
        ),

        "gap_size": round(
            nearest_gap["gap_size"],
            3
        ),

        "gap_size_pct": round(
            nearest_gap["gap_size_pct"],
            3
        ),

        "days_ago":
            nearest_gap["days_ago"],

        "weeks_ago":
            nearest_gap["weeks_ago"],

        "location":
            nearest_gap["location"],

        "distance_to_gap_pct": round(
            nearest_gap["distance_to_gap_pct"],
            3
        ),

        "is_filled": False,

        "is_effectively_filled": bool(
            nearest_gap["fill_pct"] >= 95.0
        ),

        "fill_pct": round(
            nearest_gap["fill_pct"],
            3
        ),

        "filled_date":
            nearest_gap["filled_date"],

        "total_gaps_detected":
            len(gaps),

        "unfilled_gap_count":
            len(unfilled_gaps)
    }


def evaluate_gap_fill(
    clean_df,
    gap_position,
    gap_type,
    gap_low,
    gap_high
):
    """
    Determine whether a gap was filled after it formed.

    GAP_UP:
        Fully filled when a later low reaches gap_low.

    GAP_DOWN:
        Fully filled when a later high reaches gap_high.
    """

    future_df = clean_df.iloc[
        gap_position + 1:
    ]

    if future_df.empty:
        return {
            "is_filled": False,
            "fill_pct": 0.0,
            "filled_date": None
        }

    gap_size = gap_high - gap_low

    if gap_size <= 0:
        return {
            "is_filled": True,
            "fill_pct": 100.0,
            "filled_date": None
        }

    if gap_type == "GAP_UP":
        lowest_future_price = float(
            future_df["low"].min()
        )

        filled_rows = future_df[
            future_df["low"] <= gap_low
        ]

        if not filled_rows.empty:
            filled_date = pd.Timestamp(
                filled_rows.index[0]
            ).strftime("%Y-%m-%d")

            return {
                "is_filled": True,
                "fill_pct": 100.0,
                "filled_date": filled_date
            }

        if lowest_future_price >= gap_high:
            fill_pct = 0.0
        else:
            fill_pct = (
                gap_high - lowest_future_price
            ) / gap_size * 100

    elif gap_type == "GAP_DOWN":
        highest_future_price = float(
            future_df["high"].max()
        )

        filled_rows = future_df[
            future_df["high"] >= gap_high
        ]

        if not filled_rows.empty:
            filled_date = pd.Timestamp(
                filled_rows.index[0]
            ).strftime("%Y-%m-%d")

            return {
                "is_filled": True,
                "fill_pct": 100.0,
                "filled_date": filled_date
            }

        if highest_future_price <= gap_low:
            fill_pct = 0.0
        else:
            fill_pct = (
                highest_future_price - gap_low
            ) / gap_size * 100

    else:
        raise ValueError(
            f"Unknown gap type: {gap_type}"
        )

    fill_pct = max(
        0.0,
        min(100.0, fill_pct)
    )

    return {
        "is_filled": False,
        "fill_pct": fill_pct,
        "filled_date": None
    }


def empty_gap_result():
    """
    Return a consistent structure when no unfilled gap exists.
    """

    return {
        "exists": False,
        "gap_type": None,
        "gap_date": None,
        "gap_low": None,
        "gap_high": None,
        "gap_size": None,
        "gap_size_pct": None,
        "days_ago": None,
        "weeks_ago": None,
        "location": None,
        "distance_to_gap_pct": None,
        "is_filled": None,
        "is_effectively_filled": None,
        "fill_pct": None,
        "filled_date": None,
        "total_gaps_detected": 0,
        "unfilled_gap_count": 0
    }


# ============================================================================
# Short-term weekly entry analysis
# ============================================================================

def count_consecutive_return_weeks(return_series, positive=True):
    values = return_series.dropna().astype(float).tolist()
    count = 0
    for value in reversed(values):
        if (positive and value > 0) or ((not positive) and value < 0):
            count += 1
        else:
            break
    return count


def build_short_term_structure(df_weekly, atr_period=14):
    required = ["open", "high", "low", "close"]
    missing = [c for c in required if c not in df_weekly.columns]
    if missing:
        raise ValueError(f"Missing short-term structure columns: {missing}")
    df = df_weekly[required].copy().sort_index()
    for c in required:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=required)
    if len(df) < 27:
        raise ValueError("At least 27 weekly candles are required.")

    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr_s = tr.ewm(alpha=1 / atr_period, adjust=False, min_periods=atr_period).mean()
    close = float(df["close"].iloc[-1])
    high = float(df["high"].iloc[-1])
    low = float(df["low"].iloc[-1])
    atr = float(atr_s.iloc[-1])
    returns = df["close"].pct_change() * 100

    def wh(n): return float(df["high"].tail(n).max())
    def wl(n): return float(df["low"].tail(n).min())
    def ph(n): return float(df["high"].iloc[-(n + 1):-1].max())
    def pl(n): return float(df["low"].iloc[-(n + 1):-1].min())
    def change(offset): return (close / float(df["close"].iloc[-offset]) - 1) * 100

    h4, h13, h26 = wh(4), wh(13), wh(26)
    l4, l13, l26 = wl(4), wl(13), wl(26)
    ph4, ph13, ph26 = ph(4), ph(13), ph(26)
    pl4, pl13, pl26 = pl(4), pl(13), pl(26)

    return {
        "atr14": round(atr, 3),
        "weekly_range_atr": round((high - low) / atr, 3) if atr > 0 else None,
        "change_pct_2w": round(change(3), 3),
        "change_pct_4w": round(change(5), 3),
        "change_pct_8w": round(change(9), 3),
        "high_4w": round(h4, 3), "high_13w": round(h13, 3), "high_26w": round(h26, 3),
        "low_4w": round(l4, 3), "low_13w": round(l13, 3), "low_26w": round(l26, 3),
        "previous_high_4w": round(ph4, 3), "previous_high_13w": round(ph13, 3),
        "previous_high_26w": round(ph26, 3), "previous_low_4w": round(pl4, 3),
        "previous_low_13w": round(pl13, 3), "previous_low_26w": round(pl26, 3),
        "drawdown_from_4w_high_pct": round((close / h4 - 1) * 100, 3),
        "drawdown_from_13w_high_pct": round((close / h13 - 1) * 100, 3),
        "drawdown_from_26w_high_pct": round((close / h26 - 1) * 100, 3),
        "distance_to_13w_high_pct": round((close / h13 - 1) * 100, 3),
        "distance_to_26w_high_pct": round((close / h26 - 1) * 100, 3),
        "broke_previous_4w_high": bool(high > ph4),
        "closed_above_previous_4w_high": bool(close > ph4),
        "broke_previous_13w_high": bool(high > ph13),
        "closed_above_previous_13w_high": bool(close > ph13),
        "broke_previous_26w_high": bool(high > ph26),
        "closed_above_previous_26w_high": bool(close > ph26),
        "consecutive_up_weeks": count_consecutive_return_weeks(returns, True),
        "consecutive_down_weeks": count_consecutive_return_weeks(returns, False),
    }


def add_price_level_candidate(supports, resistances, name, price, current_price, level_type, direction=None):
    if price is None or pd.isna(price):
        return
    price = float(price)
    current_price = float(current_price)
    item = {
        "name": str(name), "price": round(price, 3), "type": str(level_type),
        "direction": direction, "sources": [str(name)],
        "distance_pct": round((price / current_price - 1) * 100, 3),
    }
    (supports if price <= current_price else resistances).append(item)


def merge_duplicate_price_levels(levels, tolerance_pct=0.20):
    merged = []
    for raw in levels:
        item = raw.copy()
        match = None
        for existing in merged:
            base = max(abs(float(item["price"])), abs(float(existing["price"])), 1e-9)
            if abs(float(item["price"]) - float(existing["price"])) / base * 100 <= tolerance_pct:
                match = existing
                break
        if match is None:
            merged.append(item)
        else:
            for source in item.get("sources", [item["name"]]):
                if source not in match["sources"]:
                    match["sources"].append(source)
            if len(match["sources"]) >= 3:
                match["name"] = "MULTI_TIMEFRAME_LEVEL"
            else:
                match["name"] = "+".join(match["sources"])
    return merged


def get_level_quality_score(level, is_support=True):
    score = 50
    if level.get("type") == "MOVING_AVERAGE":
        direction = level.get("direction")
        if is_support:
            score += {"UP": 22, "FLAT": 8, "DOWN": -12}.get(direction, 0)
        else:
            score += {"DOWN": 18, "FLAT": 8, "UP": 3}.get(direction, 0)
    elif level.get("type") == "GAP":
        score += 15
    elif level.get("type") == "PRICE_STRUCTURE":
        score += 10
    if len(level.get("sources", [])) >= 3:
        score += 15
    elif len(level.get("sources", [])) == 2:
        score += 8
    return int(max(0, min(100, score)))


def build_support_resistance_candidates(weekly_k, moving_averages, gap, short_term_structure, atr=None):
    current = float(weekly_k["close"])
    atr = float(atr if atr is not None else short_term_structure["atr14"])
    supports, resistances = [], []
    for name in ["ma5", "ma10", "ma20", "ema50"]:
        add_price_level_candidate(supports, resistances, name.upper(), moving_averages.get(name), current,
                                  "MOVING_AVERAGE", moving_averages.get(f"{name}_direction"))
    current_week_high = float(weekly_k["high"])
    current_week_low = float(weekly_k["low"])
    for name in ["low_4w", "previous_low_4w", "low_13w", "previous_low_13w", "low_26w",
                 "high_4w", "previous_high_4w", "high_13w", "previous_high_13w",
                 "high_26w", "previous_high_26w"]:
        price = short_term_structure.get(name)
        if price is None or pd.isna(price):
            continue
        if name in {"high_4w", "high_13w", "high_26w"} and abs(float(price) - current_week_high) <= 1e-9:
            continue
        add_price_level_candidate(supports, resistances, name.upper(), price, current, "PRICE_STRUCTURE")
    if (
        gap.get("exists")
        and not gap.get("is_effectively_filled", False)
    ):
        add_price_level_candidate(supports, resistances, "GAP_LOW", gap.get("gap_low"), current, "GAP")
        add_price_level_candidate(supports, resistances, "GAP_HIGH", gap.get("gap_high"), current, "GAP")

    supports = merge_duplicate_price_levels(sorted(supports, key=lambda x: abs(x["distance_pct"])))
    resistances = merge_duplicate_price_levels(sorted(resistances, key=lambda x: abs(x["distance_pct"])))
    supports.sort(key=lambda x: abs(x["distance_pct"]))
    resistances.sort(key=lambda x: abs(x["distance_pct"]))
    for item in supports:
        item["distance_atr"] = round(abs(current - float(item["price"])) / atr, 3) if atr > 0 else None
        item["quality_score"] = get_level_quality_score(item, True)
        item["eligible_for_rr"] = bool(
            item["quality_score"] >= 45
            and item["distance_atr"] is not None
            and item["distance_atr"] <= 0.75
        )
    for item in resistances:
        item["distance_atr"] = round(abs(float(item["price"]) - current) / atr, 3) if atr > 0 else None
        item["quality_score"] = get_level_quality_score(item, False)
    eligible_supports = [
        item
        for item in supports
        if item.get("eligible_for_rr", False)
    ]
    # Never fall back to an ineligible level for formal trade planning.
    # The nearest physical level remains available separately as
    # nearest_reference_support.
    formal_support = eligible_supports[0] if eligible_supports else None
    return {
        "current_price": round(current, 3),
        "current_week_reference_high": round(current_week_high, 3),
        "current_week_reference_low": round(current_week_low, 3),
        "nearest_support": formal_support,
        "nearest_reference_support": supports[0] if supports else None,
        "nearest_resistance": resistances[0] if resistances else None,
        "support_candidates": supports[:8],
        "resistance_candidates": resistances[:8],
    }


def get_entry_rating(score):
    if score >= 80: return "HIGH"
    if score >= 65: return "MODERATELY_HIGH"
    if score >= 50: return "NEUTRAL"
    if score >= 35: return "LOW"
    return "VERY_LOW"


def _safe_float(value):
    return None if value is None or pd.isna(value) else float(value)


def _entry_reward_risk(close, atr, support, resistance):
    if not support or not resistance or atr is None or atr <= 0:
        return None, None
    invalidation = float(support["price"]) - 0.50 * atr
    downside = close - invalidation
    upside = float(resistance["price"]) - close
    ratio = upside / downside if upside > 0 and downside > 0 else None
    return invalidation, ratio


def build_chase_analysis(weekly_k, moving_averages, macd, volume_analysis, gap,
                         short_term_structure, support_resistance):
    positive, risks = [], []
    close = float(weekly_k["close"])
    change = float(weekly_k["weekly_change_pct"])
    close_loc = float(weekly_k["close_location"])
    upper = float(weekly_k["upper_shadow_pct"])
    lower = float(weekly_k["lower_shadow_pct"])
    ma5, ma10, ma20, ema50 = [float(moving_averages[k]) for k in ["ma5", "ma10", "ma20", "ema50"]]
    dirs = [moving_averages[f"{k}_direction"] for k in ["ma5", "ma10", "ma20", "ema50"]]
    atr = _safe_float(short_term_structure.get("atr14"))
    vr = _safe_float(volume_analysis.get("volume_ratio_13w"))
    change4 = _safe_float(short_term_structure.get("change_pct_4w"))
    up_weeks = int(short_term_structure.get("consecutive_up_weeks", 0))
    broke13 = bool(short_term_structure.get("broke_previous_13w_high", False))
    closed13 = bool(short_term_structure.get("closed_above_previous_13w_high", False))
    support = support_resistance.get("nearest_support")
    resistance = support_resistance.get("nearest_resistance")

    if close > ma5 > ma10 > ma20 > ema50 and all(d == "UP" for d in dirs):
        trend = 20; positive.append("Standard bullish weekly MA alignment")
    elif close > ma5 and close > ma10 and close > ma20 and dirs[1] == "UP" and dirs[2] == "UP":
        trend = 15; positive.append("Price is above MA5, MA10 and MA20")
    elif close > ma20 and dirs[2] == "UP":
        trend = 9; positive.append("Price remains above a rising MA20")
    elif close > ema50 and dirs[3] in ["UP", "FLAT"]:
        trend = 5
    else:
        trend = 0
    if close < ma5: risks.append("Price is below MA5")
    if close < ma10: risks.append("Price is below MA10")
    if close < ma20: risks.append("Price is below MA20")

    d5 = (close - ma5) / atr if atr and atr > 0 else None
    d10 = (close - ma10) / atr if atr and atr > 0 else None
    if d5 is None: extension = 0
    elif 0 <= d5 <= 0.50: extension = 15; positive.append("Price is close to MA5 in ATR terms")
    elif d5 <= 0.75: extension = 12
    elif d5 <= 1.25: extension = 8
    elif d5 <= 2.00: extension = 3; risks.append("Price is extended above MA5")
    elif d5 > 2.00: extension = 0; risks.append("Price is severely extended above MA5")
    else: extension = 2; risks.append("Price is below MA5")
    if d10 is not None and d10 > 2.50:
        extension = max(0, extension - 4); risks.append("Price is excessively extended above MA10")

    if change > 0 and close_loc >= 0.80 and upper <= 20:
        candle = 15; positive.append("Strong weekly close with limited upper rejection")
    elif change > 0 and close_loc >= 0.60 and upper < 35:
        candle = 11; positive.append("Weekly candle closed in its upper range")
    elif change > 0 and close_loc >= 0.50: candle = 7
    elif close_loc >= 0.60: candle = 5
    else: candle = 0
    if upper >= 50 and close_loc <= 0.40:
        candle = 0; risks.append("Severe weekly upper rejection")
    elif upper >= 40 and close_loc <= 0.50:
        candle = min(candle, 3); risks.append("Meaningful weekly upper rejection")
    if close_loc <= 0.20:
        candle = 0; risks.append("Weekly close is near the weekly low")
    if lower >= 35 and close_loc >= 0.60: candle = min(15, candle + 3)

    state = macd.get("state")
    if macd.get("dif_above_dea") and macd.get("dif_above_zero") and macd.get("dea_above_zero") and state == "POSITIVE_EXPANDING":
        macd_score = 15; positive.append("MACD is bullish above zero with expanding momentum")
    elif macd.get("dif_above_dea") and macd.get("dif_above_zero") and macd.get("dea_above_zero"):
        macd_score = 10; positive.append("MACD remains bullish above zero")
        if state == "POSITIVE_NARROWING": risks.append("MACD bullish momentum is narrowing")
    elif state == "ZERO_LINE_CROSS_UP": macd_score = 9; positive.append("Fresh bullish MACD crossover")
    elif macd.get("dif_above_dea") and not macd.get("dif_above_zero") and state == "POSITIVE_EXPANDING":
        macd_score = 7; risks.append("Long-term MACD confirmation is pending")
    elif state == "NEGATIVE_NARROWING": macd_score = 3
    else:
        macd_score = 0
        if state in ["NEGATIVE_EXPANDING", "ZERO_LINE_CROSS_DOWN"]: risks.append("MACD bearish momentum is expanding")

    if vr is None: volume = 0
    elif change > 0 and vr >= 1.20 and close_loc >= 0.70 and upper <= 30: volume = 15; positive.append("Bullish move is confirmed by volume")
    elif change > 0 and vr >= 1.00 and close_loc >= 0.60: volume = 11
    elif change > 0 and vr >= 0.75: volume = 7
    elif change > 0: volume = 3; risks.append("Price advanced on low volume")
    elif vr < 0.80: volume = 4
    else: volume = 0
    if vr is not None and vr >= 1.50 and upper >= 40 and close_loc < 0.50:
        volume = 0; risks.append("High-volume upper rejection raises distribution risk")

    if change4 is None: acceleration = 0
    elif 3 <= change4 <= 9: acceleration = 10; positive.append("Recent appreciation is constructive without extreme extension")
    elif 0 <= change4 < 3: acceleration = 7
    elif 9 < change4 < 12: acceleration = 6
    elif 12 <= change4 < 18: acceleration = 3; risks.append("Four-week gain is extended")
    elif change4 >= 18: acceleration = 0; risks.append("Four-week gain is severely extended")
    else: acceleration = 2
    if up_weeks >= 7: acceleration = 0; risks.append("Too many consecutive up weeks")
    elif up_weeks >= 5: acceleration = min(acceleration, 3)

    if closed13 and change > 0 and close_loc >= 0.70:
        if vr is not None and vr >= 1.20: breakout = 10; positive.append("Confirmed 13-week breakout with volume support")
        elif vr is not None and vr >= 1.00: breakout = 7
        else: breakout = 4; risks.append("Breakout volume is below average")
    elif broke13 and not closed13:
        breakout = 0; risks.append("Price broke the previous 13-week high but failed to close above it")
    else:
        breakout = 2; risks.append("Price has not confirmed a 13-week breakout")

    score = trend + extension + candle + macd_score + volume + acceleration + breakout
    invalidation, rr = _entry_reward_risk(close, atr, support, resistance)
    ds = (close - float(support["price"])) / atr if support and atr and atr > 0 else None
    dr = (float(resistance["price"]) - close) / atr if resistance and atr and atr > 0 else None
    if dr is not None and 0 < dr < 0.25: score -= 8; risks.append("Price is immediately below resistance")
    elif dr is not None and 0 < dr < 0.50: score -= 5; risks.append("Upside room before resistance is limited")
    if rr is not None:
        if rr >= 3: score += 5
        elif rr >= 2: score += 3
        elif rr < 0.75: score -= 6; risks.append("Upside is small relative to technical invalidation risk")
    if (
        gap.get("exists")
        and not gap.get("is_effectively_filled", False)
    ):
        gd = _safe_float(gap.get("distance_to_gap_pct"))
        if gap.get("location") == "ABOVE_PRICE" and gd is not None and gd <= 3:
            score -= 7; risks.append("Nearby overhead gap restricts upside")
        if gap.get("location") == "PRICE_INSIDE_GAP":
            score -= 5; risks.append("Price is trading inside an unfilled gap")

    if not closed13: score = min(score, 74)
    if broke13 and not closed13: score = min(score, 55)
    if vr is not None and vr < 1.00 and not closed13:
        score = min(score, 69); risks.append("Volume is below the 13-week average")
    if vr is not None and vr < 1.00 and closed13: score = min(score, 79)
    score = int(max(0, min(100, round(score))))
    if score >= 80:
        decision = (
            "CHASE_ACCEPTABLE_WITH_RISK_CONTROL"
            if closed13
            else "WAIT_FOR_BREAKOUT_CONFIRMATION"
        )
    elif score >= 65:
        decision = (
            "BREAKOUT_ENTRY_ACCEPTABLE"
            if closed13
            else "WAIT_FOR_BREAKOUT_CONFIRMATION"
        )
    elif score >= 50:
        decision = "WAIT_FOR_BREAKOUT_CONFIRMATION"
    elif score >= 35:
        decision = "PREFER_PULLBACK_OVER_CHASING"
    else:
        decision = "DO_NOT_CHASE"
    return {
        "score": score, "rating": get_entry_rating(score), "decision": decision,
        "components": {"trend": trend, "extension": extension, "weekly_candle": candle,
                       "macd": macd_score, "volume": volume, "acceleration": acceleration,
                       "breakout": breakout},
        "distance_ma5_atr": round(d5, 3) if d5 is not None else None,
        "distance_ma10_atr": round(d10, 3) if d10 is not None else None,
        "nearest_support_distance_atr": round(ds, 3) if ds is not None else None,
        "nearest_resistance_distance_atr": round(dr, 3) if dr is not None else None,
        "invalidation_price": round(invalidation, 3) if invalidation is not None else None,
        "estimated_reward_risk": round(rr, 3) if rr is not None else None,
        "positive_factors": list(dict.fromkeys(positive)), "risk_factors": list(dict.fromkeys(risks)),
    }


def _classify_support_usage(support_distance_atr, eligible_for_rr=False):
    """Classify whether formal support is usable for an entry plan."""
    if not eligible_for_rr or support_distance_atr is None:
        return "NO_ACTIONABLE_SUPPORT"
    if support_distance_atr <= 0.75:
        return "ACTIONABLE_SUPPORT"
    if support_distance_atr <= 1.00:
        return "REFERENCE_SUPPORT"
    return "DISTANT_STRUCTURAL_SUPPORT"


def build_buy_low_analysis(weekly_k, moving_averages, macd, volume_analysis,
                           gap, short_term_structure, support_resistance):
    positive, risks = [], []
    close = float(weekly_k["close"]); change = float(weekly_k["weekly_change_pct"])
    close_loc = float(weekly_k["close_location"]); lower = float(weekly_k["lower_shadow_pct"])
    upper = float(weekly_k["upper_shadow_pct"]); atr = float(short_term_structure["atr14"])
    vr = float(volume_analysis["volume_ratio_13w"])
    ma5, ma10, ma20, ema50 = [float(moving_averages[k]) for k in ["ma5", "ma10", "ma20", "ema50"]]
    support = support_resistance.get("nearest_support"); resistance = support_resistance.get("nearest_resistance")
    rising = sum(moving_averages[f"{k}_direction"] == "UP" for k in ["ma5", "ma10", "ma20", "ema50"])
    up_weeks = int(short_term_structure.get("consecutive_up_weeks", 0))
    resistance_distance_atr = (
        _safe_float(resistance.get("distance_atr")) if resistance else None
    )

    if close > ma20 and close > ema50 and rising == 4: trend = 20; positive.append("Pullback remains within a strong upward trend")
    elif close > ma20 and close > ema50 and rising >= 3: trend = 17
    elif moving_averages["ma20_direction"] == "UP" and moving_averages["ema50_direction"] in ["UP", "FLAT"]: trend = 13
    elif close > ema50: trend = 7
    else: trend = 0
    falling = (
        close < ma5
        and close < ma10
        and close < ma20
        and close < ema50
        and moving_averages["ma5_direction"] == "DOWN"
        and moving_averages["ma10_direction"] == "DOWN"
        and moving_averages["ma20_direction"] == "DOWN"
        and moving_averages["ema50_direction"] == "DOWN"
        and macd["state"] in ["NEGATIVE_EXPANDING", "ZERO_LINE_CROSS_DOWN"]
        and close_loc <= 0.35
    )

    early_recovery = (
        close > ma5
        and close > ma10
        and close < ma20
        and close < ema50
        and moving_averages["ma5_direction"] == "UP"
        and moving_averages["ma10_direction"] == "UP"
        and macd["state"] == "NEGATIVE_NARROWING"
    )

    continuation_breakout = (
        close > ma5 and close > ma10 and close > ma20 and close > ema50
        and change > 0
        and bool(short_term_structure.get("closed_above_previous_13w_high", False))
        and bool(short_term_structure.get("closed_above_previous_26w_high", False))
    )
    continuation_near_resistance = (
        close > ma5
        and close > ma10
        and close > ma20
        and close > ema50
        and change > 0
        and resistance_distance_atr is not None
        and resistance_distance_atr <= 0.50
        and (up_weeks >= 2 or close_loc >= 0.70)
    )

    if falling:
        setup_type = "FALLING_KNIFE"
    elif early_recovery:
        setup_type = "EARLY_RECOVERY"
    elif continuation_breakout:
        setup_type = "TREND_CONTINUATION_BREAKOUT"
    elif continuation_near_resistance:
        setup_type = "TREND_CONTINUATION_NEAR_RESISTANCE"
    elif (close > ma20 and close > ema50 and rising >= 3
          and moving_averages["ma20_direction"] in ["UP", "FLAT"]):
        setup_type = "TREND_PULLBACK"
    else:
        setup_type = "UNCONFIRMED_RECOVERY"

    ds = (close - float(support["price"])) / atr if support and atr > 0 else None
    support_eligible = bool(
        support
        and support.get("eligible_for_rr", False)
    )
    support_usage = _classify_support_usage(
        ds,
        eligible_for_rr=support_eligible
    )
    if support is None:
        risks.append(
            "No nearby support meets the minimum quality and distance requirements"
        )
    if ds is None: support_score = 0
    elif 0 <= ds <= 0.25: support_score = 20; positive.append("Price is immediately above weekly support")
    elif ds <= 0.50: support_score = 17; positive.append("Price is close to weekly support")
    elif ds <= 0.75: support_score = 12
    elif ds <= 1.25: support_score = 6
    else: support_score = 1; risks.append("Price remains too far above support for strong buy-low value")
    if support and int(support.get("quality_score", 50)) < 45: support_score = max(0, support_score - 5)

    dd = abs(min(0.0, float(short_term_structure["drawdown_from_4w_high_pct"])))
    if 2 <= dd <= 6: pullback = 15; positive.append("Pullback depth is constructive")
    elif 6 < dd <= 10: pullback = 11
    elif 10 < dd <= 15: pullback = 5; risks.append("Pullback is deep and needs confirmation")
    elif dd > 15: pullback = 0; risks.append("Drawdown may represent trend damage")
    elif 1 <= dd < 2: pullback = 8
    else: pullback = 2; risks.append("Price has not pulled back enough for strong buy-low value")

    # Pullback depth is most meaningful inside an established
    # upward trend. In a bearish structure, a shallow drawdown
    # may only represent consolidation rather than a healthy pullback.
    original_pullback_score = pullback

    if setup_type == "EARLY_RECOVERY":
        pullback = min(pullback, 10)
    elif setup_type == "TREND_CONTINUATION_NEAR_RESISTANCE":
        pullback = min(pullback, 8)

    elif setup_type == "UNCONFIRMED_RECOVERY":
        pullback = min(pullback, 6)

    elif setup_type == "FALLING_KNIFE":
        pullback = 0

    if pullback < original_pullback_score:
        risks.append(
            "Pullback-depth score is capped by the current setup state"
        )

    balanced_long_shadows = upper >= 35 and lower >= 35 and abs(upper - lower) <= 10
    strong = lower >= 35 and close_loc >= 0.60 and not balanced_long_shadows
    moderate = lower >= 20 and close_loc >= 0.50 and not balanced_long_shadows
    if balanced_long_shadows:
        candle = 4; risks.append("Long upper and lower shadows indicate weekly indecision")
    elif strong: candle = 15; positive.append("Weekly candle strongly rejected lower prices")
    elif moderate: candle = 9; positive.append("Weekly candle shows moderate support")
    elif close_loc >= 0.60: candle = 6
    elif close_loc >= 0.40: candle = 3
    else: candle = 0
    if close_loc <= 0.20 and lower < 15: candle = 0; risks.append("Weekly candle closed near its low without support confirmation")
    body_pct = float(weekly_k["body_pct"])
    if body_pct < 10 and upper >= 30 and lower >= 35:
        candle = min(candle, 9); risks.append("Small candle body and upper shadow indicate weekly indecision")
    if upper >= 45:
        candle = min(candle, 5 if close_loc >= 0.50 else 2)
        risks.append("Weekly candle shows meaningful upper rejection")
    elif upper >= 35 and upper > lower:
        candle = min(candle, 6)
        risks.append("Upper rejection limits the quality of the support candle")

    if change < 0:
        if vr < 0.75: volume = 10; positive.append("Pullback occurred on low volume")
        elif vr <= 1.10: volume = 7
        elif vr < 1.50: volume = 3
        else: volume = 0; risks.append("Pullback occurred on heavy volume")
    elif vr < 0.75:
        volume = 2; risks.append("Recovery advanced on low volume")
    elif vr < 1.00: volume = 4
    elif vr < 1.20: volume = 6
    elif strong: volume = 9
    elif moderate: volume = 7
    else: volume = 6

    state = macd["state"]
    if macd["dif_above_dea"] and macd["dif_above_zero"] and macd["dea_above_zero"] and state == "POSITIVE_EXPANDING": macd_score = 10
    elif macd["dif_above_dea"] and macd["dif_above_zero"] and macd["dea_above_zero"]:
        macd_score = 8
        if state == "POSITIVE_NARROWING": risks.append("MACD bullish momentum is slowing")
    elif state == "ZERO_LINE_CROSS_UP":
        macd_score = 7
    elif (
        macd["dif_above_dea"]
        and not macd["dif_above_zero"]
        and not macd["dea_above_zero"]
        and state == "POSITIVE_EXPANDING"
    ):
        macd_score = 6
        positive.append("MACD recovery is expanding below the zero axis")
        risks.append("MACD remains below zero, so long-term trend confirmation is pending")
    elif state == "NEGATIVE_NARROWING":
        macd_score = 5
    else:
        macd_score = 0
        if state in ["NEGATIVE_EXPANDING", "ZERO_LINE_CROSS_DOWN"]: risks.append("MACD bearish momentum is expanding")

    rr_support = support if support_usage == "ACTIONABLE_SUPPORT" else None
    invalidation, rr = _entry_reward_risk(close, atr, rr_support, resistance)
    if rr is None: rr_score = 0
    elif rr >= 3: rr_score = 10
    elif rr >= 2: rr_score = 7
    elif rr >= 1: rr_score = 4
    elif rr >= 0.75: rr_score = 2
    else: rr_score = 0; risks.append("Nearby resistance limits upside relative to invalidation risk")

    score = trend + support_score + pullback + candle + volume + macd_score + rr_score
    pullback_week = change < 0; near_support = ds is not None and 0 <= ds <= 0.50
    support_rejection = lower >= 25 and close_loc >= 0.60
    if not pullback_week and not support_rejection:
        score = min(score, 69); risks.append("Current week is neither a pullback nor a clear support-rejection week")
    elif near_support and support_rejection: score = min(score, 89)
    elif pullback_week and not support_rejection:
        score = min(score, 74); risks.append("Pullback has not shown clear weekly support rejection")
    if setup_type == "TREND_CONTINUATION_BREAKOUT":
        score = min(score, 64); risks.append("Breakout continuation is not a pullback entry")
        if vr < 1.00: risks.append("Breakout follow-through requires better volume confirmation")
    if setup_type == "TREND_CONTINUATION_NEAR_RESISTANCE":
        score = min(score, 59)
        risks.append("Trend continuation is near resistance rather than at a pullback entry")
    if falling:
        score = min(score, 34)
        risks.append("Setup resembles a falling knife")

    if early_recovery:
        score = min(score, 59)
        risks.append("Early recovery remains below falling MA20 and EMA50")

        resistance_distance_atr = (
            resistance.get("distance_atr")
            if resistance
            else None
        )

        if (
            resistance_distance_atr is not None
            and resistance_distance_atr < 0.50
        ):
            score = min(score, 44)
            risks.append("Early recovery is immediately below nearby resistance")

    if rr is not None:
        if rr < 0.75:
            score = min(score, 59)
            risks.append("Buy-low score is capped because estimated reward/risk is below 0.75")
        elif rr < 1.00:
            score = min(score, 69)
            risks.append("Buy-low score is capped because estimated reward/risk is below 1.0")
        elif rr < 1.50:
            score = min(score, 79)

    score = int(max(0, min(100, round(score))))

    if falling:
        decision = "AVOID_CATCHING_FALLING_KNIFE"
    elif setup_type == "UNCONFIRMED_RECOVERY":
        decision = "WAIT_FOR_RECOVERY_CONFIRMATION"
    elif early_recovery:
        decision = "WAIT_FOR_REVERSAL_CONFIRMATION"
    elif setup_type in ["TREND_CONTINUATION_BREAKOUT", "TREND_CONTINUATION_NEAR_RESISTANCE"]:
        decision = "WAIT_FOR_PULLBACK_ENTRY"
    elif score >= 80:
        if not support_rejection or candle < 9: decision = "WAIT_FOR_SUPPORT_CONFIRMATION"
        elif ds is None or ds > 0.25: decision = "WAIT_FOR_BUY_LOW_ZONE"
        elif rr is None or rr < 1.50: decision = "WAIT_FOR_BETTER_REWARD_RISK"
        else: decision = "BUY_LOW_SETUP_STRONG"
    elif score >= 65:
        if not support_rejection or candle < 6: decision = "WAIT_FOR_SUPPORT_CONFIRMATION"
        elif rr is None or rr < 1.00: decision = "WAIT_FOR_BETTER_REWARD_RISK"
        else: decision = "BUY_LOW_SETUP_ACCEPTABLE"
    elif score >= 35:
        decision = "WAIT_FOR_SUPPORT_CONFIRMATION"
    else:
        decision = "NO_BUY_LOW_EDGE"
    return {
        "score": score, "rating": get_entry_rating(score), "decision": decision,
        "setup_type": setup_type,
        "components": {"trend_background": trend, "support_proximity": support_score,
                       "pullback_depth": pullback, "support_candle": candle,
                       "volume_behavior": volume, "macd_context": macd_score, "reward_risk": rr_score},
        "nearest_support": support, "nearest_resistance": resistance,
        "support_usage": support_usage,
        "support_distance_atr": round(ds, 3) if ds is not None else None,
        "drawdown_from_4w_high_pct": short_term_structure["drawdown_from_4w_high_pct"],
        "invalidation_price": round(invalidation, 3) if invalidation is not None else None,
        "estimated_reward_risk": round(rr, 3) if rr is not None else None,
        "positive_factors": list(dict.fromkeys(positive)), "risk_factors": list(dict.fromkeys(risks)),
    }


def choose_preferred_entry_style(chase_analysis, buy_low_analysis):
    """Select the preferred weekly entry approach using scores and setup states."""
    chase_score = int(chase_analysis["score"])
    buy_low_score = int(buy_low_analysis["score"])
    chase_decision = chase_analysis.get("decision")
    buy_low_decision = buy_low_analysis.get("decision")
    buy_low_type = buy_low_analysis.get("setup_type")
    chase_rr = chase_analysis.get("estimated_reward_risk")
    buy_low_rr = buy_low_analysis.get("estimated_reward_risk")
    difference = chase_score - buy_low_score

    if buy_low_type == "FALLING_KNIFE":
        return "WAIT_NO_CLEAR_EDGE"

    if buy_low_type == "EARLY_RECOVERY":
        return "WAIT_FOR_REVERSAL_CONFIRMATION"

    if buy_low_type == "UNCONFIRMED_RECOVERY":
        return "WAIT_FOR_RECOVERY_CONFIRMATION"

    if buy_low_type in ["TREND_CONTINUATION_BREAKOUT", "TREND_CONTINUATION_NEAR_RESISTANCE"]:
        return "WAIT_FOR_BREAKOUT_OR_PULLBACK"
    if (
        buy_low_type == "TREND_PULLBACK"
        and buy_low_decision == "WAIT_FOR_SUPPORT_CONFIRMATION"
    ):
        return "PREFER_WAITING_FOR_SUPPORT"
    if buy_low_type == "TREND_PULLBACK" and buy_low_decision == "WAIT_FOR_BETTER_REWARD_RISK":
        return "WAIT_FOR_BREAKOUT_OR_DEEPER_PULLBACK"

    if (
        chase_score >= 75
        and difference >= 10
        and chase_decision in [
            "CHASE_ACCEPTABLE_WITH_RISK_CONTROL",
            "BREAKOUT_ENTRY_ACCEPTABLE",
        ]
    ):
        return "CHASE_BREAKOUT"

    if (
        buy_low_score >= 75
        and difference <= -10
        and buy_low_decision in [
            "BUY_LOW_SETUP_STRONG",
            "BUY_LOW_SETUP_ACCEPTABLE",
        ]
    ):
        return "BUY_LOW_PULLBACK"

    if (
        chase_decision == "WAIT_FOR_BREAKOUT_CONFIRMATION"
        and buy_low_decision in [
            "WAIT_FOR_BETTER_REWARD_RISK",
            "WAIT_FOR_BUY_LOW_ZONE",
            "WAIT_FOR_SUPPORT_CONFIRMATION",
        ]
    ):
        return "WAIT_FOR_BREAKOUT_OR_PULLBACK"

    if (
        chase_score >= 65
        and buy_low_score >= 65
        and abs(difference) <= 5
        and chase_decision in [
            "CHASE_ACCEPTABLE_WITH_RISK_CONTROL",
            "BREAKOUT_ENTRY_ACCEPTABLE",
        ]
        and buy_low_decision in [
            "BUY_LOW_SETUP_STRONG",
            "BUY_LOW_SETUP_ACCEPTABLE",
        ]
    ):
        return "EITHER_WITH_CONFIRMATION"

    if buy_low_score > chase_score and buy_low_score >= 55:
        if buy_low_decision in [
            "BUY_LOW_SETUP_STRONG",
            "BUY_LOW_SETUP_ACCEPTABLE",
        ]:
            return "BUY_LOW_PULLBACK"
        return "PREFER_WAITING_FOR_SUPPORT"

    if chase_score > buy_low_score and chase_score >= 55:
        if chase_decision in [
            "CHASE_ACCEPTABLE_WITH_RISK_CONTROL",
            "BREAKOUT_ENTRY_ACCEPTABLE",
        ]:
            return "CHASE_BREAKOUT"
        return "PREFER_BREAKOUT_CONFIRMATION"

    if (
        chase_rr is not None
        and buy_low_rr is not None
        and chase_rr < 1.0
        and buy_low_rr < 1.0
    ):
        return "WAIT_FOR_BETTER_REWARD_RISK"

    if chase_score >= 50 and buy_low_score >= 50:
        return "WAIT_FOR_CLEARER_ENTRY"

    return "WAIT_NO_CLEAR_EDGE"
