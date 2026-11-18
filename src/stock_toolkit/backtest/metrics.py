from __future__ import annotations

import numpy as np
import pandas as pd


def max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    dd = (equity - peak) / peak
    return float(dd.min())


def annualized_return(equity: pd.Series) -> float:
    if len(equity) < 2:
        return 0.0
    total = equity.iloc[-1] / equity.iloc[0] - 1.0
    days = (equity.index[-1] - equity.index[0]).days
    if days <= 0:
        return float(total)
    return float((1 + total) ** (365.0 / days) - 1)


def sharpe_ratio(daily_returns: pd.Series, risk_free: float = 0.0) -> float:
    if daily_returns.std() == 0 or daily_returns.empty:
        return 0.0
    excess = daily_returns - risk_free / 252
    return float(np.sqrt(252) * excess.mean() / excess.std())
