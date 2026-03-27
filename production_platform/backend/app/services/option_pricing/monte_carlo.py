import numpy as np

class MonteCarloModel:
    """
    Monte Carlo simulation for option pricing.
    
    Supports: European, Asian, Lookback, and Barrier options.
    Uses antithetic variates for variance reduction.
    """
    
    def __init__(self, S, K, T, r, sigma, q=0, n_simulations=100000, n_steps=252):
        self.S = S
        self.K = K
        self.T = T
        self.r = r
        self.sigma = sigma
        self.q = q
        self.n_simulations = n_simulations
        self.n_steps = n_steps
        self.dt = T / n_steps
        
    def _generate_paths(self, antithetic=True, seed=42):
        """Generate price paths using Geometric Brownian Motion"""
        np.random.seed(seed)
        
        n_sims = self.n_simulations // 2 if antithetic else self.n_simulations
        
        drift = (self.r - self.q - 0.5 * self.sigma**2) * self.dt
        vol = self.sigma * np.sqrt(self.dt)
        
        Z = np.random.standard_normal((n_sims, self.n_steps))
        
        if antithetic:
            Z = np.vstack([Z, -Z])
        
        log_returns = drift + vol * Z
        log_paths = np.cumsum(log_returns, axis=1)
        
        paths = self.S * np.exp(log_paths)
        paths = np.column_stack([np.full(self.n_simulations, self.S), paths])
        
        return paths
    
    def european_option_price(self, option_type="call"):
        """Price European option"""
        paths = self._generate_paths()
        final_prices = paths[:, -1]
        
        if option_type.lower() == "call":
            payoffs = np.maximum(final_prices - self.K, 0)
        else:
            payoffs = np.maximum(self.K - final_prices, 0)
        
        discount = np.exp(-self.r * self.T)
        price = discount * np.mean(payoffs)
        std_error = discount * np.std(payoffs) / np.sqrt(self.n_simulations)
        
        return price, std_error
    
    def asian_option_price(self, option_type="call", averaging="arithmetic"):
        """Price Asian option with arithmetic or geometric averaging"""
        paths = self._generate_paths()
        
        if averaging == "arithmetic":
            avg_prices = np.mean(paths, axis=1)
        else:
            avg_prices = np.exp(np.mean(np.log(paths), axis=1))
        
        if option_type.lower() == "call":
            payoffs = np.maximum(avg_prices - self.K, 0)
        else:
            payoffs = np.maximum(self.K - avg_prices, 0)
        
        discount = np.exp(-self.r * self.T)
        price = discount * np.mean(payoffs)
        std_error = discount * np.std(payoffs) / np.sqrt(self.n_simulations)
        
        return price, std_error
    
    def lookback_option_price(self, option_type="call"):
        """Price floating strike Lookback option"""
        paths = self._generate_paths()
        final_prices = paths[:, -1]
        
        if option_type.lower() == "call":
            min_prices = np.min(paths, axis=1)
            payoffs = np.maximum(final_prices - min_prices, 0)
        else:
            max_prices = np.max(paths, axis=1)
            payoffs = np.maximum(max_prices - final_prices, 0)
        
        discount = np.exp(-self.r * self.T)
        price = discount * np.mean(payoffs)
        std_error = discount * np.std(payoffs) / np.sqrt(self.n_simulations)
        
        return price, std_error
    
    def barrier_option_price(self, option_type="call", barrier_type="down-and-out", barrier_level=None):
        """Price Barrier option"""
        if barrier_level is None:
            barrier_level = self.S * 0.9 if "down" in barrier_type else self.S * 1.1
        
        paths = self._generate_paths()
        final_prices = paths[:, -1]
        
        if "down" in barrier_type:
            barrier_hit = np.any(paths <= barrier_level, axis=1)
        else:
            barrier_hit = np.any(paths >= barrier_level, axis=1)
        
        if option_type.lower() == "call":
            base_payoffs = np.maximum(final_prices - self.K, 0)
        else:
            base_payoffs = np.maximum(self.K - final_prices, 0)
        
        if "out" in barrier_type:
            payoffs = np.where(barrier_hit, 0, base_payoffs)
        else:
            payoffs = np.where(barrier_hit, base_payoffs, 0)
        
        discount = np.exp(-self.r * self.T)
        price = discount * np.mean(payoffs)
        std_error = discount * np.std(payoffs) / np.sqrt(self.n_simulations)
        
        return price, std_error, barrier_level
