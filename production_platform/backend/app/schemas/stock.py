from pydantic import BaseModel, Field
from typing import List, Optional


class StockHistoryRequest(BaseModel):
    ticker: str
    period: str = "1y"


class StockIndicator(BaseModel):
    date: str
    close: float
    volume: int
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    ema_20: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    bb_high: Optional[float] = None
    bb_low: Optional[float] = None


class StockPredictRequest(BaseModel):
    ticker: str
    # Trading-day horizons: 5 td ≈ 1 week | 21 td ≈ 1 month | 63 td ≈ 1 quarter
    timeframe: str = Field(..., pattern="^(5d|21d|63d)$")


# ── Prediction response ───────────────────────────────────────────────────────

class PredictionPoint(BaseModel):
    date: str
    price: float        # median forecast
    lower_80: float
    upper_80: float
    lower_90: float
    upper_90: float
    lower_95: float
    upper_95: float


class RegimeInfo(BaseModel):
    current: str        # "bull" | "bear" | "sideways" | "volatile"
    confidence: float   # 0-100


class CoherenceInfo(BaseModel):
    score: Optional[int] = None
    assessment: str = ""
    risk_factors: List[str] = []
    available: bool = False


class ScenarioAnalysis(BaseModel):
    """
    Bull / Base / Bear scenarios derived from the 85th / 50th / 15th
    percentiles of the 500 Chronos sample trajectories' final prices.
    """
    bull_price: float   # 85th percentile final price
    base_price: float   # median final price
    bear_price: float   # 15th percentile final price
    bull_pct: float     # % change from current — bull
    base_pct: float     # % change from current — base
    bear_pct: float     # % change from current — bear


class RiskMetrics(BaseModel):
    """
    Probability and risk statistics extracted from all 500 sample paths.
    """
    # Final-price probabilities
    prob_gain: float            # % of paths ending above current price
    prob_loss: float            # % of paths ending below current price

    # Path-level extremes (across entire trajectory, not just final step)
    max_gain_pct: float         # 75th pct of best-case gain across paths
    max_loss_pct: float         # 25th pct of worst-case loss (negative)

    # Market microstructure
    annualized_vol_pct: float   # annualized vol implied by sample spread
    skewness: float             # +ve = upside tail | -ve = downside tail
    trajectory_shape: str       # "uptrend" | "downtrend" | "flat" | "volatile"

    # Probability of hitting price targets at ANY point during the horizon
    prob_up_5pct: float         # P(price hits +5% at any step)
    prob_up_10pct: float        # P(price hits +10% at any step)
    prob_down_5pct: float       # P(price hits -5% at any step)
    prob_down_10pct: float      # P(price hits -10% at any step)


class StockPredictionResponse(BaseModel):
    ticker: str
    current_price: float
    horizon_trading_days: int

    # Layer 1 — Chronos probabilistic forecast (per trading day)
    predictions: List[PredictionPoint]

    # Layer 2 — HMM regime
    regime: RegimeInfo

    # Layer 3 — Conformal coverage
    empirical_coverage: float

    # Layer 4 — LLM coherence
    coherence: CoherenceInfo

    # Rich analytics from 500 sample trajectories
    scenarios: ScenarioAnalysis
    risk_metrics: RiskMetrics

    # Meta
    n_samples: int
    model: str = "amazon/chronos-t5-small"
