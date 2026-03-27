import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from services.stock_service import ChronosStockPredictor, PredictionResult
from .session_log import log_activity


# ─────────────────────────────────────────────────────────────────────────────
# Cache the predictor so Chronos is loaded once per Streamlit session
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _get_predictor() -> ChronosStockPredictor:
    return ChronosStockPredictor()


# ─────────────────────────────────────────────────────────────────────────────
# Regime helpers
# ─────────────────────────────────────────────────────────────────────────────

_REGIME_CONFIG = {
    "bull":     {"color": "#00c853", "icon": "🟢", "label": "BULL",     "desc": "Positive momentum, low volatility"},
    "bear":     {"color": "#f44336", "icon": "🔴", "label": "BEAR",     "desc": "Negative momentum, elevated volatility"},
    "sideways": {"color": "#ffa726", "icon": "🟡", "label": "SIDEWAYS", "desc": "Range-bound, indecisive price action"},
    "volatile": {"color": "#ab47bc", "icon": "🟣", "label": "VOLATILE", "desc": "High uncertainty, large swings expected"},
}


def _regime_badge(regime: str, confidence: float) -> str:
    cfg = _REGIME_CONFIG.get(regime, _REGIME_CONFIG["sideways"])
    return (
        f"<div style='"
        f"display:inline-block;padding:6px 18px;border-radius:20px;"
        f"background:{cfg['color']}22;border:1.5px solid {cfg['color']};"
        f"color:{cfg['color']};font-weight:700;font-size:1.05rem;letter-spacing:1px;"
        f"'>{cfg['icon']} {cfg['label']} &nbsp; <span style='font-weight:400;font-size:0.88rem;opacity:0.85'>"
        f"{confidence:.1f}% confidence</span></div>"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Chart builders
# ─────────────────────────────────────────────────────────────────────────────

def _build_fan_chart(
    data: pd.DataFrame,
    result: PredictionResult,
    ticker: str,
    timeframe: str,
) -> go.Figure:
    """
    Probability fan chart:
      - Historical prices (last 90 days)
      - 50 sample trajectories (thin, transparent)
      - Conformal bands: 95 / 90 / 80 %
      - Median forecast line
    """
    historical = data.tail(90)
    last_date = data.index[-1]

    pred_dates = pd.date_range(
        start=last_date + timedelta(days=1), periods=result.days, freq="D"
    )

    fig = go.Figure()

    # ── Historical prices ────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=historical.index,
        y=historical["Close"],
        name="Historical Price",
        line=dict(color="#00d4ff", width=2),
        hovertemplate="$%{y:.2f}<extra>Historical</extra>",
    ))

    # ── Sample trajectories (50 of n_samples) ────────────────────────────────
    rng = np.random.default_rng(seed=0)
    sample_idx = rng.choice(result.n_samples, size=min(50, result.n_samples), replace=False)
    for i, idx in enumerate(sample_idx):
        fig.add_trace(go.Scatter(
            x=pred_dates,
            y=result.samples[idx],
            mode="lines",
            line=dict(color="rgba(255,200,80,0.07)", width=1),
            showlegend=(i == 0),
            name="Sample Trajectories" if i == 0 else "",
            hoverinfo="skip",
        ))

    # ── 95% conformal band ───────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=list(pred_dates) + list(pred_dates[::-1]),
        y=list(result.upper_95) + list(result.lower_95[::-1]),
        fill="toself",
        fillcolor="rgba(255,165,0,0.08)",
        line=dict(color="rgba(0,0,0,0)"),
        name="95% Conformal Band",
        hoverinfo="skip",
    ))

    # ── 90% conformal band ───────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=list(pred_dates) + list(pred_dates[::-1]),
        y=list(result.upper_90) + list(result.lower_90[::-1]),
        fill="toself",
        fillcolor="rgba(255,165,0,0.14)",
        line=dict(color="rgba(0,0,0,0)"),
        name="90% Conformal Band",
        hoverinfo="skip",
    ))

    # ── 80% conformal band ───────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=list(pred_dates) + list(pred_dates[::-1]),
        y=list(result.upper_80) + list(result.lower_80[::-1]),
        fill="toself",
        fillcolor="rgba(255,165,0,0.22)",
        line=dict(color="rgba(0,0,0,0)"),
        name="80% Conformal Band",
        hoverinfo="skip",
    ))

    # ── Median forecast ───────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=pred_dates,
        y=result.median,
        name="Median Forecast",
        line=dict(color="#ff8c00", width=3),
        hovertemplate="$%{y:.2f}<extra>Median Forecast</extra>",
    ))

    # ── "Now" divider ─────────────────────────────────────────────────────────
    fig.add_vline(
        x=last_date.timestamp() * 1000,
        line_dash="dot",
        line_color="rgba(255,255,255,0.35)",
        annotation_text="  Now",
        annotation_font_color="rgba(255,255,255,0.55)",
    )

    fig.update_layout(
        title=dict(
            text=f"{ticker} — {timeframe} Probabilistic Forecast (Chronos + Conformal)",
            font=dict(size=15),
        ),
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        height=520,
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11),
        ),
        margin=dict(t=80),
    )
    return fig


