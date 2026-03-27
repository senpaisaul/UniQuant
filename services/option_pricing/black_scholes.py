import numpy as np
from scipy.stats import norm

class BlackScholesModel:
    """
    Black-Scholes-Merton model for European option pricing.
    
    Attributes:
        S: Spot price
        K: Strike price
        T: Time to expiry (years)
        r: Risk-free rate
        sigma: Volatility
        q: Dividend yield
    """
    
    def __init__(self, S, K, T, r, sigma, q=0):
        self.S = S
        self.K = K
        self.T = T
        self.r = r
        self.sigma = sigma
        self.q = q
        self._calculate_d1_d2()
    
    def _calculate_d1_d2(self):
        """Calculate d1 and d2 parameters"""
        sqrt_T = np.sqrt(self.T)
        self.d1 = (np.log(self.S / self.K) + (self.r - self.q + 0.5 * self.sigma**2) * self.T) / (self.sigma * sqrt_T)
        self.d2 = self.d1 - self.sigma * sqrt_T
    
    def call_price(self):
        """European call option price"""
        return (self.S * np.exp(-self.q * self.T) * norm.cdf(self.d1) - 
                self.K * np.exp(-self.r * self.T) * norm.cdf(self.d2))
    
    def put_price(self):
        """European put option price"""
        return (self.K * np.exp(-self.r * self.T) * norm.cdf(-self.d2) - 
                self.S * np.exp(-self.q * self.T) * norm.cdf(-self.d1))
    
    def price(self, option_type="call"):
        """Get option price by type"""
        return self.call_price() if option_type.lower() == "call" else self.put_price()
    
    def delta(self, option_type="call"):
        """Delta: dV/dS"""
        if option_type.lower() == "call":
            return np.exp(-self.q * self.T) * norm.cdf(self.d1)
        return np.exp(-self.q * self.T) * (norm.cdf(self.d1) - 1)
    
    def gamma(self):
        """Gamma: d2V/dS2"""
        return (np.exp(-self.q * self.T) * norm.pdf(self.d1)) / (self.S * self.sigma * np.sqrt(self.T))
    
    def theta(self, option_type="call"):
        """Theta: dV/dT (per day)"""
        term1 = -(self.S * self.sigma * np.exp(-self.q * self.T) * norm.pdf(self.d1)) / (2 * np.sqrt(self.T))
        if option_type.lower() == "call":
            term2 = self.q * self.S * np.exp(-self.q * self.T) * norm.cdf(self.d1)
            term3 = -self.r * self.K * np.exp(-self.r * self.T) * norm.cdf(self.d2)
        else:
            term2 = -self.q * self.S * np.exp(-self.q * self.T) * norm.cdf(-self.d1)
            term3 = self.r * self.K * np.exp(-self.r * self.T) * norm.cdf(-self.d2)
        return (term1 + term2 + term3) / 365
    
    def vega(self):
        """Vega: dV/dsigma (per 1% change)"""
        return self.S * np.exp(-self.q * self.T) * np.sqrt(self.T) * norm.pdf(self.d1) / 100
    
    def rho(self, option_type="call"):
        """Rho: dV/dr (per 1% change)"""
        if option_type.lower() == "call":
            return self.K * self.T * np.exp(-self.r * self.T) * norm.cdf(self.d2) / 100
        return -self.K * self.T * np.exp(-self.r * self.T) * norm.cdf(-self.d2) / 100
    
    def get_all_greeks(self, option_type="call"):
        """Return all Greeks as dictionary"""
        return {
            'delta': self.delta(option_type),
            'gamma': self.gamma(),
            'theta': self.theta(option_type),
            'vega': self.vega(),
            'rho': self.rho(option_type)
        }
