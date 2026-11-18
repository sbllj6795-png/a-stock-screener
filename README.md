# A 股筛选器 + 回测

基于 [东财掘金 Python SDK（`gm`）](https://emquant.18.cn/help/doc/python/quickstart.html) 的 A 股条件筛选与简易组合回测，带 Web 界面。

## 前置条件

1. [东财掘金终端](https://emquant.18.cn/) **已登录并保持运行**（本机 Windows，或局域网内另一台 Windows）。
2. 在终端 **系统设置 → 密钥管理** 创建 `token`。
3. Python 3.10+。

### Ubuntu 通过局域网连接 Windows 终端

你可以在 Ubuntu 上跑本项目，数据仍走 `gm`，终端开在局域网里的 Windows 电脑上即可。

1. **Windows**：安装掘金并登录；在 `cmd` 执行 `ipconfig`，记下内网 IPv4（如 `192.168.1.10`）。若开了防火墙，需放行 **7001–7004** 等端口（见[官方 FAQ](https://www.myquant.cn/docs2/faq/)）。
2. **Ubuntu**：`pip install gm`，在 `.env` 中配置：
   - `GM_TOKEN=...`（与 Windows 终端同一账号密钥）
   - `GM_SERV_ADDR=192.168.1.10:7001`
3. **连通性自测**：

```bash
python scripts/test_gm_connection.py
```

官方说明：SDK 通过 `set_serv_addr` 指向终端；`run(..., serv_addr=...)` 用于策略回测模式。本项目取数在初始化时会自动调用 `set_serv_addr`（当设置了 `GM_SERV_ADDR`）。

可选：从 Windows 安装目录 `...\resources\app\gmserv.json` 复制到 Linux 的 `~/.goldminer3/` 并按文档改 `hostAddr`（部分环境需要，与 `set_serv_addr` 二选一或并存以官方文档为准）。

## 安装

```bash
cd ~/Projects/a-stock-screener
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install gm -U -i https://mirrors.aliyun.com/pypi/simple/
cp .env.example .env
# 编辑 .env，填入 GM_TOKEN
```

## 使用

### Web（推荐）

```bash
a-stock-web
# 浏览器打开 http://127.0.0.1:8765
```

### 命令行

```bash
a-stock-screen --config configs/default_screen.yaml
a-stock-backtest --config configs/example_backtest.yaml
```

## 筛选规则（YAML）

见 `configs/default_screen.yaml`。支持：

- 股票池：全 A、指数成分（如沪深 300）
- 截面指标：`pe_ttm`、`tot_mv`、`turnrate` 等（掘金 `stk_get_*_pt`）
- 技术条件：均线金叉/死叉、收盘价相对均线（对初筛后的标的拉日线计算）

## 回测说明

当前为 **定期调仓 + 等权持有** 的向量回测：

- 按 `rebalance`（如 `1M`）在交易日调仓
- 每个调仓日用当时的筛选条件选股，取前 `top_n` 只等权买入
- 用 `history` 拉日线收盘价，含简单手续费率

这不是掘金内置的 tick 级回测；后续可对接 `run(..., mode=MODE_BACKTEST)` 做更精细的策略回测。

## 免责声明

仅供学习研究，不构成投资建议。历史回测不代表未来收益。
