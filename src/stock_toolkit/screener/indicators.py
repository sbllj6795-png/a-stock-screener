from __future__ import annotations

import pandas as pd

from stock_toolkit.data import gm_data
from stock_toolkit.screener.rules import TechnicalRule


def apply_technical(
    symbols: list[str],
    trade_date: str | None,
    rules: list[TechnicalRule],
) -> list[str]:
    if not rules or not symbols:
        return symbols

    end_time = f"{trade_date} 15:00:00" if trade_date else None
    kept: list[str] = []
    for sym in symbols:
        close_windows = [r.window for r in rules if r.type.startswith("close_")]
        cross_windows = [r.slow + 2 for r in rules if "cross" in r.type]
        max_count = 0
        if close_windows:
            max_count = max(max_count, max(close_windows))
        if cross_windows:
            max_count = max(max_count, max(cross_windows))
        if max_count < 2:
            kept.append(sym)
            continue

        df = gm_data.fetch_history_n(sym, count=max_count + 5, end_time=end_time)
        if df.empty or "close" not in df.columns:
            continue
        closes = df["close"].astype(float)
        ok = True
        for rule in rules:
            if rule.type == "close_above_ma":
                ma = closes.rolling(rule.window).mean()
                if ma.iloc[-1] != ma.iloc[-1]:
                    ok = False
                    break
                if closes.iloc[-1] <= ma.iloc[-1]:
                    ok = False
                    break
            elif rule.type == "close_below_ma":
                ma = closes.rolling(rule.window).mean()
                if closes.iloc[-1] >= ma.iloc[-1]:
                    ok = False
                    break
            elif rule.type == "ma_cross_up":
                fast = closes.rolling(rule.fast).mean()
                slow = closes.rolling(rule.slow).mean()
                if len(fast) < 2:
                    ok = False
                    break
                if not (fast.iloc[-2] <= slow.iloc[-2] and fast.iloc[-1] > slow.iloc[-1]):
                    ok = False
                    break
            elif rule.type == "ma_cross_down":
                fast = closes.rolling(rule.fast).mean()
                slow = closes.rolling(rule.slow).mean()
                if len(fast) < 2:
                    ok = False
                    break
                if not (fast.iloc[-2] >= slow.iloc[-2] and fast.iloc[-1] < slow.iloc[-1]):
                    ok = False
                    break
        if ok:
            kept.append(sym)
    return kept


def apply_filters(df: pd.DataFrame, rules: list) -> pd.DataFrame:
    if df.empty:
        return df
    out = df
    for rule in rules:
        col = rule.metric
        if col not in out.columns:
            continue
        series = pd.to_numeric(out[col], errors="coerce")
        mask = pd.Series(True, index=out.index)
        if rule.op == "eq" and rule.value is not None:
            mask &= series == rule.value
        elif rule.op == "neq" and rule.value is not None:
            mask &= series != rule.value
        elif rule.op == "gt" and rule.value is not None:
            mask &= series > rule.value
        elif rule.op == "gte" and rule.value is not None:
            mask &= series >= rule.value
        elif rule.op == "lt" and rule.value is not None:
            mask &= series < rule.value
        elif rule.op == "lte" and rule.value is not None:
            mask &= series <= rule.value
        elif rule.op == "between":
            lo, hi = rule.min, rule.max
            if lo is not None:
                mask &= series >= lo
            if hi is not None:
                mask &= series <= hi
        out = out.loc[mask]
    return out
