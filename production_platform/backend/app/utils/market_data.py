import requests
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class MarketDataService:
    @staticmethod
    def _fetch_yahoo_chart(ticker: str, period: str = "2y"):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={period}&interval=1d"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            return None
            
        data = res.json()
        result = data.get("chart", {}).get("result")
        if not result:
            return None
            
        result = result[0]
        timestamps = result.get("timestamp")
        if not timestamps:
            return None
            
        quote = result.get("indicators", {}).get("quote", [{}])[0]
        
        df = pd.DataFrame({
            "Open": quote.get("open", []),
            "High": quote.get("high", []),
            "Low": quote.get("low", []),
            "Close": quote.get("close", []),
            "Volume": quote.get("volume", [])
        })
        
        # Convert timestamps to DatetimeIndex so strftime() works downstream
        df.index = pd.to_datetime(timestamps, unit="s")
        
        # Yahoo sometimes returns nulls within the arrays; fill them
        df.ffill(inplace=True)
        df.bfill(inplace=True)
        return df

    @staticmethod
    def fetch_history(ticker: str, period: str = "2y"):
        """
        Fetch historical stock data using direct un-auth Yahoo Finance API
        so we don't rely on brittle bot-bypass libraries.
        """
        try:
            df = MarketDataService._fetch_yahoo_chart(ticker, period)
            if df is None or df.empty:
                logger.warning(f"Returned empty data for {ticker} (period={period})")
                return None
            logger.info(f"Fetched {len(df)} rows for {ticker}")
            return df
        except Exception as e:
            logger.error(f"fetch_history({ticker}) failed: {type(e).__name__}: {e}")
            return None

    @staticmethod
    def validate_ticker(ticker: str) -> bool:
        """
        Validate a ticker symbol by attempting to fetch recent data.
        """
        try:
            df = MarketDataService._fetch_yahoo_chart(ticker, "5d")
            return df is not None and not df.empty
        except Exception as e:
            logger.warning(f"validate_ticker({ticker}) failed: {type(e).__name__}: {e}")
            return False

    @staticmethod
    def get_info(ticker: str) -> dict:
        """
        Since yfinance info requires strict cookie passing, we gracefully fallback
        to returning an empty dict. The Option service has builtin failovers 
        that will read spot prices from fetch_history() instead. 
        """
        return {}

    @staticmethod
    def get_risk_free_rate() -> float:
        """
        Fetch risk-free rate from 13-week Treasury Bill (^IRX).
        Returns rate as a decimal (e.g., 0.05 for 5%).
        """
        try:
            df = MarketDataService._fetch_yahoo_chart("^IRX", "5d")
            if df is not None and not df.empty:
                return float(df["Close"].iloc[-1] / 100)
            return 0.05
        except Exception as e:
            logger.warning(f"get_risk_free_rate failed: {type(e).__name__}: {e}, using default 5%")
            return 0.05


