function renderTable(rows, el) {
  if (!rows || !rows.length) {
    el.innerHTML = "<p class='muted'>无结果</p>";
    return;
  }
  const cols = Object.keys(rows[0]);
  const head = cols.map((c) => `<th>${c}</th>`).join("");
  const body = rows
    .map((r) => `<tr>${cols.map((c) => `<td>${r[c] ?? ""}</td>`).join("")}</tr>`)
    .join("");
  el.innerHTML = `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function drawEquity(points) {
  const canvas = document.getElementById("equity-chart");
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  if (!points.length) return;

  const vals = points.map((p) => p.equity);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const pad = 12;
  ctx.strokeStyle = "#3d8bfd";
  ctx.lineWidth = 2;
  ctx.beginPath();
  points.forEach((p, i) => {
    const x = pad + (i / (points.length - 1 || 1)) * (w - 2 * pad);
    const y = h - pad - ((p.equity - min) / (max - min || 1)) * (h - 2 * pad);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

document.getElementById("btn-screen").addEventListener("click", async () => {
  const btn = document.getElementById("btn-screen");
  const out = document.getElementById("screen-out");
  const table = document.getElementById("screen-table");
  btn.disabled = true;
  out.textContent = "运行中…";
  try {
    const config_file = document.getElementById("screen-config").value;
    const data = await postJson("/api/screen", { config_file });
    out.textContent = `${data.name} @ ${data.trade_date}\n${data.symbols.length} 只股票`;
    renderTable(data.rows, table);
  } catch (e) {
    out.textContent = String(e.message || e);
    table.innerHTML = "";
  } finally {
    btn.disabled = false;
  }
});

let skdjChart = null;

function skdjPayload() {
  return {
    symbol: document.getElementById("sk-symbol").value,
    start: document.getElementById("sk-start").value,
    end: document.getElementById("sk-end").value,
    initial_cash: Number(document.getElementById("sk-cash").value),
    commission: 0.00015,
    n: Number(document.getElementById("sk-n").value),
    m1: Number(document.getElementById("sk-m1").value),
    m2: Number(document.getElementById("sk-m2").value),
    buy_k_below: Number(document.getElementById("sk-buy-k").value),
    buy_d_below: Number(document.getElementById("sk-buy-d").value),
    buy_diff_target: Number(document.getElementById("sk-buy-diff-t").value),
    buy_diff_tol: Number(document.getElementById("sk-buy-diff-tol").value),
    sell_kd_diff_below: Number(document.getElementById("sk-sell-kd-tol").value),
  };
}

function renderSkdjCharts(data) {
  const el = document.getElementById("skdj-chart");
  if (!skdjChart) skdjChart = echarts.init(el);
  const dates = data.ohlc.map((b) => b.date);
  const kline = data.ohlc.map((b) => [b.open, b.close, b.low, b.high]);
  const ks = data.ohlc.map((b) => b.k);
  const ds = data.ohlc.map((b) => b.d);

  const markPoints = data.trades.map((t) => ({
    name: t.side === "buy" ? "买" : "卖",
    coord: [t.date, t.price],
    value: t.side === "buy" ? "买" : "卖",
    itemStyle: { color: t.side === "buy" ? "#26a69a" : "#ef5350" },
  }));

  skdjChart.setOption(
    {
      backgroundColor: "transparent",
      animation: false,
      tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
      axisPointer: { link: [{ xAxisIndex: [0, 1] }] },
      grid: [
        { left: 56, right: 24, top: 48, height: "48%" },
        { left: 56, right: 24, top: "62%", height: "30%" },
      ],
      xAxis: [
        { type: "category", data: dates, boundaryGap: true, axisLine: { lineStyle: { color: "#8b9cb3" } } },
        { type: "category", gridIndex: 1, data: dates, boundaryGap: true, axisLine: { lineStyle: { color: "#8b9cb3" } } },
      ],
      yAxis: [
        { scale: true, splitLine: { lineStyle: { color: "#2a3548" } } },
        { scale: true, gridIndex: 1, splitLine: { lineStyle: { color: "#2a3548" } }, min: 0, max: 100 },
      ],
      dataZoom: [
        { type: "inside", xAxisIndex: [0, 1] },
        { type: "slider", xAxisIndex: [0, 1], bottom: 8 },
      ],
      series: [
        {
          name: "K线",
          type: "candlestick",
          data: kline,
          itemStyle: { color: "#ef5350", color0: "#26a69a", borderColor: "#ef5350", borderColor0: "#26a69a" },
          markPoint: { data: markPoints, symbolSize: 42, label: { color: "#fff", fontSize: 11 } },
        },
        { name: "K", type: "line", xAxisIndex: 1, yAxisIndex: 1, data: ks, showSymbol: false, lineStyle: { width: 1.5, color: "#f6c343" } },
        { name: "D", type: "line", xAxisIndex: 1, yAxisIndex: 1, data: ds, showSymbol: false, lineStyle: { width: 1.5, color: "#3d8bfd" } },
      ],
    },
    true
  );
}

document.getElementById("btn-skdj").addEventListener("click", async () => {
  const btn = document.getElementById("btn-skdj");
  const summary = document.getElementById("skdj-summary");
  const tradesEl = document.getElementById("skdj-trades");
  btn.disabled = true;
  summary.textContent = "拉取行情并回测中…";
  tradesEl.innerHTML = "";
  try {
    const data = await postJson("/api/skdj-backtest", skdjPayload());
    const s = data.summary;
    summary.textContent = [
      `${data.symbol}  SKDJ 回测`,
      `总收益: ${(s.total_return_pct).toFixed(2)}%  期末权益: ${s.final_equity}  交易次数: ${s.trade_count}`,
      `手续费率: 万分之 ${(s.commission_rate * 10000).toFixed(1)}`,
    ].join("\n");
    renderSkdjCharts(data);
    renderTable(data.trades, tradesEl);
  } catch (e) {
    summary.textContent = String(e.message || e);
    if (skdjChart) skdjChart.clear();
    tradesEl.innerHTML = "";
  } finally {
    btn.disabled = false;
  }
});

window.addEventListener("resize", () => skdjChart && skdjChart.resize());

document.getElementById("btn-backtest").addEventListener("click", async () => {
  const btn = document.getElementById("btn-backtest");
  const statsEl = document.getElementById("bt-stats");
  btn.disabled = true;
  statsEl.textContent = "回测中（会多次调用 gm，请耐心等待）…";
  try {
    const config = document.getElementById("bt-config").value;
    const data = await postJson("/api/backtest", { config });
    statsEl.textContent = JSON.stringify(data.stats, null, 2);
    drawEquity(data.equity || []);
  } catch (e) {
    statsEl.textContent = String(e.message || e);
    drawEquity([]);
  } finally {
    btn.disabled = false;
  }
});
