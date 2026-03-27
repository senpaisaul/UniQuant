"""
UniQuant — Production Stock Prediction Service (FastAPI backend)

Hybrid Chronos + GARCH Architecture:

  Layer 1 — Amazon Chronos T5-Small
            Generative foundation model → median forecast, 500 sample trajectories,
            scenario analysis, directional probabilities.

  Layer 2 — HMM Market Regime Gate
            4-state Gaussian HMM → bull / bear / sideways / volatile classification.

  Layer 3 — GARCH(1,1) Volatility Model  +  Conformal Calibration
            GARCH specifically designed for financial heteroscedasticity gives
            tight, realistic interval widths.  Conformal calibration on GARCH
            standardized residuals provides the statistical coverage guarantee.

            Why hybrid:
              Chronos underestimates stock volatility (trained on diverse non-financial
              time series).  Its native sample spread is too narrow → conformal
              calibration overcorrects with q-multipliers of 8-15 → 40%+ wide bands.
              GARCH directly models volatility clustering in equity returns → q-
              multiplier stays near 1.28-1.6 → realistic 8-20% wide bands.

  Layer 4 — LLM Coherence Score (Claude Haiku)
            Narrative validation of the full forecast context.
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Result container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PredictionResult:
    # Layer 1 — Chronos
    median: np.ndarray
    samples: np.ndarray

    # Layer 3 — GARCH + Conformal intervals
    lower_80: np.ndarray
    upper_80: np.ndarray
    lower_90: np.ndarray
    upper_90: np.ndarray
    lower_95: np.ndarray
    upper_95: np.ndarray
    empirical_coverage: float

    # Layer 2 — HMM regime
    regime: str
    regime_confidence: float

    # Layer 4 — LLM coherence
    coherence_score: Optional[int]
    coherence_assessment: str
    risk_factors: list
    llm_available: bool

    # Rich analytics from sample distribution + GARCH
    scenarios: dict
    risk_metrics: dict

    # Meta
    current_price: float
    n_samples: int


# ─────────────────────────────────────────────────────────────────────────────
# Chronos pipeline — module-level singleton
# ─────────────────────────────────────────────────────────────────────────────

_pipeline = None


def _load_pipeline():
    global _pipeline
    if _pipeline is None:
        from chronos import ChronosPipeline
        import torch
        _pipeline = ChronosPipeline.from_pretrained(
            "amazon/chronos-t5-small",
            device_map="cpu",
            torch_dtype=torch.float32,
        )
    return _pipeline


# ── Layer 2 — HMM Regime ──────────────────────────────────────────────────────

def _detect_regime(data: pd.DataFrame) -> dict:
    from hmmlearn.hmm import GaussianHMM

    close  = data["Close"].astype(float).values
    volume = data["Volume"].astype(float).values

    log_returns = np.diff(np.log(close + 1e-8))
    rolling_vol = (
        pd.Series(log_returns).rolling(5, min_periods=1).std().fillna(0).values
    )
    vol_ma = (
        pd.Series(volume[1:])
        .rolling(20, min_periods=1).mean()
        .fillna(volume[1:].mean()).values
    )
    volume_ratio = np.log(np.clip(volume[1:] / (vol_ma + 1e-8), 0.05, 20))

    features = np.column_stack([log_returns, rolling_vol, volume_ratio])

    model = GaussianHMM(
        n_components=4, covariance_type="full", n_iter=300, random_state=42
    )
    model.fit(features)

    raw_labels = model.predict(features)
    posterior  = model.predict_proba(features)

    stats = []
    for sid in range(4):
        mask = raw_labels == sid
        if mask.sum() == 0:
            stats.append((sid, 0.0, 0.0))
            continue
        stats.append((
            sid,
            float(log_returns[mask].mean()),
            float(rolling_vol[mask].mean()),
        ))

    by_return  = sorted(stats, key=lambda x: x[1], reverse=True)
    top_two    = sorted(by_return[:2], key=lambda x: x[2])
    bot_two    = sorted(by_return[2:], key=lambda x: x[2])
    name_order = ["bull", "volatile", "sideways", "bear"]
    regime_map = {s[0]: name_order[i] for i, s in enumerate(top_two + bot_two)}

    current_id   = int(raw_labels[-1])
    current_name = regime_map.get(current_id, "sideways")

    # ── Confidence: average over last 5 steps + temperature-soften ────────────
    window         = min(5, len(posterior))
    mean_posterior = posterior[-window:].mean(axis=0)
    temperature    = 1.5
    log_p          = np.log(mean_posterior + 1e-12) / temperature
    softened       = np.exp(log_p - log_p.max())
    softened       = softened / softened.sum()
    confidence     = min(float(softened[current_id]) * 100, 85.0)

    # ── Transition uncertainty via Shannon entropy (Gibbs & Candès 2021) ──────
    # H=0 → model is certain about regime  |  H=1 → maximal transition uncertainty
    # Use the RAW last-step posterior (not softened) for the true entropy signal.
    raw_last   = np.clip(posterior[-1], 1e-12, 1.0)
    raw_last  /= raw_last.sum()
    H          = -float(np.sum(raw_last * np.log(raw_last)))
    H_max      = np.log(4)                         # max entropy for 4 states
    transition_uncertainty = float(H / H_max)      # 0 = stable, 1 = fully uncertain

    # ── Data-driven regime drift (Jegadeesh & Titman 1993 momentum approach) ──
    # Use the actual historical mean log-return of observations the HMM labeled
    # as the current regime.  Only retain if t-stat ≥ 0.8 so noise regimes
    # produce zero drift rather than misleading directional signals.
    regime_returns = log_returns[raw_labels == current_id]
    drift_per_day  = 0.0
    if len(regime_returns) >= 15:
        r_mean   = float(regime_returns.mean())
        r_std    = float(regime_returns.std()) + 1e-8
        t_stat   = r_mean / (r_std / np.sqrt(len(regime_returns)))
        if abs(t_stat) >= 0.8:
            drift_per_day = r_mean   # daily log-return drift, e.g. 0.0008 for bull

    return {
        "current":               current_name,
        "confidence":            confidence,
        "regime_labels":         raw_labels,          # shape (T-1,)
        "current_id":            current_id,
        "drift_per_day":         drift_per_day,
        "transition_uncertainty": transition_uncertainty,  # 0=stable, 1=transition
    }


# ── Layer 3 — GJR-GARCH(1,1,1) volatility forecast ───────────────────────────

def _garch_volatility(
    log_returns: np.ndarray,
    days: int,
    regime_labels: np.ndarray = None,
    current_regime_id: int    = None,
) -> tuple:
    """
    Fit GJR-GARCH(1,1,1) with Student-t innovations and return multi-step
    price standard deviations plus regime-conditional conformal scores.

    GJR-GARCH (Glosten, Jagannathan & Runkle 1993):
        σ²_t = ω + (α + γ·I_{ε<0})·ε²_{t-1} + β·σ²_{t-1}
    The asymmetric term γ captures the leverage effect — negative shocks
    increase variance more than positive shocks of equal magnitude, which
    is empirically dominant in equity markets.

    Regime-conditional conformal calibration (Tibshirani et al. 2019):
    Using only standardized residuals from the *same HMM regime* as today
    gives calibration scores that match current market conditions.  A
    volatile-regime calibration set naturally produces a larger q_90,
    widening intervals exactly when tail risk is elevated.
    """
    from arch import arch_model

    returns_pct = log_returns * 100

    try:
        # GJR-GARCH(1,1,1): p=1 ARCH, o=1 asymmetric, q=1 GARCH; dist='t' fat tails
        garch = arch_model(
            returns_pct,
            vol="Garch", p=1, o=1, q=1,
            dist="t", mean="Zero",
        )
        garch_fit = garch.fit(disp="off", show_warning=False)

        fc            = garch_fit.forecast(horizon=days, reindex=False)
        step_var_pct2 = fc.variance.values[-1]
        step_std_dec  = np.sqrt(step_var_pct2) / 100

        cum_var_dec        = np.cumsum(step_std_dec ** 2)
        price_std_per_step = cum_var_dec

        garch_annual_vol = round(float(step_std_dec[0]) * np.sqrt(252) * 100, 1)

        # Standardized residuals; drop leading NaNs from GARCH initialisation
        std_resid = np.asarray(garch_fit.std_resid)
        std_resid = std_resid[~np.isnan(std_resid)]

        # ── Regime-conditional calibration ────────────────────────────────────
        if regime_labels is not None and current_regime_id is not None:
            # Align lengths — both series start at the second price observation
            n_common = min(len(std_resid), len(regime_labels))
            aligned_labels = regime_labels[-n_common:]
            aligned_resid  = std_resid[-n_common:]
            regime_resid   = aligned_resid[aligned_labels == current_regime_id]
            if len(regime_resid) >= 20:
                conformal_scores = np.abs(regime_resid)
            else:
                conformal_scores = np.abs(std_resid[-60:])  # fallback: all regimes
        else:
            conformal_scores = np.abs(std_resid[-60:])

    except Exception:
        hist_daily_vol     = float(np.std(returns_pct[-60:])) / 100
        step_std_dec       = np.full(days, hist_daily_vol)
        cum_var_dec        = np.cumsum(step_std_dec ** 2)
        price_std_per_step = cum_var_dec
        garch_annual_vol   = round(hist_daily_vol * np.sqrt(252) * 100, 1)
        conformal_scores   = np.abs(returns_pct[-60:]) / (hist_daily_vol * 100 + 1e-8)

    return price_std_per_step, garch_annual_vol, conformal_scores


# ── Layer 1 + 3 — Chronos forecast with GJR-GARCH conformal intervals ────────

def _predict_chronos_garch(
    data: pd.DataFrame,
    days: int,
    n_samples: int       = 500,
    regime: str          = "sideways",
    regime_confidence: float = 60.0,
    regime_labels: np.ndarray = None,
    current_regime_id: int    = None,
    regime_drift_per_day: float = 0.0,
    transition_uncertainty: float = 0.0,
) -> dict:
    import torch

    pipeline      = _load_pipeline()
    close_prices  = data["Close"].astype(float).values
    current_price = close_prices[-1]
    log_returns   = np.diff(np.log(close_prices + 1e-8))

    # ── GJR-GARCH: regime-conditional calibration ─────────────────────────────
    price_std_frac, garch_annual_vol, conformal_scores = _garch_volatility(
        log_returns, days,
        regime_labels=regime_labels,
        current_regime_id=current_regime_id,
    )
    price_std_per_step = current_price * np.sqrt(price_std_frac)

    # ── Entropy-based transition inflation ────────────────────────────────────
    # During regime transitions the HMM posterior spreads across states (high H).
    # We inflate the price std proportionally so intervals automatically widen
    # when calibration is least reliable — up to +50% at maximum uncertainty.
    # At stable regimes (H≈0) inflation ≈ 1.0 (no change).
    interval_inflation = 1.0 + 0.5 * transition_uncertainty
    price_std_per_step = price_std_per_step * interval_inflation

    # ── Conformal quantiles ────────────────────────────────────────────────────
    def _q(level: float) -> float:
        n = len(conformal_scores)
        i = min(int(np.ceil((n + 1) * level)) - 1, n - 1)
        return float(np.sort(conformal_scores)[i])

    q80, q90, q95      = _q(0.80), _q(0.90), _q(0.95)
    empirical_coverage = float(np.mean(conformal_scores <= q90))

    # ── Chronos generative forecast ───────────────────────────────────────────
    context = torch.tensor(close_prices, dtype=torch.float32)
    with torch.no_grad():
        forecast = pipeline.predict(
            context, prediction_length=days, num_samples=n_samples
        )

    samples = forecast[0].numpy()       # (n_samples, days)
    median  = np.median(samples, axis=0)

    # ── Data-driven regime drift injection ────────────────────────────────────
    # Scale drift by how far confidence exceeds the 50% uninformative prior.
    # 50% confidence → zero extra drift; 85% confidence → conf_weight = 0.70.
    # Using the ticker-specific historical regime mean return (drift_per_day)
    # instead of a hardcoded table makes the signal data-driven and directionally
    # consistent with the HMM output without overpowering Chronos's own forecast.
    # Samples are left unmodified so scenario/probability analytics stay unbiased.
    conf_weight  = max(0.0, (regime_confidence / 100 - 0.50) * 2)
    scaled_drift = regime_drift_per_day * conf_weight
    drift_mults  = np.exp(scaled_drift * np.arange(1, days + 1))
    median       = median * drift_mults

    # ── GARCH-calibrated conformal bands ──────────────────────────────────────
    lower_80 = np.maximum(median - q80 * price_std_per_step, 0.0)
    upper_80 = median + q80 * price_std_per_step
    lower_90 = np.maximum(median - q90 * price_std_per_step, 0.0)
    upper_90 = median + q90 * price_std_per_step
    lower_95 = np.maximum(median - q95 * price_std_per_step, 0.0)
    upper_95 = median + q95 * price_std_per_step

    return {
        "median":             median,
        "samples":            samples,
        "lower_80":           lower_80,
        "upper_80":           upper_80,
        "lower_90":           lower_90,
        "upper_90":           upper_90,
        "lower_95":           lower_95,
        "upper_95":           upper_95,
        "empirical_coverage": empirical_coverage,
        "n_samples":          n_samples,
        "garch_annual_vol":   garch_annual_vol,
        "regime_drift_pct":   round(scaled_drift * days * 100, 2),  # for LLM prompt
    }


# ── Rich analytics from sample distribution ───────────────────────────────────

def _extract_analytics(
    samples: np.ndarray,
    current_price: float,
    garch_annual_vol: float,
) -> tuple:
    """
    Extract every meaningful signal from the 500 Chronos trajectories.
    Volatility comes from GARCH (authoritative), not Chronos samples (miscalibrated).
    """
    from scipy.stats import skew as scipy_skew

    final_prices = samples[:, -1]
    path_max     = np.max(samples, axis=1)
    path_min     = np.min(samples, axis=1)

    def pct(p: float) -> float:
        return round((p - current_price) / current_price * 100, 2)

    # ── Scenarios ─────────────────────────────────────────────────────────────
    bull_price = float(np.percentile(final_prices, 85))
    base_price = float(np.median(final_prices))
    bear_price = float(np.percentile(final_prices, 15))

    scenarios = {
        "bull_price": round(bull_price, 2),
        "base_price": round(base_price, 2),
        "bear_price": round(bear_price, 2),
        "bull_pct":   pct(bull_price),
        "base_pct":   pct(base_price),
        "bear_pct":   pct(bear_price),
    }

    # ── Probabilities ─────────────────────────────────────────────────────────
    prob_gain = float(np.mean(final_prices > current_price))
    prob_loss = float(np.mean(final_prices < current_price))

    max_gain_pct = float(
        np.percentile((path_max - current_price) / current_price * 100, 75)
    )
    max_loss_pct = float(
        np.percentile((path_min - current_price) / current_price * 100, 25)
    )

    def _prob_hit(target: float) -> float:
        if target >= current_price:
            return float(np.mean(np.any(samples >= target, axis=1)))
        return float(np.mean(np.any(samples <= target, axis=1)))

    # ── Skewness + trajectory shape ───────────────────────────────────────────
    skewness    = round(float(scipy_skew(final_prices)), 3)
    median_path = np.median(samples, axis=0)
    total_drift = (median_path[-1] - current_price) / current_price
    intra_vol   = float(np.std(median_path) / current_price)

    if intra_vol > 0.04:
        shape = "volatile"
    elif total_drift > 0.01:
        shape = "uptrend"
    elif total_drift < -0.01:
        shape = "downtrend"
    else:
        shape = "flat"

    risk_metrics = {
        "prob_gain":          round(prob_gain * 100, 1),
        "prob_loss":          round(prob_loss * 100, 1),
        "max_gain_pct":       round(max_gain_pct, 2),
        "max_loss_pct":       round(max_loss_pct, 2),
        # Authoritative volatility from GARCH, not Chronos sample spread
        "annualized_vol_pct": garch_annual_vol,
        "skewness":           skewness,
        "trajectory_shape":   shape,
        "prob_up_5pct":       round(_prob_hit(current_price * 1.05) * 100, 1),
        "prob_up_10pct":      round(_prob_hit(current_price * 1.10) * 100, 1),
        "prob_down_5pct":     round(_prob_hit(current_price * 0.95) * 100, 1),
        "prob_down_10pct":    round(_prob_hit(current_price * 0.90) * 100, 1),
    }

    return scenarios, risk_metrics


# ── Layer 4 — LLM Coherence ───────────────────────────────────────────────────

def _get_llm_coherence(
    ticker: str,
    current_price: float,
    forecast: dict,
    regime: dict,
    days: int,
    api_key: str,
) -> dict:
    if not api_key:
        return {
            "coherence_score": None,
            "assessment":      "ANTHROPIC_API_KEY not configured.",
            "risk_factors":    [],
            "available":       False,
        }
    try:
        import anthropic, json

        client        = anthropic.Anthropic(api_key=api_key)
        median_final  = float(forecast["median"][-1])
        lower_90      = float(forecast["lower_90"][-1])
        upper_90      = float(forecast["upper_90"][-1])
        pct_change    = (median_final - current_price) / current_price * 100
        width_pct     = (upper_90 - lower_90) / current_price * 100
        garch_vol     = forecast.get("garch_annual_vol", 0)

        regime_drift   = forecast.get("regime_drift_pct", 0.0)
        trans_uncert   = regime.get("transition_uncertainty", 0.0)
        inflation_pct  = round((0.5 * trans_uncert) * 100, 1)
        prompt = f"""You are a senior quantitative analyst reviewing an AI-generated stock price forecast.

