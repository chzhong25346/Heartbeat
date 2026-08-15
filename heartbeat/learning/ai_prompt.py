from ..models import Index,  Quote, Quote_CSI300
import pandas as pd
import numpy as np
import json


def get_AI_Prompt(sdic, dbname, ticker):
    s = sdic[dbname]

    if dbname == "csi300":
        query = (
            s.query(Quote_CSI300)
            .filter(Quote_CSI300.symbol == ticker)
        )
    else:
        query = (
            s.query(Quote)
            .filter(Quote.symbol == ticker)
        )

    df = pd.read_sql(
        query.statement,
        s.bind,
        index_col="date"
    ).sort_index()

    df_weekly = to_weekly_df(df)

    if df_weekly is None or df_weekly.empty:
        raise ValueError(
            f"No weekly data found for {ticker} in {dbname}."
        )

    result = {
        "symbol": ticker,
        "database": dbname,

        "weekly_k": build_weekly_k(
            df_weekly
        ),

        "moving_averages": build_moving_averages(
            df_weekly=df_weekly,
            flat_threshold_pct=0.05
        ),

        "macd": build_macd(
            df_weekly=df_weekly,
            fast_period=14,
            slow_period=56,
            signal_period=5,
            history_weeks=8,
            histogram_multiplier=1,
            flat_threshold=0.0001
        ),

        "volume_analysis": build_volume_analysis(
            df_weekly=df_weekly,
            high_volume_threshold=1.20,
            history_weeks=8
        ),

        "gap": build_gap_analysis(
            df_daily=df,
            current_price=float(df_weekly["close"].iloc[-1]),
            lookback_days=252,
            minimum_gap_pct=0.30
        )
    }


    json_output = json.dumps(
        result,
        indent=2,
        ensure_ascii=False
    )

    prompt = f"""
    Analyze the following stock using weekly trading only.

    Focus on:
    1. Weekly trend stage
    2. MA5, MA10, MA20 and EMA50 structure
    3. Weekly MACD(14,56,5)
    4. Price and volume relationship
    5. Unfilled gaps
    6. Support and resistance
    7. Whether this is a reversal, pullback, or continuation

    Stock data:

    {json_output}
    """

    print(prompt)


############################################# Methods #############################


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
        if strong_volume and close_location >= 0.70:
            return "BULLISH_HIGH_VOLUME_CLOSE"

        if high_volume and close_location < 0.40:
            return "HIGH_VOLUME_UPPER_REJECTION"

        if high_volume:
            return "BULLISH_VOLUME_EXPANSION"

        return "PRICE_UP_NORMAL_VOLUME"

    if weekly_change_pct < 0:
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
        "fill_pct": None,
        "filled_date": None,
        "total_gaps_detected": 0,
        "unfilled_gap_count": 0
    }