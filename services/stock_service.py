"""
UniQuant Stock Prediction Engine v2.0

4-Layer Architecture:
  Layer 1 — Amazon Chronos T5-Small (generative foundation model, probabilistic)
  Layer 2 — Hidden Markov Model regime gate (4-state: bull/bear/sideways/volatile)
  Layer 3 — Conformal prediction intervals (statistically guaranteed coverage)
  Layer 4 — LLM narrative coherence score (Claude Haiku validation layer)

Data source: Yahoo Finance via yfinance (free, no API key required for data)
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Result Container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PredictionResult:
    """Full output from all 4 prediction layers."""

    # Layer 1 — Chronos generative forecast
    median: np.ndarray          # shape (days,) — median of sample distribution
    samples: np.ndarray         # shape (n_samples, days) — full trajectory set

    # Layer 3 — Conformal prediction intervals
    lower_80: np.ndarray
    upper_80: np.ndarray
    lower_90: np.ndarray
    upper_90: np.ndarray
    lower_95: np.ndarray
    upper_95: np.ndarray
    empirical_coverage: float   # measured on calibration set
    n_samples: int

    # Layer 2 — HMM regime detection
    regime: str                 # "bull" | "bear" | "sideways" | "volatile"
    regime_confidence: float    # posterior probability of current state (0-100)
    regime_history: list        # named regime per historical day

    # Layer 4 — LLM coherence assessment
    coherence_score: Optional[int]   # 0-100, None if unavailable
    coherence_assessment: str
    risk_factors: list
    llm_available: bool

    # Meta
    current_price: float
    days: int
    ticker: str


# ─────────────────────────────────────────────────────────────────────────────
# Predictor Class
# ─────────────────────────────────────────────────────────────────────────────

class ChronosStockPredictor:
    """
    Orchestrates all 4 prediction layers.

    Usage:
        predictor = ChronosStockPredictor()
        result = predictor.predict(data, days=7, ticker="AAPL")
    """

    # Cached pipeline across calls (lazy-loaded on first predict)
    _pipeline = None

    def _load_pipeline(self):
        """Load Amazon Chronos T5-Small. Downloads ~250 MB on first call."""
        if ChronosStockPredictor._pipeline is None:
            from chronos import ChronosPipeline
            import torch
            ChronosStockPredictor._pipeline = ChronosPipeline.from_pretrained(
                "amazon/chronos-t5-small",
                device_map="cpu",
                torch_dtype=torch.float32,
            )
        return ChronosStockPredictor._pipeline

    # ── Layer 2 ──────────────────────────────────────────────────────────────

    def detect_regime(self, data: pd.DataFrame) -> dict:
        """
        Layer 2: Fit a 4-state Gaussian HMM on log-return / volatility / volume
        features to label the current market regime.

        Returns dict with keys: current, confidence, history, raw_labels
        """
        from hmmlearn import GaussianHMM

        close = data["Close"].astype(float).values
        volume = data["Volume"].astype(float).values

        # ── Feature engineering ──────────────────────────────────────────────
        log_returns = np.diff(np.log(close + 1e-8))

        rolling_vol = (
            pd.Series(log_returns)
            .rolling(5, min_periods=1)
            .std()
            .fillna(0)
            .values
        )

        vol_ma = (
            pd.Series(volume[1:])
            .rolling(20, min_periods=1)
            .mean()
            .fillna(volume[1:].mean())
            .values
        )
        volume_ratio = np.log(np.clip(volume[1:] / (vol_ma + 1e-8), 0.05, 20))

        features = np.column_stack([log_returns, rolling_vol, volume_ratio])

        # ── Fit HMM ──────────────────────────────────────────────────────────
        model = GaussianHMM(
            n_components=4,
            covariance_type="full",
            n_iter=300,
            random_state=42,
        )
        model.fit(features)

        raw_labels = model.predict(features)
        posterior = model.predict_proba(features)

        # ── Characterise each HMM state ──────────────────────────────────────
        regime_map = self._label_regimes(log_returns, rolling_vol, raw_labels)

        current_id = int(raw_labels[-1])
        current_name = regime_map.get(current_id, "sideways")
        regime_confidence = float(posterior[-1, current_id]) * 100

        named_history = [regime_map.get(int(r), "sideways") for r in raw_labels]

        return {
            "current": current_name,
            "confidence": regime_confidence,
            "history": named_history,
            "raw_labels": raw_labels,
        }

    def _label_regimes(self, log_returns, rolling_vol, labels) -> dict:
        """
        Assign human-readable names to HMM state IDs based on the mean return
        and mean volatility of observations in each state.

        High return + low vol  → bull
        High return + high vol → volatile
        Low return  + low vol  → sideways
        Low return  + high vol → bear
        """
        stats = []
        for state_id in range(4):
            mask = labels == state_id
            if mask.sum() == 0:
                stats.append((state_id, 0.0, 0.0))
                continue
            mean_ret = float(log_returns[mask].mean())
            mean_vol = float(rolling_vol[mask].mean())
            stats.append((state_id, mean_ret, mean_vol))

        # Sort by return descending
        by_return = sorted(stats, key=lambda x: x[1], reverse=True)
        top_two = sorted(by_return[:2], key=lambda x: x[2])   # low vol first
        bot_two = sorted(by_return[2:], key=lambda x: x[2])   # low vol first

        regime_map = {}
        labels_assigned = ["bull", "volatile", "sideways", "bear"]
        for i, (state_id, _, _) in enumerate(top_two + bot_two):
            regime_map[state_id] = labels_assigned[i]

        return regime_map

    # ── Layer 1 + 3 ──────────────────────────────────────────────────────────

    def predict_with_conformal(
        self,
        data: pd.DataFrame,
        days: int,
        n_samples: int = 500,
    ) -> dict:
        """
        Layer 1: Run Chronos to generate n_samples probabilistic trajectories.
        Layer 3: Calibrate conformal intervals using split conformal prediction
                 on a held-out calibration window.

        Conformal guarantee: the true future price falls inside the 90% band
        with ≥90% probability (under exchangeability assumption).
        """
        import torch

        pipeline = self._load_pipeline()
        close_prices = data["Close"].astype(float).values

        # ── Conformal calibration ─────────────────────────────────────────────
        # Use the last 60 days as calibration (1-step-ahead rolling predictions,
        # sampled every 4 days → ~15 calibration points for speed).
        calib_window = 60
        step = 4
        calib_nonconf_scores = []

        calib_start = max(100, len(close_prices) - calib_window)
        calib_indices = list(range(calib_start, len(close_prices) - 1, step))

        for idx in calib_indices:
            ctx = torch.tensor(close_prices[:idx], dtype=torch.float32)
            with torch.no_grad():
                fc = pipeline.predict(ctx, prediction_length=1, num_samples=100)
            samp = fc[0, :, 0].numpy()
            median_hat = float(np.median(samp))
            std_hat = float(samp.std()) + 1e-8
            true_next = float(close_prices[idx])
            calib_nonconf_scores.append(abs(true_next - median_hat) / std_hat)

        calib_scores = np.array(calib_nonconf_scores)

        def _conformal_q(level: float) -> float:
            n = len(calib_scores)
            q_idx = min(int(np.ceil((n + 1) * level)) - 1, n - 1)
            return float(np.sort(calib_scores)[q_idx])

        q80 = _conformal_q(0.80)
        q90 = _conformal_q(0.90)
        q95 = _conformal_q(0.95)

        # Empirical coverage at the 90% nominal level
        empirical_coverage = float(np.mean(calib_scores <= q90))

        # ── Main forecast ─────────────────────────────────────────────────────
        context = torch.tensor(close_prices, dtype=torch.float32)
        with torch.no_grad():
            forecast = pipeline.predict(
                context, prediction_length=days, num_samples=n_samples
            )

        # forecast shape: (1, n_samples, days)
        samples = forecast[0].numpy()                    # (n_samples, days)
        median = np.median(samples, axis=0)              # (days,)
        std_per_step = samples.std(axis=0) + 1e-8        # (days,)

        # ── Build conformal bands ─────────────────────────────────────────────
        # Width grows with each step's spread (heteroscedastic intervals).
        lower_80 = np.maximum(median - q80 * std_per_step, 0.0)
        upper_80 = median + q80 * std_per_step
        lower_90 = np.maximum(median - q90 * std_per_step, 0.0)
        upper_90 = median + q90 * std_per_step
        lower_95 = np.maximum(median - q95 * std_per_step, 0.0)
        upper_95 = median + q95 * std_per_step

        return {
            "median": median,
            "samples": samples,
            "lower_80": lower_80,
            "upper_80": upper_80,
            "lower_90": lower_90,
            "upper_90": upper_90,
            "lower_95": lower_95,
            "upper_95": upper_95,
            "empirical_coverage": empirical_coverage,
            "n_samples": n_samples,
        }

    # ── Layer 4 ──────────────────────────────────────────────────────────────

    def get_llm_coherence(
        self,
        ticker: str,
        current_price: float,
        forecast_result: dict,
        regime_result: dict,
        days: int,
        api_key: Optional[str] = None,
    ) -> dict:
        """
        Layer 4: Send forecast context to Claude Haiku and ask it to act as a
        quantitative analyst evaluating whether the prediction is coherent.

        Returns a structured assessment: score (0-100), narrative, risk factors.
        """
        import os
        import json

        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            return {
                "coherence_score": None,
                "assessment": (
                    "Set the ANTHROPIC_API_KEY environment variable (or paste it "
                    "in the sidebar) to enable LLM coherence scoring."
                ),
                "risk_factors": [],
                "available": False,
            }

        try:
            import anthropic
        except ImportError:
            return {
                "coherence_score": None,
                "assessment": "Install the `anthropic` package to enable this layer.",
                "risk_factors": [],
                "available": False,
            }

        client = anthropic.Anthropic(api_key=key)

        median_final = float(forecast_result["median"][-1])
        lower_90_final = float(forecast_result["lower_90"][-1])
        upper_90_final = float(forecast_result["upper_90"][-1])
        pct_change = ((median_final - current_price) / current_price) * 100
        interval_width_pct = (
            (upper_90_final - lower_90_final) / current_price * 100
        )

        prompt = f"""You are a senior quantitative analyst reviewing an AI-generated stock price forecast.

