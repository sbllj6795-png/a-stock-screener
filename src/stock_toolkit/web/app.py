from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import yaml

from stock_toolkit.backtest.engine import BacktestConfig, load_backtest_job, run_backtest
from stock_toolkit.backtest.skdj_engine import SkdjBacktestParams, run_skdj_backtest
from stock_toolkit.config import project_root
from stock_toolkit.screener.engine import run_screen
from stock_toolkit.screener.rules import ScreenConfig, UniverseConfig, load_screen_config

WEB_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))

app = FastAPI(title="A 股筛选器", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")


def list_configs() -> list[str]:
    cfg_dir = project_root() / "configs"
    return sorted(p.name for p in cfg_dir.glob("*.yaml"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "configs": list_configs(),
            "default_screen": "default_screen.yaml",
            "default_backtest": "example_backtest.yaml",
        },
    )


@app.post("/api/screen")
async def api_screen(payload: dict):
    try:
        if payload.get("config_file"):
            cfg = load_screen_config(project_root() / "configs" / payload["config_file"])
        else:
            cfg = _screen_from_payload(payload)
        result = run_screen(cfg)
        return {
            "name": result.config_name,
            "trade_date": result.trade_date,
            "symbols": result.symbols,
            "rows": result.table.to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/backtest")
async def api_backtest(payload: dict):
    try:
        config_name = payload.get("config")
        if config_name:
            path = project_root() / "configs" / config_name
            screen_cfg, bt_cfg = load_backtest_job(path)
        else:
            screen_cfg = _screen_from_payload(payload.get("screen", {}))
            b = payload.get("backtest", {})
            bt_cfg = BacktestConfig(
                start=b["start"],
                end=b["end"],
                initial_cash=float(b.get("initial_cash", 1_000_000)),
                top_n=int(b.get("top_n", 10)),
                rebalance=str(b.get("rebalance", "1M")),
                commission=float(b.get("commission", 0.0003)),
                slippage=float(b.get("slippage", 0.0001)),
            )
        result = run_backtest(screen_cfg, bt_cfg)
        equity = [
            {"date": t.strftime("%Y-%m-%d"), "equity": float(v)}
            for t, v in result.equity_curve.items()
        ]
        return {
            "stats": result.stats,
            "equity": equity,
            "rebalance_log": result.rebalance_log,
            "trades": result.trades.to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/skdj-backtest")
async def api_skdj_backtest(payload: dict):
    try:
        p = SkdjBacktestParams(
            symbol=str(payload.get("symbol", "600000")),
            start=str(payload["start"]),
            end=str(payload["end"]),
            initial_cash=float(payload.get("initial_cash", 100_000)),
            commission=float(payload.get("commission", 0.00015)),
            n=int(payload.get("n", 9)),
            m1=int(payload.get("m1", 3)),
            m2=int(payload.get("m2", 3)),
            buy_k_below=float(payload.get("buy_k_below", 20)),
            buy_d_below=float(payload.get("buy_d_below", 20)),
            buy_diff_target=float(payload.get("buy_diff_target", 0)),
            buy_diff_tol=float(payload.get("buy_diff_tol", 2)),
            sell_kd_diff_below=float(payload.get("sell_kd_diff_below", 3)),
        )
        return run_skdj_backtest(p)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"缺少字段: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/config/{name}")
async def get_config(name: str):
    path = project_root() / "configs" / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="config not found")
    return JSONResponse(content=yaml.safe_load(path.read_text(encoding="utf-8")))


def _screen_from_payload(payload: dict) -> ScreenConfig:
    if payload.get("config_file"):
        return load_screen_config(project_root() / "configs" / payload["config_file"])
    u = payload.get("universe", {"type": "index_constituents", "index": "SHSE.000300"})
    return ScreenConfig(
        name=payload.get("name", "web"),
        trade_date=payload.get("trade_date"),
        universe=UniverseConfig(
            type=u.get("type", "index_constituents"),
            index=u.get("index"),
            symbols=u.get("symbols"),
        ),
        filters=[],
        technical=[],
        sort_by=None,
        limit=payload.get("limit"),
    )


def main() -> None:
    uvicorn.run(
        "stock_toolkit.web.app:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
    )


if __name__ == "__main__":
    main()