def _build_regime_timeline(regime_history: list, data: pd.DataFrame) -> go.Figure:
    """Compact timeline of regime changes over the historical window."""
    colour_map = {
        "bull":     "#00c853",
        "bear":     "#f44336",
        "sideways": "#ffa726",
        "volatile": "#ab47bc",
    }
    # HMM operates on diff(log(close)) so history length = len(data) - 1
    dates = data.index[1:]
    n = min(len(dates), len(regime_history))
    dates = dates[-n:]
    history = regime_history[-n:]

    numeric = [list(colour_map.keys()).index(r) for r in history]
    colours = [colour_map[r] for r in history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=numeric,
        mode="markers",
        marker=dict(color=colours, size=4, symbol="square"),
        hovertemplate="%{text}<br>%{x}<extra></extra>",
        text=history,
        showlegend=False,
    ))
    fig.update_layout(
        height=90,
        margin=dict(t=10, b=10, l=0, r=0),
        template="plotly_dark",
        xaxis=dict(showgrid=False),
        yaxis=dict(
            tickvals=[0, 1, 2, 3],
            ticktext=["bull", "bear", "sideways", "volatile"],
            showgrid=False,
            tickfont=dict(size=9),
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _build_coherence_gauge(score: int) -> go.Figure:
    """Gauge chart for LLM coherence score."""
    if score >= 75:
        color = "#00c853"
    elif score >= 50:
        color = "#ffa726"
    else:
        color = "#f44336"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": "Coherence Score", "font": {"size": 14}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "rgba(255,255,255,0.05)",
            "steps": [
                {"range": [0,   40], "color": "rgba(244,67,54,0.15)"},
                {"range": [40,  70], "color": "rgba(255,167,38,0.15)"},
                {"range": [70, 100], "color": "rgba(0,200,83,0.15)"},
            ],
            "threshold": {
                "line": {"color": color, "width": 3},
                "thickness": 0.8,
                "value": score,
            },
        },
        number={"suffix": "/100", "font": {"size": 28, "color": color}},
    ))
    fig.update_layout(
        height=220,
        margin=dict(t=30, b=10, l=20, r=20),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Main page entry point
# ─────────────────────────────────────────────────────────────────────────────

def show(data: pd.DataFrame, ticker: str):
    st.header(f"Generative AI Price Prediction — {ticker}")

    # ── Architecture info banner ──────────────────────────────────────────────
    with st.expander("Model Architecture — 4-Layer Generative AI System", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
**Layer 1 — Amazon Chronos T5-Small**
A transformer-based *generative* foundation model pre-trained on 700 B+
time-series observations. Outputs 500 probabilistic trajectories instead of
a single point estimate — making it a true generative AI forecaster.

**Layer 2 — HMM Market Regime Gate**
A 4-state Gaussian HMM labels the current market as bull / bear / sideways /
volatile. The detected regime is fed into the LLM prompt and informs how
uncertainty should be interpreted.
""")
        with col2:
            st.markdown("""
**Layer 3 — Conformal Prediction Intervals**
Split conformal prediction on a 60-day held-out calibration window gives
*statistically guaranteed* coverage: the true price falls inside the 90%
band with ≥90% empirical probability — not a heuristic ±σ estimate.

**Layer 4 — LLM Coherence Assessment (Claude Haiku)**
The forecast summary is sent to Claude Haiku which acts as a quantitative
analyst. It returns a 0–100 coherence score, a narrative assessment, and
the top 3 risk factors that could invalidate the prediction.
""")

    # ── API key input (sidebar) ───────────────────────────────────────────────
    with st.sidebar:
        st.markdown("---")
        st.markdown("**Layer 4 — LLM Coherence**")
        anthropic_key = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-...",
            key="anthropic_api_key_input",
            help="Required for the LLM coherence layer (Claude Haiku). "
                 "Leave blank to skip Layer 4.",
        )

    # ── Controls ──────────────────────────────────────────────────────────────
    col1, col2 = st.columns([3, 1])
    with col1:
        timeframe = st.selectbox(
            "Prediction Timeframe",
            ["1 Day", "1 Week", "1 Month"],
            index=0,
            key="stock_pred_timeframe",
        )
    with col2:
        st.markdown("<div style='margin-top:32px'></div>", unsafe_allow_html=True)
        if st.button(
            "Generate Prediction",
            type="primary",
            use_container_width=True,
            key="stock_btn_predict",
        ):
            st.session_state.stock_generate_prediction = True
            st.session_state.stock_pred_result = None  # reset on new run

    days_map = {"1 Day": 1, "1 Week": 7, "1 Month": 30}
    days = days_map[timeframe]

    # ── Run prediction ────────────────────────────────────────────────────────
    if st.session_state.get("stock_generate_prediction", False):

        # Use cached result if timeframe hasn't changed
        cached = st.session_state.get("stock_pred_result")
        if cached and cached.days == days and cached.ticker == ticker:
            result = cached
        else:
            progress_bar = st.progress(0, text="Initialising...")
            status_text = st.empty()

            try:
                predictor = _get_predictor()

                status_text.markdown("**Step 1 / 4** — Detecting market regime (HMM)...")
                progress_bar.progress(10, text="Detecting market regime...")
                regime_result = predictor.detect_regime(data)
                progress_bar.progress(25, text="Regime detected.")

                status_text.markdown("**Step 2 / 4** — Loading Chronos foundation model...")
                progress_bar.progress(30, text="Loading Chronos T5-Small...")
                predictor._load_pipeline()
                progress_bar.progress(45, text="Model ready.")

                status_text.markdown("**Step 3 / 4** — Calibrating conformal intervals...")
                progress_bar.progress(50, text="Running conformal calibration (~15 rollouts)...")
                forecast_result = predictor.predict_with_conformal(data, days)
                progress_bar.progress(80, text="Forecast generated.")

                status_text.markdown("**Step 4 / 4** — LLM coherence assessment (Claude Haiku)...")
                progress_bar.progress(85, text="Querying Claude Haiku...")
                llm_result = predictor.get_llm_coherence(
                    ticker=ticker,
                    current_price=float(data["Close"].iloc[-1]),
                    forecast_result=forecast_result,
                    regime_result=regime_result,
                    days=days,
                    api_key=anthropic_key or None,
                )
                progress_bar.progress(100, text="Done.")
                status_text.empty()
                progress_bar.empty()

                # Assemble result manually (avoid double-running layers)
                import dataclasses
                result = PredictionResult(
                    median=forecast_result["median"],
                    samples=forecast_result["samples"],
                    lower_80=forecast_result["lower_80"],
                    upper_80=forecast_result["upper_80"],
                    lower_90=forecast_result["lower_90"],
                    upper_90=forecast_result["upper_90"],
                    lower_95=forecast_result["lower_95"],
                    upper_95=forecast_result["upper_95"],
                    empirical_coverage=forecast_result["empirical_coverage"],
                    n_samples=forecast_result["n_samples"],
                    regime=regime_result["current"],
                    regime_confidence=regime_result["confidence"],
                    regime_history=regime_result["history"],
                    coherence_score=llm_result.get("coherence_score"),
                    coherence_assessment=llm_result.get("assessment", ""),
                    risk_factors=llm_result.get("risk_factors", []),
                    llm_available=llm_result.get("available", False),
                    current_price=float(data["Close"].iloc[-1]),
                    days=days,
                    ticker=ticker,
                )

                st.session_state.stock_pred_result = result

                # Log to session log
                log_activity(
                    activity_type="Prediction",
                    ticker=ticker,
                    timeframe=timeframe,
                    current_price=result.current_price,
                    predicted_price=float(result.median[-1]),
                    model_confidence=result.coherence_score or 0,
                    regime=result.regime,
                    regime_confidence=result.regime_confidence,
                    coherence_score=result.coherence_score,
                    conformal_coverage=f"{result.empirical_coverage*100:.1f}%",
                    lower_90=float(result.lower_90[-1]),
                    upper_90=float(result.upper_90[-1]),
                )
                st.toast(f"Prediction logged for {ticker}", icon="✅")

            except Exception as exc:
                progress_bar.empty()
                status_text.empty()
                st.error(f"Prediction failed: {exc}")
                st.exception(exc)
                return

        _display_results(data, result, ticker, timeframe)

    else:
        _show_architecture_idle()


# ─────────────────────────────────────────────────────────────────────────────
# Idle state
# ─────────────────────────────────────────────────────────────────────────────

def _show_architecture_idle():
    st.info("Click **Generate Prediction** to run the full 4-layer pipeline.")

    cols = st.columns(4)
    layer_info = [
        ("1", "Chronos Foundation", "Generative trajectory sampling (500 paths)"),
        ("2", "HMM Regime Gate", "Bull / Bear / Sideways / Volatile detection"),
        ("3", "Conformal Intervals", "Statistically guaranteed coverage bands"),
        ("4", "LLM Coherence", "Claude Haiku narrative validation score"),
    ]
    for col, (num, title, desc) in zip(cols, layer_info):
        with col:
            st.markdown(
                f"<div style='padding:14px;border-radius:8px;"
                f"background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);'>"
                f"<div style='font-size:0.75rem;color:#aaa;margin-bottom:4px'>LAYER {num}</div>"
                f"<div style='font-weight:600;margin-bottom:6px'>{title}</div>"
                f"<div style='font-size:0.82rem;color:#ccc'>{desc}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# Results display
# ─────────────────────────────────────────────────────────────────────────────

def _display_results(
    data: pd.DataFrame,
    result: PredictionResult,
    ticker: str,
    timeframe: str,
):
    st.success("Prediction complete — all 4 layers executed.")

    # ── Layer 2 — Regime ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Layer 2 — Market Regime Detection")

    badge_html = _regime_badge(result.regime, result.regime_confidence)
    cfg = _REGIME_CONFIG.get(result.regime, _REGIME_CONFIG["sideways"])
    st.markdown(
        f"{badge_html}<span style='margin-left:18px;color:#aaa;font-size:0.9rem'>"
        f"{cfg['desc']}</span>",
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    # Regime chips
    regime_cols = st.columns(4)
    for col, regime_name in zip(regime_cols, ["bull", "bear", "sideways", "volatile"]):
        r_cfg = _REGIME_CONFIG[regime_name]
        is_current = regime_name == result.regime
        border = f"2px solid {r_cfg['color']}" if is_current else "1px solid rgba(255,255,255,0.1)"
        bg = f"{r_cfg['color']}22" if is_current else "rgba(255,255,255,0.02)"
        with col:
            st.markdown(
                f"<div style='padding:10px 0;text-align:center;border-radius:8px;"
                f"border:{border};background:{bg}'>"
                f"<div style='font-size:1.4rem'>{r_cfg['icon']}</div>"
                f"<div style='font-weight:700;color:{r_cfg['color']}'>{r_cfg['label']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin-top:10px;font-size:0.8rem;color:#aaa'>Regime History</div>",
                unsafe_allow_html=True)
    st.plotly_chart(
        _build_regime_timeline(result.regime_history, data),
        use_container_width=True,
    )

    # ── Layer 1 — Probabilistic Forecast ─────────────────────────────────────
    st.markdown("---")
    st.subheader("Layer 1 — Probabilistic Forecast (Chronos)")

    st.markdown(
        f"<div style='font-size:0.85rem;color:#aaa;margin-bottom:8px'>"
        f"Generated <b>{result.n_samples}</b> independent trajectories. "
        f"Bands show conformal intervals from Layer 3.</div>",
        unsafe_allow_html=True,
    )

    st.plotly_chart(
        _build_fan_chart(data, result, ticker, timeframe),
        use_container_width=True,
    )

    # Price summary metrics
    predicted_final = float(result.median[-1])
    price_change = predicted_final - result.current_price
    pct_change = price_change / result.current_price * 100
    trend = "Bullish" if price_change > 0 else "Bearish"
    trend_delta = f"{pct_change:+.2f}%"

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Price", f"${result.current_price:.2f}")
    m2.metric("Median Forecast", f"${predicted_final:.2f}")
    m3.metric("Expected Change", f"${price_change:+.2f}", trend_delta)
    m4.metric("Trend Signal", trend)

    # ── Layer 3 — Conformal Intervals ────────────────────────────────────────
    st.markdown("---")
    st.subheader("Layer 3 — Conformal Prediction Intervals")

    cov_color = "#00c853" if result.empirical_coverage >= 0.85 else "#ffa726"
    st.markdown(
        f"<div style='padding:10px 16px;border-radius:6px;"
        f"background:rgba(255,255,255,0.04);border-left:3px solid {cov_color};"
        f"margin-bottom:12px;font-size:0.9rem'>"
        f"Empirical coverage on held-out calibration set: "
        f"<b style='color:{cov_color}'>{result.empirical_coverage*100:.1f}%</b> "
        f"(nominal 90%). Conformal prediction guarantees coverage ≥ nominal level "
        f"under the exchangeability assumption — unlike heuristic ±σ bands.</div>",
        unsafe_allow_html=True,
    )

    ci_cols = st.columns(3)
    interval_data = [
        ("80%", result.lower_80[-1], result.upper_80[-1], "#29b6f6"),
        ("90%", result.lower_90[-1], result.upper_90[-1], "#ff8c00"),
        ("95%", result.lower_95[-1], result.upper_95[-1], "#ab47bc"),
    ]
    for col, (level, lo, hi, colour) in zip(ci_cols, interval_data):
        width_pct = (hi - lo) / result.current_price * 100
        with col:
            st.markdown(
                f"<div style='padding:14px;border-radius:8px;"
                f"background:{colour}11;border:1px solid {colour}44;text-align:center'>"
                f"<div style='font-size:0.75rem;color:#aaa'>COVERAGE LEVEL</div>"
                f"<div style='font-size:1.6rem;font-weight:700;color:{colour}'>{level}</div>"
                f"<div style='font-size:0.9rem;margin:4px 0'>"
                f"${lo:.2f} – ${hi:.2f}</div>"
                f"<div style='font-size:0.78rem;color:#aaa'>Width: {width_pct:.1f}% of price</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ── Layer 4 — LLM Coherence ───────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Layer 4 — LLM Narrative Coherence (Claude Haiku)")

    if result.llm_available and result.coherence_score is not None:
        llm_col1, llm_col2 = st.columns([1, 2])

        with llm_col1:
            st.plotly_chart(
                _build_coherence_gauge(result.coherence_score),
                use_container_width=True,
            )

        with llm_col2:
            score = result.coherence_score
            if score >= 75:
                signal = ("HIGH CONFIDENCE", "#00c853")
            elif score >= 50:
                signal = ("MODERATE CONFIDENCE", "#ffa726")
            else:
                signal = ("LOW CONFIDENCE", "#f44336")

            st.markdown(
                f"<div style='margin-top:10px;padding:3px 12px;display:inline-block;"
                f"border-radius:4px;background:{signal[1]}22;"
                f"border:1px solid {signal[1]};color:{signal[1]};"
                f"font-size:0.78rem;font-weight:700;letter-spacing:1px'>"
                f"{signal[0]}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(f"**Assessment**")
            st.markdown(
                f"<div style='color:#ddd;font-size:0.92rem;line-height:1.6'>"
                f"{result.coherence_assessment}</div>",
                unsafe_allow_html=True,
            )

            if result.risk_factors:
                st.markdown("<br>**Risk Factors Identified**", unsafe_allow_html=True)
                for rf in result.risk_factors:
                    st.markdown(
                        f"<div style='display:inline-block;margin:3px 4px;"
                        f"padding:3px 10px;border-radius:12px;"
                        f"background:rgba(244,67,54,0.12);border:1px solid rgba(244,67,54,0.3);"
                        f"font-size:0.82rem;color:#ef9a9a'>{rf}</div>",
                        unsafe_allow_html=True,
                    )
    else:
        st.info(result.coherence_assessment)
        st.markdown(
            "Add your Anthropic API key in the **sidebar** to enable Claude Haiku "
            "narrative coherence scoring."
        )

    # ── Detailed Prediction Table ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Detailed Forecast Table")

    last_date = data.index[-1]
    pred_dates = pd.date_range(
        start=last_date + timedelta(days=1), periods=result.days, freq="D"
    )

    table_df = pd.DataFrame({
        "Date": pred_dates.strftime("%Y-%m-%d"),
        "Median Forecast": [f"${v:.2f}" for v in result.median],
        "80% Lower": [f"${v:.2f}" for v in result.lower_80],
        "80% Upper": [f"${v:.2f}" for v in result.upper_80],
        "90% Lower": [f"${v:.2f}" for v in result.lower_90],
        "90% Upper": [f"${v:.2f}" for v in result.upper_90],
        "Change vs Current": [
            f"${v - result.current_price:+.2f} ({(v - result.current_price) / result.current_price * 100:+.2f}%)"
            for v in result.median
        ],
    })

    st.dataframe(table_df, use_container_width=True, hide_index=True)

    # ── Disclaimer ────────────────────────────────────────────────────────────
    st.warning(
        "**Disclaimer:** These predictions are generated by a machine learning model "
        "and are not financial advice. Conformal coverage guarantees are statistical "
        "and assume price returns are exchangeable — a simplification that may not hold "
        "during structural market breaks. Always consult a qualified financial advisor "
        "before making investment decisions."
    )
