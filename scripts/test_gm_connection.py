#!/usr/bin/env python3
"""Quick check: Ubuntu/Linux can reach a LAN Windows 掘金 terminal."""

from __future__ import annotations

import socket
import sys

from stock_toolkit.config import gm_serv_addr, gm_token


def main() -> int:
    token = gm_token()
    addr = gm_serv_addr()
    if not addr:
        print("未设置 GM_SERV_ADDR（例如 192.168.1.10:7001）", file=sys.stderr)
        return 1

    host, _, port_s = addr.partition(":")
    port = int(port_s or "7001")
    print(f"探测 TCP {host}:{port} ...")
    try:
        with socket.create_connection((host, port), timeout=3):
            print("端口可达。")
    except OSError as e:
        print(f"无法连接终端服务: {e}", file=sys.stderr)
        print("请确认 Windows 终端已打开、IP 正确、防火墙已放行。", file=sys.stderr)
        return 1

    from gm.api import history, set_serv_addr, set_token  # type: ignore

    set_serv_addr(addr)
    set_token(token)
    df = history(
        symbol="SHSE.600000",
        frequency="1d",
        start_time="2024-01-01 09:00:00",
        end_time="2024-01-31 16:00:00",
        fields="close,eob",
        df=True,
    )
    if df is None or len(df) == 0:
        print("gm history 返回空，请检查 token 与终端登录状态。", file=sys.stderr)
        return 1
    print(f"gm 取数成功，浦发银行日线 {len(df)} 条，末条收盘: {df.iloc[-1]['close']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