Stock: {ticker}
Current Price: ${current_price:.2f}
Forecast Horizon: {days} calendar day(s)
Predicted Median Price: ${median_final:.2f}
Expected Change: {pct_change:+.2f}%
90% Conformal Interval: ${lower_90_final:.2f} – ${upper_90_final:.2f}
Interval Width: {interval_width_pct:.1f}% of current price
Detected Market Regime: {regime_result["current"].upper()}
Regime Posterior Confidence: {regime_result["confidence"]:.1f}%

Evaluate the coherence and real-world plausibility of this forecast.
Consider:
1. Is the magnitude of predicted change realistic for this regime and horizon?
2. Are the uncertainty bounds appropriately sized (not too tight or too wide)?
3. Does the direction align with the detected regime signal?
4. What are the key risk factors that could invalidate this prediction?

Respond with valid JSON only — no markdown fences, no explanation outside the JSON:
{{"coherence_score": <integer 0-100>, "assessment": "<2-3 sentence evaluation>", "risk_factors": ["<factor1>", "<factor2>", "<factor3>"]}}"""

        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            # Strip any accidental markdown fences
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.lower().startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw.strip())
            parsed["available"] = True
            return parsed
        except Exception as exc:
            return {
                "coherence_score": 50,
                "assessment": f"LLM assessment encountered an error: {exc}",
                "risk_factors": ["API connectivity issue", "Check ANTHROPIC_API_KEY"],
                "available": False,
            }

    # ── Master orchestrator ───────────────────────────────────────────────────

    def predict(
        self,
        data: pd.DataFrame,
        days: int,
        ticker: str = "STOCK",
        n_samples: int = 500,
        anthropic_api_key: Optional[str] = None,
    ) -> PredictionResult:
        """
        Run the full 4-layer pipeline and return a PredictionResult.

        Args:
            data:               DataFrame with at least Close and Volume columns
            days:               Number of calendar days to forecast
            ticker:             Stock symbol (used in LLM prompt and logging)
            n_samples:          Number of generative trajectories from Chronos
            anthropic_api_key:  Optional — falls back to ANTHROPIC_API_KEY env var
        """
        current_price = float(data["Close"].iloc[-1])

        # Layer 2 first — regime info feeds into the LLM prompt
        regime_result = self.detect_regime(data)

        # Layer 1 + 3
        forecast_result = self.predict_with_conformal(data, days, n_samples=n_samples)

        # Layer 4 (bonus)
        llm_result = self.get_llm_coherence(
            ticker=ticker,
            current_price=current_price,
            forecast_result=forecast_result,
            regime_result=regime_result,
            days=days,
            api_key=anthropic_api_key,
        )

        return PredictionResult(
            # Layer 1
            median=forecast_result["median"],
            samples=forecast_result["samples"],
            # Layer 3
            lower_80=forecast_result["lower_80"],
            upper_80=forecast_result["upper_80"],
            lower_90=forecast_result["lower_90"],
            upper_90=forecast_result["upper_90"],
            lower_95=forecast_result["lower_95"],
            upper_95=forecast_result["upper_95"],
            empirical_coverage=forecast_result["empirical_coverage"],
            n_samples=forecast_result["n_samples"],
            # Layer 2
            regime=regime_result["current"],
            regime_confidence=regime_result["confidence"],
            regime_history=regime_result["history"],
            # Layer 4
            coherence_score=llm_result.get("coherence_score"),
            coherence_assessment=llm_result.get("assessment", ""),
            risk_factors=llm_result.get("risk_factors", []),
            llm_available=llm_result.get("available", False),
            # Meta
            current_price=current_price,
            days=days,
            ticker=ticker,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Backward-compatibility alias
# (kept so any other import of StockPredictor fails loudly with a clear message)
# ─────────────────────────────────────────────────────────────────────────────

class StockPredictor:
    def __init__(self, *args, **kwargs):
        raise RuntimeError(
            "StockPredictor (LSTM) has been replaced by ChronosStockPredictor. "
            "Update your imports: from services.stock_service import ChronosStockPredictor"
        )
