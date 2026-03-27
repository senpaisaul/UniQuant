import streamlit as st
import numpy as np
import pandas as pd
from utils.market_data import MarketDataService
from services.option_pricing.black_scholes import BlackScholesModel
from services.option_pricing.monte_carlo import MonteCarloModel
from services.option_pricing.binomial import BinomialModel

def calculate_volatility(ticker):
    """Calculate annualized historical volatility"""
    data = MarketDataService.fetch_history(ticker, period="1y")
    if data is None or data.empty:
        return 0.20  # Fallback
    
    returns = np.log(data['Close'] / data['Close'].shift(1)).dropna()
    return float(returns.std() * np.sqrt(252))

def render():
    st.header("🧮 Option Pricing Calculator")
    st.info("Production-grade pricing using Black-Scholes, Monte Carlo, and Binomial Tree models.")

    # Sidebar Inputs
    st.sidebar.markdown("---")
    st.sidebar.header("Option Parameters")
    
    ticker = st.sidebar.text_input("Ticker Symbol", value="SPY", key="opt_ticker").upper()
    option_type = st.sidebar.selectbox("Option Type", ["Call", "Put"], key="opt_type")
    
    # Get Spot Price for default/ATM
    spot_price = 0.0
    if ticker:
        info = MarketDataService.get_info(ticker)
        # Try to get fast price, else fetch history
        if 'currentPrice' in info:
            spot_price = info['currentPrice']
        else:
            hist = MarketDataService.fetch_history(ticker, period="5d")
            if hist is not None and not hist.empty:
                spot_price = hist['Close'].iloc[-1]
    
    strike_price = st.sidebar.number_input("Strike Price ($)", min_value=0.01, value=float(spot_price) if spot_price > 0 else 100.0, step=1.0, format="%.2f", key="opt_strike")
    days_to_expiry = st.sidebar.number_input("Days to Expiry", min_value=1, max_value=1095, value=30, key="opt_days")
    
    rf_rate_manual = st.sidebar.checkbox("Override Risk-Free Rate", key="opt_rf_override")
    if rf_rate_manual:
        risk_free_rate = st.sidebar.number_input("Risk-Free Rate (%)", value=5.0, step=0.1, key="opt_rf_val") / 100
    else:
        risk_free_rate = MarketDataService.get_risk_free_rate()
        st.sidebar.markdown(f"Risk-Free Rate: **{risk_free_rate*100:.2f}%** (Source: ^IRX)")

    st.sidebar.markdown("---")
    
    if st.button("Calculate Prices", type="primary"):
        if not ticker:
            st.error("Please enter a ticker symbol.")
            return

        with st.spinner("Fetching market data and running simulations..."):
            # 1. Market Data
            volatility = calculate_volatility(ticker)
            dividend_yield = MarketDataService.get_info(ticker).get('dividendYield', 0) or 0
            
            S = spot_price
            K = strike_price
            T = days_to_expiry / 365.0
            r = risk_free_rate
            sigma = volatility
            q = dividend_yield
            
            # Display Market Data
            st.subheader("1. Market Data & Parameters")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Spot Price", f"${S:.2f}")
            col2.metric("Strike Price", f"${K:.2f}")
            col3.metric("Volatility (IV)", f"{sigma*100:.2f}%")
            col4.metric("Dividend Yield", f"{q*100:.2f}%")
            
            moneyness = S / K
            status = "ATM"
            if option_type == "Call":
                if moneyness > 1.02: status = "ITM"
                elif moneyness < 0.98: status = "OTM"
            else:
                if moneyness < 0.98: status = "ITM"
                elif moneyness > 1.02: status = "OTM"
            
            st.caption(f"Status: **{status}** (Moneyness: {moneyness:.2%})")
            st.markdown("---")

            # 2. Black-Scholes
            st.subheader("2. Black-Scholes Model")
            bs = BlackScholesModel(S, K, T, r, sigma, q)
            bs_price = bs.price(option_type)
            greeks = bs.get_all_greeks(option_type)
            
            c1, c2 = st.columns([1, 3])
            c1.metric(f"BS {option_type} Price", f"${bs_price:.4f}")
            
            # Greeks Display
            greeks_df = pd.DataFrame([greeks]).T
            greeks_df.columns = ["Value"]
            c2.dataframe(greeks_df.style.format("{:.4f}"), use_container_width=True)
            
            st.markdown("---")

            # 3. Binomial Tree
            st.subheader("3. Binomial Tree (American)")
            bn = BinomialModel(S, K, T, r, sigma, q, n_steps=200) # Increased steps for better accuracy
            bn_euro = bn.european_option_price(option_type)
            bn_amer, ex_nodes = bn.american_option_price(option_type)
            early_prem = bn_amer - bn_euro
            
            c1, c2, c3 = st.columns(3)
            c1.metric("European Price", f"${bn_euro:.4f}")
            c2.metric("American Price", f"${bn_amer:.4f}")
            c3.metric("Early Exercise Premium", f"${early_prem:.4f}")
            
            if early_prem > 0.01:
                st.warning(f"⚠️ Significant early exercise value detected. American option is worth ${early_prem:.4f} more.")

            st.markdown("---")

            # 4. Monte Carlo
            st.subheader("4. Monte Carlo Simulation")
            mc_steps = max(min(int(T * 252), 252), 21)
            mc = MonteCarloModel(S, K, T, r, sigma, q, n_simulations=50000, n_steps=mc_steps)
            
            mc_euro, mc_se = mc.european_option_price(option_type)
            mc_asian, _ = mc.asian_option_price(option_type, "arithmetic")
            mc_barr, _, barr_lvl = mc.barrier_option_price(option_type, "down-and-out" if option_type == "Call" else "up-and-out")
            
            mc_data = {
                "Option Style": ["European", "Asian (Arithmetic)", f"Barrier (Out @ {barr_lvl:.2f})"],
                "Price": [mc_euro, mc_asian, mc_barr],
                "Std Error": [mc_se, "N/A", "N/A"]
            }
            st.dataframe(pd.DataFrame(mc_data).style.format({"Price": "${:.4f}", "Std Error": "${:.4f}"}), use_container_width=True)

    else:
        st.info("👈 Adjust parameters in the sidebar and click **Calculate Prices**")
