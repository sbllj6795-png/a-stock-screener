from __future__ import annotations

import pandas as pd


def compute_skdj(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    n: int = 9,
    m1: int = 3,
    m2: int = 3,
) -> pd.DataFrame:
    """慢速 KDJ（双平滑 K、D），与国内常见 SKDJ 一致。"""
    low_n = low.rolling(n, min_periods=1).min()
    high_n = high.rolling(n, min_periods=1).max()
    denom = (high_n - low_n).replace(0, pd.NA)
    rsv = (close - low_n) / denom * 100
    rsv = rsv.fillna(50.0)
    k_smooth = rsv.rolling(m1, min_periods=1).mean()
    k = k_smooth.rolling(m2, min_periods=1).mean()
    d = k.rolling(m2, min_periods=1).mean()
    j = 3 * k - 2 * d
    return pd.DataFrame({"k": k, "d": d, "j": j})


def diff_near(k: float, d: float, target: float, tol: float) -> bool:
    if pd.isna(k) or pd.isna(d):
        return False
    return abs(abs(float(k) - float(d)) - target) <= tol
