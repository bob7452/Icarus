import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
from dataclasses import dataclass

@dataclass
class OptionInput:
    option_type: str  # 'call' or 'put'
    S: float  # 現價
    K: float  # 行權價
    T: float  # 年化剩餘時間
    r: float  # 無風險利率
    market_price: float  # 市場成交價
    q: float = 0.0  # 股息率，預設為0

@dataclass
class OptionGreeks:
    IV: float
    Delta: float
    Gamma: float
    Vega: float
    Theta: float
    Rho: float

def black_scholes_price(opt: OptionInput, sigma: float) -> float:
    d1 = (np.log(opt.S / opt.K) + (opt.r - opt.q + 0.5 * sigma ** 2) * opt.T) / (sigma * np.sqrt(opt.T))
    d2 = d1 - sigma * np.sqrt(opt.T)
    if opt.option_type == 'call':
        return opt.S * np.exp(-opt.q * opt.T) * norm.cdf(d1) - opt.K * np.exp(-opt.r * opt.T) * norm.cdf(d2)
    elif opt.option_type == 'put':
        return opt.K * np.exp(-opt.r * opt.T) * norm.cdf(-d2) - opt.S * np.exp(-opt.q * opt.T) * norm.cdf(-d1)
    else:
        raise ValueError("option_type 必須是 'call' 或 'put'")

def implied_volatility(opt: OptionInput) -> float:
    def objective(sigma):
        return black_scholes_price(opt, sigma) - opt.market_price
    try:
        return brentq(objective, 1e-6, 5.0)
    except ValueError:
        return None

def calculate_greeks(opt: OptionInput, sigma: float) -> OptionGreeks:
    d1 = (np.log(opt.S / opt.K) + (opt.r - opt.q + 0.5 * sigma ** 2) * opt.T) / (sigma * np.sqrt(opt.T))
    d2 = d1 - sigma * np.sqrt(opt.T)

    delta = np.exp(-opt.q * opt.T) * norm.cdf(d1) if opt.option_type == 'call' else -np.exp(-opt.q * opt.T) * norm.cdf(-d1)
    gamma = np.exp(-opt.q * opt.T) * norm.pdf(d1) / (opt.S * sigma * np.sqrt(opt.T))
    vega = opt.S * np.exp(-opt.q * opt.T) * norm.pdf(d1) * np.sqrt(opt.T) / 100
    theta = (
        (-opt.S * norm.pdf(d1) * sigma * np.exp(-opt.q * opt.T)) / (2 * np.sqrt(opt.T))
        - opt.r * opt.K * np.exp(-opt.r * opt.T) * (norm.cdf(d2) if opt.option_type == 'call' else norm.cdf(-d2))
        + opt.q * opt.S * np.exp(-opt.q * opt.T) * (norm.cdf(d1) if opt.option_type == 'call' else norm.cdf(-d1))
    ) / 365
    rho = (
        opt.K * opt.T * np.exp(-opt.r * opt.T) * norm.cdf(d2) / 100 if opt.option_type == 'call'
        else -opt.K * opt.T * np.exp(-opt.r * opt.T) * norm.cdf(-d2) / 100
    )

    return OptionGreeks(
        IV=sigma,
        Delta=delta,
        Gamma=gamma,
        Vega=vega,
        Theta=theta,
        Rho=rho
    )