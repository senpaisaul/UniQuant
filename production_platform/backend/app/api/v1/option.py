from fastapi import APIRouter, HTTPException
from app.schemas.option import OptionCalculateRequest, OptionCalculationResponse, OptionModelResult, OptionGreeks
from app.services.option_pricing.black_scholes import BlackScholesModel
from app.services.option_pricing.monte_carlo import MonteCarloModel
from app.services.option_pricing.binomial import BinomialModel
from app.utils.market_data import MarketDataService
import numpy as np

router = APIRouter()

def calculate_volatility(ticker):
    """Calculate annualized historical volatility"""
    data = MarketDataService.fetch_history(ticker, period="1y")
    if data is None or data.empty:
        return 0.20  # Fallback
    
    returns = np.log(data['Close'] / data['Close'].shift(1)).dropna()
    return float(returns.std() * np.sqrt(252))

@router.post("/calculate", response_model=OptionCalculationResponse)
def calculate_option_price(request: OptionCalculateRequest):
    # 1. Gather Market Data
    spot_price = 0.0
    
    # Try getting info, fallback to history
    info = MarketDataService.get_info(request.ticker)
    if 'currentPrice' in info and info['currentPrice']:
        spot_price = info['currentPrice']
    else:
        hist = MarketDataService.fetch_history(request.ticker, period="5d")
        if hist is not None and not hist.empty:
            spot_price = float(hist['Close'].iloc[-1])
            
    if spot_price <= 0:
         raise HTTPException(status_code=404, detail="Could not fetch spot price")
         
    # Volatility
    sigma = request.volatility_override if request.volatility_override else calculate_volatility(request.ticker)
    
    # Risk Free Rate
    r = request.risk_free_rate if request.risk_free_rate else MarketDataService.get_risk_free_rate()
    
    # Dividend Yield
    q = info.get('dividendYield', 0) if info else 0
    if q is None: q = 0
    
    # Params
    S = spot_price
    K = request.strike_price
    T = request.days_to_expiry / 365.0
    
    # 2. Black Scholes
    bs_model = BlackScholesModel(S, K, T, r, sigma, q)
    bs_price = bs_model.price(request.option_type)
    bs_greeks = bs_model.get_all_greeks(request.option_type)
    
    # 3. Binomial
    bn_model = BinomialModel(S, K, T, r, sigma, q, n_steps=200)
    bn_euro = bn_model.european_option_price(request.option_type)
    bn_amer, _ = bn_model.american_option_price(request.option_type)
    
    # 4. Monte Carlo
    mc_steps = max(min(int(T * 252), 252), 21)
    mc_model = MonteCarloModel(S, K, T, r, sigma, q, n_simulations=50000, n_steps=mc_steps)
    mc_euro, _ = mc_model.european_option_price(request.option_type)
    mc_asian, _ = mc_model.asian_option_price(request.option_type, "arithmetic")
    barrier_type = "down-and-out" if request.option_type == "Call" else "up-and-out"
    mc_barrier, _, barrier_lvl = mc_model.barrier_option_price(request.option_type, barrier_type)
    
    return {
        "spot_price": S,
        "volatility": sigma,
        "risk_free_rate": r,
        "black_scholes": {
            "price": bs_price,
            "greeks": bs_greeks
        },
        "binomial": {
            "euro": float(bn_euro),
            "amer": float(bn_amer)
        },
        "monte_carlo": {
            "euro": float(mc_euro),
            "asian": float(mc_asian),
            "barrier": float(mc_barrier)
        }
    }
