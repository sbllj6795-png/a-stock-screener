from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]


def project_root() -> Path:
    return _ROOT


def load_env() -> None:
    env_path = project_root() / ".env"
    if env_path.is_file():
        load_dotenv(env_path)
    else:
        load_dotenv()


def gm_token() -> str:
    load_env()
    token = os.environ.get("GM_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "未设置 GM_TOKEN。请复制 .env.example 为 .env 并填入东财掘金密钥。"
        )
    return token


def gm_serv_addr() -> str | None:
    """局域网掘金终端地址，例如 192.168.1.10:7001（Linux 远程取数必填）。"""
    load_env()
    raw = os.environ.get("GM_SERV_ADDR", "").strip()
    return raw or None