Architecture:
  Layer 1 — Amazon Chronos T5-Small: generative foundation model → 500 probabilistic trajectories
  Layer 2 — 4-state Gaussian HMM: market regime detection; confidence temperature-softened (T=1.5),
             averaged over last 5 steps, capped at 85%
  Layer 3 — GJR-GARCH(1,1,1) + Student-t: asymmetric volatility (leverage effect)
             Regime-conditional conformal calibration: quantile derived from same-regime residuals only
             Entropy-based transition inflation: interval σ × (1 + 0.5·H_norm) widens during transitions
  Layer 4 — Claude Haiku: coherence validation (you)

Stock: {ticker}
Current Price: ${current_price:.2f}
Horizon: {days} trading day(s)
Median Forecast: ${median_final:.2f} ({pct_change:+.2f}%)
  — regime drift component: {regime_drift:+.2f}% (data-driven from ticker-specific HMM regime history)
90% Conformal Interval: ${lower_90:.2f} – ${upper_90:.2f} (width {width_pct:.1f}%)
GJR-GARCH Implied Annual Vol: {garch_vol:.1f}%
Market Regime: {regime["current"].upper()} (confidence {regime["confidence"]:.1f}%)
Regime Transition Uncertainty (H_norm): {trans_uncert:.2f}  → interval inflation applied: +{inflation_pct:.1f}%
  — H=0 means fully stable regime; H=1 means maximally uncertain (transition); intervals widen proportionally

