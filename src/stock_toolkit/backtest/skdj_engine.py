from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from stock_toolkit.data import gm_data
from stock_toolkit.indicators.skdj import compute_skdj, diff_near


@dataclass
class SkdjBacktestParams:
    symbol: str
    start: str
    end: str
    initial_cash: float = 100_000.0
    commission: float = 0.00015
    n: int = 9
    m1: int = 3
    m2: int = 3
    buy_k_below: float = 20.0
    buy_d_below: float = 20.0
    buy_diff_target: float = 0.0
    buy_diff_tol: float = 2.0
    sell_kd_diff_below: float = 3.0


def normalize_symbol(code: str) -> str:
    code = code.strip().upper().replace(" ", "")
    if code.startswith("SHSE.") or code.startswith("SZSE."):
        return code
    if "." in code:
        sym, exch = code.split(".", 1)
        if exch in ("SH", "XSHG", "SS"):
            return f"SHSE.{sym}"
        if exch in ("SZ", "XSHE"):
            return f"SZSE.{sym}"
    digits = "".join(c for c in code if c.isdigit())
    if len(digits) != 6:
        raise ValueError(f"无法识别股票代码: {code}")
    if digits.startswith(("5", "6", "9")) or digits.startswith("68"):
        return f"SHSE.{digits}"
    return f"SZSE.{digits}"


def _buy_signal(k, d, p: SkdjBacktestParams) -> bool:
    if pd.isna(k) or pd.isna(d):
        return False
    if float(k) >= p.buy_k_below or float(d) >= p.buy_d_below:
        return False
    return diff_near(k, d, p.buy_diff_target, p.buy_diff_tol)


def _sell_signal(k, d, p: SkdjBacktestParams) -> bool:
    if pd.isna(k) or pd.isna(d):
        return False
    fk, fd = float(k), float(d)
    return fk < fd and abs(fk - fd) < p.sell_kd_diff_below


def run_skdj_backtest(p: SkdjBacktestParams) -> dict:
    symbol = normalize_symbol(p.symbol)
    bars = gm_data.fetch_daily_bars(symbol, p.start, p.end)
    if bars.empty:
        raise ValueError(f"未取到 {symbol} 的行情数据")

    sk = compute_skdj(bars["high"], bars["low"], bars["close"], p.n, p.m1, p.m2)
    bars = bars.join(sk)

    cash = p.initial_cash
    shares = 0.0
    in_position = False
    trades: list[dict] = []
    equity_curve: list[dict] = []

    for idx, row in bars.iterrows():
        date_str = pd.Timestamp(idx).strftime("%Y-%m-%d")
        price = float(row["close"])
        k, d = row["k"], row["d"]

        if not in_position and _buy_signal(k, d, p):
            fee_rate = p.commission
            max_shares = int(cash / (price * (1 + fee_rate)) / 100) * 100
            if max_shares >= 100:
                amount = max_shares * price
                fee = amount * fee_rate
                cash -= amount + fee
                shares = float(max_shares)
                in_position = True
                trades.append(
                    {
                        "date": date_str,
                        "side": "buy",
                        "price": price,
                        "shares": max_shares,
                        "fee": round(fee, 4),
                        "k": round(float(k), 4),
                        "d": round(float(d), 4),
                        "cash_after": round(cash, 2),
                    }
                )
        elif in_position and _sell_signal(k, d, p):
            amount = shares * price
            fee = amount * p.commission
            cash += amount - fee
            trades.append(
                {
                    "date": date_str,
                    "side": "sell",
                    "price": price,
                    "shares": int(shares),
                    "fee": round(fee, 4),
                    "k": round(float(k), 4),
                    "d": round(float(d), 4),
                    "cash_after": round(cash, 2),
                }
            )
            shares = 0.0
            in_position = False

        equity = cash + shares * price
        equity_curve.append({"date": date_str, "equity": round(equity, 2)})

    final_equity = equity_curve[-1]["equity"] if equity_curve else p.initial_cash
    total_return = final_equity / p.initial_cash - 1.0

    ohlc = []
    for idx, row in bars.iterrows():
        ohlc.append(
            {
                "date": pd.Timestamp(idx).strftime("%Y-%m-%d"),
                "open": round(float(row["open"]), 4),
                "high": round(float(row["high"]), 4),
                "low": round(float(row["low"]), 4),
                "close": round(float(row["close"]), 4),
                "k": round(float(row["k"]), 4) if pd.notna(row["k"]) else None,
                "d": round(float(row["d"]), 4) if pd.notna(row["d"]) else None,
                "j": round(float(row["j"]), 4) if pd.notna(row["j"]) else None,
            }
        )

    return {
        "symbol": symbol,
        "params": asdict(p),
        "ohlc": ohlc,
        "trades": trades,
        "equity": equity_curve,
        "summary": {
            "initial_cash": p.initial_cash,
            "final_equity": final_equity,
            "total_return": round(total_return, 6),
            "total_return_pct": round(total_return * 100, 4),
            "trade_count": len(trades),
            "commission_rate": p.commission,
        },
    }
