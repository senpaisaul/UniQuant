from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class OptionCalculateRequest(BaseModel):
    ticker: str
    option_type: str = Field(..., pattern="^(Call|Put)$")
    strike_price: float = Field(..., gt=0)
    days_to_expiry: int = Field(..., ge=1)
    risk_free_rate: Optional[float] = None
    volatility_override: Optional[float] = None

class OptionGreeks(BaseModel):
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float

class OptionModelResult(BaseModel):
    price: float
    greeks: Optional[OptionGreeks] = None
    details: Optional[Dict[str, Any]] = None

class OptionCalculationResponse(BaseModel):
    spot_price: float
    volatility: float
    risk_free_rate: float
    black_scholes: OptionModelResult
    binomial: Dict[str, float]
    monte_carlo: Dict[str, Any]
