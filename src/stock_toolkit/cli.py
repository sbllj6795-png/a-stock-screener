from __future__ import annotations

import argparse
import json
import sys

from stock_toolkit.backtest.engine import load_backtest_job, run_backtest as execute_backtest
from stock_toolkit.config import project_root
from stock_toolkit.screener.rules import load_screen_config
from stock_toolkit.screener.engine import run_screen as execute_screen


def run_screen_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="运行 A 股筛选")
    parser.add_argument(
        "--config",
        default=str(project_root() / "configs/default_screen.yaml"),
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)
    cfg = load_screen_config(args.config)
    result = execute_screen(cfg)
    if args.json:
        payload = {
            "name": result.config_name,
            "trade_date": result.trade_date,
            "symbols": result.symbols,
            "rows": result.table.to_dict(orient="records"),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"# {result.config_name} @ {result.trade_date}")
        print(result.table.to_string(index=False))
    return 0


def run_backtest_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="筛选 + 组合回测")
    parser.add_argument(
        "--config",
        default=str(project_root() / "configs/example_backtest.yaml"),
    )
    args = parser.parse_args(argv)
    screen_cfg, bt_cfg = load_backtest_job(args.config)
    result = execute_backtest(screen_cfg, bt_cfg)
    print("回测统计:")
    for k, v in result.stats.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    if not result.equity_curve.empty:
        print("\n净值曲线（最近 5 行）:")
        print(result.equity_curve.tail().to_string())
    return 0


def run_screen() -> None:
    raise SystemExit(run_screen_main())


def run_backtest() -> None:
    raise SystemExit(run_backtest_main())