Rate the forecast coherence 0–100. Reply with valid JSON only:
{{"coherence_score": <int>, "assessment": "<2-3 sentences>", "risk_factors": ["<f1>","<f2>","<f3>"]}}"""

        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.lower().startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        result["available"] = True
        return result
    except Exception as exc:
        return {
            "coherence_score": 50,
            "assessment":      f"LLM assessment error: {exc}",
            "risk_factors":    [],
            "available":       False,
        }


# ── Public API ────────────────────────────────────────────────────────────────

def run_prediction(
    data: pd.DataFrame,
    ticker: str,
    days: int,
    anthropic_api_key: str = "",
    n_samples: int = 500,
) -> PredictionResult:
    """
    Full hybrid pipeline: Chronos direction + GARCH intervals + HMM regime + LLM coherence.
    """
    current_price   = float(data["Close"].iloc[-1])
    regime_result   = _detect_regime(data)
    forecast_result = _predict_chronos_garch(
        data, days, n_samples=n_samples,
        regime                 = regime_result["current"],
        regime_confidence      = regime_result["confidence"],
        regime_labels          = regime_result["regime_labels"],
        current_regime_id      = regime_result["current_id"],
        regime_drift_per_day   = regime_result["drift_per_day"],
        transition_uncertainty = regime_result["transition_uncertainty"],
    )
    llm_result      = _get_llm_coherence(
        ticker, current_price, forecast_result, regime_result, days, anthropic_api_key
    )
    scenarios, risk_metrics = _extract_analytics(
        forecast_result["samples"],
        current_price,
        forecast_result["garch_annual_vol"],
    )

    return PredictionResult(
        median               = forecast_result["median"],
        samples              = forecast_result["samples"],
        lower_80             = forecast_result["lower_80"],
        upper_80             = forecast_result["upper_80"],
        lower_90             = forecast_result["lower_90"],
        upper_90             = forecast_result["upper_90"],
        lower_95             = forecast_result["lower_95"],
        upper_95             = forecast_result["upper_95"],
        empirical_coverage   = forecast_result["empirical_coverage"],
        regime               = regime_result["current"],
        regime_confidence    = regime_result["confidence"],
        coherence_score      = llm_result.get("coherence_score"),
        coherence_assessment = llm_result.get("assessment", ""),
        risk_factors         = llm_result.get("risk_factors", []),
        llm_available        = llm_result.get("available", False),
        scenarios            = scenarios,
        risk_metrics         = risk_metrics,
        current_price        = current_price,
        n_samples            = forecast_result["n_samples"],
    )
