from fastapi import APIRouter, HTTPException
from app.schemas.stock import (
    StockHistoryRequest,
    StockPredictionResponse,
    StockPredictRequest,
    StockIndicator,
    PredictionPoint,
    RegimeInfo,
    CoherenceInfo,
    ScenarioAnalysis,
    RiskMetrics,
)
from app.services.stock_service import run_prediction
from app.services.stock_analysis import calculate_indicators
from app.utils.market_data import MarketDataService
from app.core.config import settings
import pandas as pd
from typing import List
from datetime import timedelta

router = APIRouter()


def _next_trading_days(start, n: int) -> list:
    """Return the next n weekday dates after start."""
    dates = []
    current = start
    while len(dates) < n:
        current += timedelta(days=1)
        if current.weekday() < 5:   # Monday–Friday only
            dates.append(current)
    return dates


@router.get("/history", response_model=List[StockIndicator])
def get_stock_history(ticker: str, period: str = "1y"):
    data = MarketDataService.fetch_history(ticker, period)
    if data is None or data.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {ticker}")

    df_analyzed = calculate_indicators(data)

    results = []
    for index, row in df_analyzed.iterrows():
        def safe_float(val):
            return val if not pd.isna(val) else None

        results.append({
            "date":        index.strftime("%Y-%m-%d"),
            "close":       safe_float(row["Close"]),
            "volume":      int(row["Volume"]),
            "sma_20":      safe_float(row.get("SMA_20")),
            "sma_50":      safe_float(row.get("SMA_50")),
            "ema_20":      safe_float(row.get("EMA_20")),
            "rsi":         safe_float(row.get("RSI")),
            "macd":        safe_float(row.get("MACD")),
            "macd_signal": safe_float(row.get("MACD_Signal")),
            "bb_high":     safe_float(row.get("BB_High")),
            "bb_low":      safe_float(row.get("BB_Low")),
        })

    return results


@router.post("/predict", response_model=StockPredictionResponse)
def predict_stock_price(request: StockPredictRequest):
    # Trading-day horizon map
    timeframe_map = {"5d": 5, "21d": 21, "63d": 63}
    days = timeframe_map[request.timeframe]

    data = MarketDataService.fetch_history(request.ticker, period="2y")
    if data is None or data.empty:
        raise HTTPException(
            status_code=404, detail=f"No data found for {request.ticker}"
        )

    try:
        result = run_prediction(
            data=data,
            ticker=request.ticker,
            days=days,
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
        )
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}")

    # Generate trading-day dates for each forecast step
    last_date    = data.index[-1]
    pred_dates   = _next_trading_days(last_date, days)

    prediction_points = [
        PredictionPoint(
            date     = pred_dates[i].strftime("%Y-%m-%d"),
            price    = float(result.median[i]),
            lower_80 = float(result.lower_80[i]),
            upper_80 = float(result.upper_80[i]),
            lower_90 = float(result.lower_90[i]),
            upper_90 = float(result.upper_90[i]),
            lower_95 = float(result.lower_95[i]),
            upper_95 = float(result.upper_95[i]),
        )
        for i in range(days)
    ]

    return StockPredictionResponse(
        ticker               = request.ticker,
        current_price        = result.current_price,
        horizon_trading_days = days,
        predictions          = prediction_points,
        regime               = RegimeInfo(
            current    = result.regime,
            confidence = result.regime_confidence,
        ),
        empirical_coverage   = result.empirical_coverage,
        coherence            = CoherenceInfo(
            score        = result.coherence_score,
            assessment   = result.coherence_assessment,
            risk_factors = result.risk_factors,
            available    = result.llm_available,
        ),
        scenarios            = ScenarioAnalysis(**result.scenarios),
        risk_metrics         = RiskMetrics(**result.risk_metrics),
        n_samples            = result.n_samples,
    )
