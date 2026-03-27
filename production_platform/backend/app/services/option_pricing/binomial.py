import numpy as np

class BinomialModel:
    """
    Cox-Ross-Rubinstein Binomial Tree model.
    
    Supports both European and American option pricing
    with early exercise valuation.
    """
    
    def __init__(self, S, K, T, r, sigma, q=0, n_steps=500):
        self.S = S
        self.K = K
        self.T = T
        self.r = r
        self.sigma = sigma
        self.q = q
        self.n_steps = n_steps
        self.dt = T / n_steps
        
        # CRR parameters
        self.u = np.exp(sigma * np.sqrt(self.dt))
        self.d = 1 / self.u
        self.p = (np.exp((r - q) * self.dt) - self.d) / (self.u - self.d)
        self.discount = np.exp(-r * self.dt)
        
    def _build_terminal_stock_prices(self):
        """Build stock prices at maturity"""
        n = self.n_steps
        return self.S * (self.u ** np.arange(n, -1, -1)) * (self.d ** np.arange(0, n + 1))
    
    def european_option_price(self, option_type="call"):
        """Price European option using backward induction"""
        n = self.n_steps
        stock_prices = self._build_terminal_stock_prices()
        
        if option_type.lower() == "call":
            option_values = np.maximum(stock_prices - self.K, 0)
        else:
            option_values = np.maximum(self.K - stock_prices, 0)
        
        for i in range(n - 1, -1, -1):
            option_values = self.discount * (self.p * option_values[:-1] + (1 - self.p) * option_values[1:])
        
        return option_values[0]
    
    def american_option_price(self, option_type="call"):
        """Price American option with early exercise"""
        n = self.n_steps
        
        # Build stock price tree
        stock_tree = np.zeros((n + 1, n + 1))
        stock_tree[0, 0] = self.S
        
        for i in range(1, n + 1):
            stock_tree[0:i, i] = stock_tree[0:i, i-1] * self.u
            stock_tree[i, i] = stock_tree[i-1, i-1] * self.d
        
        # Initialize option values at maturity
        option_tree = np.zeros((n + 1, n + 1))
        
        if option_type.lower() == "call":
            option_tree[:, n] = np.maximum(stock_tree[:, n] - self.K, 0)
        else:
            option_tree[:, n] = np.maximum(self.K - stock_tree[:, n], 0)
        
        # Backward induction with early exercise
        early_exercise_count = 0
        
        for i in range(n - 1, -1, -1):
            continuation = self.discount * (self.p * option_tree[0:i+1, i+1] + 
                                           (1 - self.p) * option_tree[1:i+2, i+1])
            
            if option_type.lower() == "call":
                exercise = np.maximum(stock_tree[0:i+1, i] - self.K, 0)
            else:
                exercise = np.maximum(self.K - stock_tree[0:i+1, i], 0)
            
            early_exercise_count += np.sum(exercise > continuation)
            option_tree[0:i+1, i] = np.maximum(continuation, exercise)
        
        return option_tree[0, 0], early_exercise_count
    
    def early_exercise_premium(self, option_type="call"):
        """Calculate early exercise premium"""
        american, _ = self.american_option_price(option_type)
        european = self.european_option_price(option_type)
        return american - european
    
    def calculate_greeks(self, option_type="call", american=True):
        """Calculate Greeks using finite differences"""
        if american:
            price_func = lambda m: m.american_option_price(option_type)[0]
        else:
            price_func = lambda m: m.european_option_price(option_type)[0] if isinstance(m.european_option_price(option_type), tuple) else m.european_option_price(option_type)
        
        base_price = price_func(self)
        
        # Delta
        dS = self.S * 0.01
        model_up = BinomialModel(self.S + dS, self.K, self.T, self.r, self.sigma, self.q, self.n_steps)
        model_down = BinomialModel(self.S - dS, self.K, self.T, self.r, self.sigma, self.q, self.n_steps)
        delta = (price_func(model_up) - price_func(model_down)) / (2 * dS)
        
        # Gamma
        gamma = (price_func(model_up) - 2 * base_price + price_func(model_down)) / (dS ** 2)
        
        # Theta
        if self.T > 1/365:
            dT = 1/365
            model_theta = BinomialModel(self.S, self.K, self.T - dT, self.r, self.sigma, self.q, self.n_steps)
            theta = price_func(model_theta) - base_price
        else:
            theta = 0
        
        # Vega
        d_sigma = 0.01
        model_vega_up = BinomialModel(self.S, self.K, self.T, self.r, self.sigma + d_sigma, self.q, self.n_steps)
        model_vega_down = BinomialModel(self.S, self.K, self.T, self.r, self.sigma - d_sigma, self.q, self.n_steps)
        vega = (price_func(model_vega_up) - price_func(model_vega_down)) / 2
        
        return {'delta': delta, 'gamma': gamma, 'theta': theta, 'vega': vega}
