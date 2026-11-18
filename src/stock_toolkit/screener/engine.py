from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from stock_toolkit.data import gm_data
from stock_toolkit.screener import indicators
from stock_toolkit.screener.rules import ScreenConfig


@dataclass
class ScreenResult:
    config_name: str
    trade_date: str | None
    symbols: list[str]
    table: pd.DataFrame


def _universe_symbols(cfg: ScreenConfig) -> list[str]:
    u = cfg.universe
    td = cfg.trade_date
    if u.type == "all_a":
        return gm_data.list_a_share_symbols(trade_date=td)
    if u.type == "symbols" and u.symbols:
        return list(u.symbols)
    if u.type == "index_constituents" and u.index:
        return gm_data.index_constituents(u.index, trade_date=td)
    raise ValueError(f"无效 universe 配置: {u}")


def _fields_needed(cfg: ScreenConfig) -> tuple[set[str], set[str], set[str]]:
    val: set[str] = set()
    mkt: set[str] = set()
    basic: set[str] = set()
    valuation_like = {"pe_ttm", "pe_lyr", "pe_mrq", "pb", "pb_mrq", "ps_ttm"}
    mkt_like = {"tot_mv", "tot_mv_csrc", "a_mv", "negotiable_mv"}
    basic_like = {"turnrate", "tclose", "ttl_shr", "circ_shr"}
    for f in cfg.filters:
        if f.metric in valuation_like:
            val.add(f.metric)
        elif f.metric in mkt_like:
            mkt.add(f.metric)
        elif f.metric in basic_like:
            basic.add(f.metric)
        else:
            val.add(f.metric)
    if cfg.sort_by:
        field = cfg.sort_by.field
        if field in valuation_like:
            val.add(field)
        elif field in mkt_like:
            mkt.add(field)
        elif field in basic_like:
            basic.add(field)
        else:
            val.add(field)
    return val, mkt, basic


def run_screen(cfg: ScreenConfig) -> ScreenResult:
    symbols = _universe_symbols(cfg)
    val, mkt, basic = _fields_needed(cfg)
    table = gm_data.fetch_cross_section(
        symbols,
        trade_date=cfg.trade_date,
        valuation_fields=val,
        mktvalue_fields=mkt,
        basic_fields=basic,
    )
    if table.empty:
        return ScreenResult(cfg.name, cfg.trade_date, [], table)

    if "trade_date" in table.columns and cfg.trade_date is None:
        cfg_trade = str(table["trade_date"].iloc[0])
    else:
        cfg_trade = cfg.trade_date

    filtered = indicators.apply_filters(table, cfg.filters)
    sym_list = filtered["symbol"].astype(str).tolist() if "symbol" in filtered.columns else []
    sym_list = indicators.apply_technical(sym_list, cfg_trade, cfg.technical)

    if "symbol" in filtered.columns:
        filtered = filtered[filtered["symbol"].astype(str).isin(sym_list)]
    if cfg.sort_by and cfg.sort_by.field in filtered.columns:
        filtered = filtered.sort_values(
            cfg.sort_by.field, ascending=cfg.sort_by.ascending, na_position="last"
        )
    if cfg.limit:
        filtered = filtered.head(cfg.limit)
        sym_list = filtered["symbol"].astype(str).tolist()

    return ScreenResult(cfg.name, cfg_trade, sym_list, filtered.reset_index(drop=True))
