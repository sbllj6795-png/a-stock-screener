from __future__ import annotations

from functools import lru_cache
from typing import Iterable, Sequence

import pandas as pd

from stock_toolkit.config import gm_serv_addr, gm_token

_CHUNK = 80


def _ensure_gm():
    try:
        from gm.api import set_serv_addr, set_token  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "未安装 gm。请执行: pip install gm -U -i https://mirrors.aliyun.com/pypi/simple/"
        ) from e
    addr = gm_serv_addr()
    if addr:
        set_serv_addr(addr)
    set_token(gm_token())


@lru_cache(maxsize=1)
def _gm_ready() -> bool:
    _ensure_gm()
    return True


def chunk_symbols(symbols: Sequence[str], size: int = _CHUNK) -> list[list[str]]:
    return [list(symbols[i : i + size]) for i in range(0, len(symbols), size)]


def list_a_share_symbols(trade_date: str | None = None) -> list[str]:
    _gm_ready()
    from gm.api import get_symbols  # type: ignore

    df = get_symbols(
        sec_type1=1010,
        sec_type2=101001,
        skip_suspended=True,
        skip_st=True,
        trade_date=trade_date,
        df=True,
    )
    if df is None or df.empty:
        return []
    return df["symbol"].astype(str).tolist()


def index_constituents(index: str, trade_date: str | None = None) -> list[str]:
    _gm_ready()
    from gm.api import stk_get_index_constituents  # type: ignore

    result = stk_get_index_constituents(index=index, trade_date=trade_date)
    if isinstance(result, pd.DataFrame):
        if result.empty:
            return []
        col = "symbol" if "symbol" in result.columns else result.columns[0]
        return result[col].astype(str).tolist()
    if not result:
        return []
    if isinstance(result, list):
        out: list[str] = []
        for row in result:
            if isinstance(row, dict):
                out.append(str(row.get("symbol", "")))
            else:
                out.append(str(row))
        return [s for s in out if s]
    return []


def fetch_cross_section(
    symbols: Sequence[str],
    trade_date: str | None,
    valuation_fields: Iterable[str] | None = None,
    mktvalue_fields: Iterable[str] | None = None,
    basic_fields: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Merge valuation / market value / basic metrics for one trade date."""
    _gm_ready()
    from gm.api import (  # type: ignore
        stk_get_daily_basic_pt,
        stk_get_daily_mktvalue_pt,
        stk_get_daily_valuation_pt,
    )

    if not symbols:
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []
    val_f = ",".join(valuation_fields or [])
    mv_f = ",".join(mktvalue_fields or [])
    basic_f = ",".join(basic_fields or [])

    for batch in chunk_symbols(list(symbols)):
        if val_f:
            df = stk_get_daily_valuation_pt(
                symbols=batch, fields=val_f, trade_date=trade_date, df=True
            )
            if isinstance(df, pd.DataFrame) and not df.empty:
                frames.append(df)
        if mv_f:
            df = stk_get_daily_mktvalue_pt(
                symbols=batch, fields=mv_f, trade_date=trade_date, df=True
            )
            if isinstance(df, pd.DataFrame) and not df.empty:
                frames.append(df)
        if basic_f:
            df = stk_get_daily_basic_pt(
                symbols=batch, fields=basic_f, trade_date=trade_date, df=True
            )
            if isinstance(df, pd.DataFrame) and not df.empty:
                frames.append(df)

    if not frames:
        return pd.DataFrame()

    merged = frames[0]
    for extra in frames[1:]:
        on = [c for c in ("symbol", "trade_date") if c in merged.columns and c in extra.columns]
        if not on:
            on = ["symbol"]
        dup = [c for c in extra.columns if c in merged.columns and c not in on]
        extra = extra.drop(columns=dup, errors="ignore")
        merged = merged.merge(extra, on=on, how="outer")

    return merged


def fetch_daily_bars(
    symbol: str,
    start: str,
    end: str,
) -> pd.DataFrame:
    """Daily OHLCV for one symbol."""
    _gm_ready()
    from gm.api import ADJUST_PREV, history  # type: ignore

    df = history(
        symbol=symbol,
        frequency="1d",
        start_time=f"{start} 09:00:00",
        end_time=f"{end} 16:00:00",
        fields="open,high,low,close,volume,eob",
        adjust=ADJUST_PREV,
        df=True,
    )
    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()
    out = df.set_index("eob").sort_index()
    out.index = pd.to_datetime(out.index)
    return out[["open", "high", "low", "close", "volume"]].astype(float, errors="ignore")


def fetch_daily_closes(
    symbols: Sequence[str],
    start: str,
    end: str,
) -> pd.DataFrame:
    """Wide DataFrame: index=datetime, columns=symbols, values=close."""
    _gm_ready()
    from gm.api import ADJUST_PREV, history  # type: ignore

    if not symbols:
        return pd.DataFrame()

    pieces: list[pd.DataFrame] = []
    for sym in symbols:
        df = history(
            symbol=sym,
            frequency="1d",
            start_time=f"{start} 09:00:00",
            end_time=f"{end} 16:00:00",
            fields="close,eob",
            adjust=ADJUST_PREV,
            df=True,
        )
        if not isinstance(df, pd.DataFrame) or df.empty:
            continue
        s = df.set_index("eob")["close"].rename(sym)
        pieces.append(s)

    if not pieces:
        return pd.DataFrame()
    out = pd.concat(pieces, axis=1).sort_index()
    out.index = pd.to_datetime(out.index)
    return out


def fetch_history_n(
    symbol: str,
    count: int,
    end_time: str | None = None,
    fields: str = "close",
) -> pd.DataFrame:
    _gm_ready()
    from gm.api import ADJUST_PREV, history_n  # type: ignore

    kwargs: dict = {
        "symbol": symbol,
        "frequency": "1d",
        "count": count,
        "fields": fields,
        "adjust": ADJUST_PREV,
        "df": True,
    }
    if end_time:
        kwargs["end_time"] = end_time
    df = history_n(**kwargs)
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()
    return df
