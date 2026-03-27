import yfinance as yf
import streamlit as st

class MarketDataService:
    @staticmethod
    @st.cache_data(ttl=3600)
    def fetch_history(ticker: str, period: str = "2y"):
        """
        Fetch historical stock data for a given ticker and period.
        """
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period=period)
            if data.empty:
                return None
            return data
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            return None

    @staticmethod
    def validate_ticker(ticker: str):
        """
        Validate a ticker symbol by attempting to fetch recent data.
        """
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            if hist.empty:
                return False
            return True
        except Exception:
            return False

    @staticmethod
    def get_info(ticker: str):
        """
        Get stock info dictionary.
        """
        try:
            return yf.Ticker(ticker).info
        except Exception:
            return {}

    @staticmethod
    def get_risk_free_rate():
        """
        Fetch risk-free rate from 13-week Treasury Bill (^IRX).
        Returns rate as a decimal (e.g., 0.05 for 5%).
        """
        try:
            treasury = yf.Ticker("^IRX")
            hist = treasury.history(period="5d")
            if not hist.empty:
                return float(hist['Close'].iloc[-1] / 100)
            return 0.05
        except Exception:
            return 0.05
