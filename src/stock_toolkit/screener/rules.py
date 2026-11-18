from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

Op = Literal["eq", "neq", "gt", "gte", "lt", "lte", "between"]


@dataclass
class UniverseConfig:
    type: Literal["all_a", "index_constituents", "symbols"]
    index: str | None = None
    symbols: list[str] | None = None


@dataclass
class FilterRule:
    metric: str
    op: Op
    value: float | None = None
    min: float | None = None
    max: float | None = None


@dataclass
class TechnicalRule:
    type: Literal["close_above_ma", "close_below_ma", "ma_cross_up", "ma_cross_down"]
    window: int = 20
    fast: int = 5
    slow: int = 20


@dataclass
class SortConfig:
    field: str
    ascending: bool = True


@dataclass
class ScreenConfig:
    name: str
    trade_date: str | None
    universe: UniverseConfig
    filters: list[FilterRule]
    technical: list[TechnicalRule]
    sort_by: SortConfig | None
    limit: int | None


def _parse_universe(raw: dict[str, Any]) -> UniverseConfig:
    return UniverseConfig(
        type=raw.get("type", "index_constituents"),
        index=raw.get("index"),
        symbols=raw.get("symbols"),
    )


def load_screen_config(path: str | Path) -> ScreenConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    filters = [
        FilterRule(
            metric=f["metric"],
            op=f["op"],
            value=f.get("value"),
            min=f.get("min"),
            max=f.get("max"),
        )
        for f in data.get("filters", [])
    ]
    technical = [
        TechnicalRule(
            type=t["type"],
            window=int(t.get("window", 20)),
            fast=int(t.get("fast", 5)),
            slow=int(t.get("slow", 20)),
        )
        for t in data.get("technical", [])
    ]
    sort_raw = data.get("sort_by")
    sort_by = None
    if sort_raw:
        sort_by = SortConfig(
            field=sort_raw["field"],
            ascending=bool(sort_raw.get("ascending", True)),
        )
    return ScreenConfig(
        name=data.get("name", "screen"),
        trade_date=data.get("trade_date"),
        universe=_parse_universe(data.get("universe", {})),
        filters=filters,
        technical=technical,
        sort_by=sort_by,
        limit=data.get("limit"),
    )
