from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

from stock_toolkit.backtest import metrics
from stock_toolkit.data import gm_data
from stock_toolkit.screener.engine import run_screen
from stock_toolkit.screener.rules import ScreenConfig, load_screen_config


@dataclass
class BacktestConfig:
    start: str
    end: str
    initial_cash: float
    top_n: int
    rebalance: str
    commission: float
    slippage: float


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trades: pd.DataFrame
    stats: dict[str, float]
    rebalance_log: list[dict]


def load_backtest_job(path: str | Path) -> tuple[ScreenConfig, BacktestConfig]:
    from stock_toolkit.config import project_root

    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    screen_ref = Path(raw["screen"])
    candidates = [
        Path(path).parent / screen_ref.name,
        Path(path).parent / screen_ref,
        project_root() / screen_ref,
        screen_ref,
    ]
    screen_path = next((p for p in candidates if p.is_file()), candidates[-1])
    screen = load_screen_config(screen_path)
    b = raw["backtest"]
    bt = BacktestConfig(
        start=b["start"],
        end=b["end"],
        initial_cash=float(b.get("initial_cash", 1_000_000)),
        top_n=int(b.get("top_n", 10)),
        rebalance=str(b.get("rebalance", "1M")),
        commission=float(b.get("commission", 0.0003)),
        slippage=float(b.get("slippage", 0.0001)),
    )
    return screen, bt


def _rebalance_dates(index: pd.DatetimeIndex, freq: str) -> pd.DatetimeIndex:
    rule = {"1M": "MS", "1W": "W-MON"}.get(freq, freq)
    starts = pd.date_range(index.min(), index.max(), freq=rule)
    return index[index.isin(starts) | (index == index[0])]


def run_backtest(screen_template: ScreenConfig, bt: BacktestConfig) -> BacktestResult:
    """Monthly screen + equal-weight; prices from first rebalance symbols union."""
    probe = ScreenConfig(
        name=screen_template.name,
        trade_date=bt.start,
        universe=screen_template.universe,
        filters=screen_template.filters,
        technical=[],
        sort_by=screen_template.sort_by,
        limit=screen_template.limit,
    )
    first = run_screen(probe)
    if not first.symbols:
        empty = pd.Series(dtype=float)
        return BacktestResult(empty, pd.DataFrame(), {}, [])

    all_syms: set[str] = set()
    rebalance_log: list[dict] = []
    idx_guess = pd.date_range(bt.start, bt.end, freq="B")

    for d in _rebalance_dates(idx_guess, bt.rebalance):
        td = d.strftime("%Y-%m-%d")
        cfg = ScreenConfig(
            name=screen_template.name,
            trade_date=td,
            universe=screen_template.universe,
            filters=screen_template.filters,
            technical=screen_template.technical,
            sort_by=screen_template.sort_by,
            limit=bt.top_n,
        )
        try:
            res = run_screen(cfg)
        except Exception:
            continue
        picks = res.symbols[: bt.top_n]
        all_syms.update(picks)
        rebalance_log.append({"date": td, "symbols": picks})

    prices = gm_data.fetch_daily_closes(sorted(all_syms), bt.start, bt.end)
    if prices.empty:
        empty = pd.Series(dtype=float)
        return BacktestResult(empty, pd.DataFrame(), {}, rebalance_log)

    prices = prices.loc[(prices.index >= bt.start) & (prices.index <= bt.end)]
    cash = bt.initial_cash
    holdings: dict[str, float] = {}
    equity_rows: list[tuple[pd.Timestamp, float]] = []
    trades: list[dict] = []
    rebal_map = {row["date"]: row["symbols"] for row in rebalance_log}

    for dt, row in prices.iterrows():
        date_str = dt.strftime("%Y-%m-%d")
        if date_str in rebal_map:
            targets = rebal_map[date_str]
            valid = [s for s in targets if s in row.index and pd.notna(row[s])]
            port_value = cash + sum(
                holdings.get(s, 0) * float(row[s]) for s in holdings if s in row.index and pd.notna(row[s])
            )
            holdings = {}
            cash = port_value
            if valid:
                weight = 1.0 / len(valid)
                for s in valid:
                    px = float(row[s]) * (1 + bt.slippage)
                    gross = port_value * weight
                    fee = gross * bt.commission
                    net = gross - fee
                    shares = net / px
                    cash -= gross
                    holdings[s] = shares
                    trades.append(
                        {
                            "date": date_str,
                            "symbol": s,
                            "side": "buy",
                            "price": px,
                            "shares": shares,
                            "fee": fee,
                        }
                    )
        port_value = cash + sum(
            holdings.get(s, 0) * float(row[s])
            for s in holdings
            if s in row.index and pd.notna(row[s])
        )
        equity_rows.append((dt, port_value))

    equity = pd.Series(
        {t: v for t, v in equity_rows},
        name="equity",
    ).sort_index()
    daily_rets = equity.pct_change().dropna()
    stats = {
        "total_return": float(equity.iloc[-1] / equity.iloc[0] - 1) if len(equity) > 1 else 0.0,
        "annualized_return": metrics.annualized_return(equity),
        "max_drawdown": metrics.max_drawdown(equity),
        "sharpe": metrics.sharpe_ratio(daily_rets),
        "final_equity": float(equity.iloc[-1]) if len(equity) else 0.0,
    }
    trades_df = pd.DataFrame(trades)
    return BacktestResult(equity, trades_df, stats, rebalance_log)
