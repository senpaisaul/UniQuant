<div align="center">

# UniQuant
### Production-Grade AI Financial Intelligence Platform

[![Next.js](https://img.shields.io/badge/Next.js-14-black?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Chronos](https://img.shields.io/badge/Amazon-Chronos%20T5--Small-FF9900?style=for-the-badge&logo=amazon&logoColor=white)](https://github.com/amazon-science/chronos-forecasting)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.0-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)

<p align="center">
  <b>Credit Risk Assessment</b> &nbsp;•&nbsp; <b>Generative AI Stock Prediction</b> &nbsp;•&nbsp; <b>Advanced Option Pricing</b>
</p>

</div>

---

## Overview

UniQuant is a production-scale fintech platform that unifies three financial modelling domains into a single full-stack application. The frontend is built with Next.js 14 and TypeScript; the backend is a FastAPI service exposing a versioned REST API. The platform is deployed on Render (backend) and Vercel (frontend).

The stock prediction module underwent six design iterations, replacing the original LSTM baseline with a novel 4-layer generative AI architecture that combines a pre-trained foundation model, asymmetric volatility modelling, regime-aware conformal calibration, and LLM coherence validation.

---

## Modules

### Credit Risk Engine
Instant borrower risk scoring using an ensemble of Random Forest and XGBoost classifiers trained on structured loan application data. Returns a probability of default with a `Low / High` risk classification and feature importance breakdown. Built on Scikit-Learn pipelines served via FastAPI.

### Stock Prediction Lab — 4-Layer Generative AI Architecture

The most technically involved module. Replaced a deterministic Bidirectional LSTM with a probabilistic generative system through six iterations:

| Version | Architecture | Key Problem |
|---|---|---|
| v1 | Bidirectional LSTM | Point forecast, no uncertainty quantification |
| v2 | Chronos T5-Small (raw) | Sample spread too narrow for equities, 35–40% CI width |
| v3 | Chronos + Split Conformal | q₉₀ multiplier 8–15×, intervals 41%+ wide |
| v4 | Chronos + GARCH(1,1) Gaussian | 100% regime confidence saturation, symmetric volatility |
| v5 | Chronos + GARCH(1,1) Student-t | Hardcoded drift table, no transition awareness |
| v6 (current) | Chronos + GJR-GARCH + Regime-Conditional Conformal | — |

**Current architecture (v6):**

**Layer 1 — Amazon Chronos T5-Small**
A generative foundation model pre-trained on 700B+ time series observations. Produces 500 probabilistic price trajectories per prediction. Used for directional signal, scenario percentiles (bear/base/bull at 15th/50th/85th), and path-level probability analytics. The 500 samples are not used for interval widths — see Layer 3.

**Layer 2 — 4-State Gaussian HMM**
Hidden Markov Model trained on three features: log-returns, rolling 5-day volatility, and log volume ratio. Classifies the current market into `bull`, `bear`, `sideways`, or `volatile`. Regime confidence is temperature-softened (T=1.5) over the last 5 posterior observations and capped at 85% to prevent the saturation artefact common in well-fit Gaussian HMMs. Data-driven regime drift (the actual historical mean log-return of same-regime observations, gated by a t-test) is injected into the Chronos median, scaled by how far confidence exceeds the 50% uninformative prior.

**Layer 3 — GJR-GARCH(1,1,1) + Regime-Conditional Conformal Calibration**
GJR-GARCH (Glosten, Jagannathan & Runkle 1993) extends GARCH with an asymmetric term that gives negative return shocks a proportionally larger effect on next-period variance than positive shocks — the leverage effect empirically dominant in equity markets. Student-t innovations handle fat tails.

Conformal calibration (Tibshirani et al. 2019) is conditioned on the current HMM regime: only standardized residuals from same-regime time steps are used to compute the conformal quantile. This means volatile-regime calibration automatically produces wider intervals and bull-regime calibration produces tighter ones.

Interval widths are additionally inflated by a factor of `1 + 0.5 × H_norm` where `H_norm` is the normalised Shannon entropy of the HMM posterior. At maximum regime uncertainty (transition), intervals widen by up to 50%. At stable regimes, no inflation is applied.

**Layer 4 — Claude Haiku (LLM Coherence Scoring)**
A structured prompt containing all forecast outputs, model architecture description, regime state, transition entropy, interval inflation applied, and regime drift component is sent to Claude Haiku. Returns a 0–100 coherence score, a 2–3 sentence assessment, and up to three risk factors. The score validates internal consistency of the forecast before it is displayed.

**Forecast outputs per prediction:**
- Per-step median price with regime drift applied (trading-day dates, skipping weekends)
- 80%, 90%, and 95% confidence intervals from GJR-GARCH + regime-conditional conformal
- Bear / Base / Bull scenario prices (15th / 50th / 85th percentile of 500 Chronos paths)
- Probability of gain / loss at end of horizon
- Probability of price hitting ±5% or ±10% at any point during the horizon
- Maximum expected gain / drawdown (75th / 25th percentile of path extremes)
- GJR-GARCH annualised volatility
- Final-price distribution skewness
- Trajectory shape classification (uptrend / downtrend / flat / volatile)
- LLM coherence score, assessment, and risk factors

### Option Pricing Suite
Multi-model derivative valuation supporting European and American options:
- **Black-Scholes**: closed-form European option pricing
- **Monte Carlo**: path-dependent simulation (10,000 paths)
- **Binomial Tree**: American option pricing with early exercise
- **Live Greeks**: Delta, Gamma, Theta, Vega computed in real time

---

## Architecture

```
User
 └── Next.js 14 Frontend (Vercel)
       └── FastAPI Backend /api/v1 (Render)
             ├── /credit  — Scikit-Learn ensemble
             ├── /stock   — Chronos + GJR-GARCH + HMM + Claude Haiku
             └── /option  — Black-Scholes / Monte Carlo / Binomial Tree
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Recharts, Framer Motion |
| Backend | FastAPI, Pydantic v2, Uvicorn |
| Generative Model | Amazon Chronos T5-Small (PyTorch) |
| Volatility | GJR-GARCH(1,1,1) via `arch` library |
| Regime Detection | 4-state Gaussian HMM via `hmmlearn` |
| Calibration | Split conformal prediction (regime-conditional) |
| LLM Validation | Claude Haiku (`claude-haiku-4-5-20251001`) via Anthropic SDK |
| Credit / Option | Scikit-Learn, XGBoost, NumPy, SciPy |
| Market Data | yfinance |
| Deployment | Render (Pro, 4 GB RAM) + Vercel |

---

## Local Development

### Prerequisites
- Python 3.11
- Node.js 18+
- conda or venv

### 1 — Environment setup

```bash
# Create and activate conda environment (recommended)
conda create -n uniquant python=3.11 -y
conda activate uniquant

# Install backend dependencies
cd production_platform/backend
pip install -r requirements.txt
```

### 2 — Environment variables

Create a `.env` file in the project root (`UniQuant-main/.env`):

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ALLOWED_ORIGINS=http://localhost:3000
```

The backend uses `python-dotenv` with `find_dotenv()` to walk up the directory tree and locate this file automatically.

### 3 — Start the backend

```bash
cd production_platform/backend
uvicorn main:app --reload
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

The first prediction request downloads and caches the Chronos T5-Small model weights (~300 MB). Subsequent requests use the in-memory singleton.

### 4 — Start the frontend

```bash
cd production_platform/frontend
npm install
npm run dev
# Dashboard at http://localhost:3000
```

---

## Deployment

Backend is deployed on **Render Pro** (4 GB RAM required for PyTorch + Chronos). The Dockerfile pre-bakes the Chronos model weights into the image at build time, eliminating cold-start latency. Frontend is deployed on **Vercel**.

Set the following environment variables:

**Render (backend):**
```
ANTHROPIC_API_KEY=your_key
ALLOWED_ORIGINS=https://your-app.vercel.app
```

**Vercel (frontend):**
```
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com/api/v1
```

---

## License
Proprietary — UniQuant. All rights reserved.
