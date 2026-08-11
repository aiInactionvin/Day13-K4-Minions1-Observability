from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .analytics import build_dashboard_snapshot


app = FastAPI(title="Day 13 AI Observability Dashboard")


@app.get("/api/dashboard")
async def dashboard_data() -> dict:
    return build_dashboard_snapshot()


@app.get("/health")
async def dashboard_health() -> dict:
    snapshot = build_dashboard_snapshot()
    return {
        "ok": True,
        "records_in_window": snapshot["meta"]["records_in_window"],
        "skipped_lines": snapshot["meta"]["skipped_lines"],
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard_page() -> str:
    return DASHBOARD_HTML


DASHBOARD_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Day 13 AI Observability</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #071019;
      --surface: #0d1823;
      --surface-2: #132230;
      --line: #20394a;
      --text: #ecf7ff;
      --muted: #8ca6b8;
      --cyan: #32d6c5;
      --blue: #55a7ff;
      --amber: #ffbe55;
      --red: #ff6b6b;
      --green: #4ade80;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at 15% -10%, rgba(50,214,197,.13), transparent 35%),
        radial-gradient(circle at 90% 0%, rgba(85,167,255,.10), transparent 32%),
        var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    main { max-width: 1500px; margin: 0 auto; padding: 34px 32px 56px; }
    header { display: flex; justify-content: space-between; align-items: flex-start; gap: 24px; margin-bottom: 26px; }
    h1 { margin: 0; font-size: clamp(28px, 4vw, 48px); letter-spacing: -.045em; font-weight: 720; }
    .eyebrow { color: var(--cyan); text-transform: uppercase; letter-spacing: .16em; font-size: 12px; font-weight: 700; margin-bottom: 10px; }
    .subtitle { color: var(--muted); margin-top: 10px; max-width: 720px; line-height: 1.55; }
    .meta { display: grid; gap: 7px; justify-items: end; color: var(--muted); font-size: 13px; white-space: nowrap; }
    .live { display: flex; align-items: center; gap: 8px; color: var(--green); font-weight: 700; }
    .dot { width: 8px; height: 8px; background: var(--green); border-radius: 50%; box-shadow: 0 0 12px var(--green); }
    .summary { display: flex; align-items: center; gap: 12px; margin: 0 0 18px; color: var(--muted); font-size: 13px; }
    .summary strong { color: var(--text); font-size: 15px; }
    .grid { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 16px; }
    .card { grid-column: span 4; background: linear-gradient(150deg, rgba(19,34,48,.94), rgba(11,24,34,.96)); border: 1px solid var(--line); border-radius: 18px; padding: 20px; min-height: 225px; box-shadow: 0 18px 50px rgba(0,0,0,.18); }
    .card-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
    .card h2 { margin: 0; font-size: 15px; letter-spacing: -.01em; }
    .badge { border: 1px solid currentColor; border-radius: 99px; padding: 4px 8px; font-size: 10px; letter-spacing: .08em; text-transform: uppercase; font-weight: 800; }
    .healthy { color: var(--green); }
    .violated { color: var(--red); }
    .no_data, .unknown { color: var(--amber); }
    .primary { margin: 22px 0 6px; font-size: 38px; font-weight: 760; letter-spacing: -.04em; }
    .unit { font-size: 13px; color: var(--muted); margin-left: 5px; font-weight: 500; }
    .split { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 22px 0 16px; }
    .metric { padding: 10px 0; border-top: 1px solid var(--line); }
    .metric span { display: block; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .1em; }
    .metric strong { display: block; margin-top: 6px; font-size: 21px; }
    .target { color: var(--muted); font-size: 12px; margin-top: 11px; }
    .spark { height: 54px; margin-top: 14px; width: 100%; }
    .bar-track { height: 9px; background: #08121a; border-radius: 9px; overflow: hidden; margin-top: 14px; }
    .bar-fill { height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--cyan), var(--blue)); min-width: 2px; }
    .legend { display: flex; justify-content: space-between; color: var(--muted); font-size: 12px; margin-top: 9px; }
    .section { margin-top: 26px; background: rgba(13,24,35,.9); border: 1px solid var(--line); border-radius: 18px; overflow: hidden; }
    .section-title { padding: 18px 20px; border-bottom: 1px solid var(--line); display: flex; justify-content: space-between; align-items: center; }
    .section-title h2 { margin: 0; font-size: 16px; }
    .section-title span { color: var(--muted); font-size: 12px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th { color: var(--muted); text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: .1em; padding: 12px 20px; background: rgba(7,16,25,.55); }
    td { padding: 13px 20px; border-top: 1px solid rgba(32,57,74,.65); }
    td.number { text-align: right; font-variant-numeric: tabular-nums; }
    code { color: var(--cyan); font-family: "SFMono-Regular", Consolas, monospace; font-size: 12px; }
    .empty { color: var(--muted); padding: 26px 20px; }
    .error { margin-bottom: 18px; padding: 12px 14px; background: rgba(255,107,107,.12); color: #ffd0d0; border: 1px solid rgba(255,107,107,.4); border-radius: 12px; display: none; }
    @media (max-width: 980px) { .card { grid-column: span 6; } }
    @media (max-width: 680px) { main { padding: 24px 16px 40px; } header { flex-direction: column; } .meta { justify-items: start; } .card { grid-column: 1 / -1; } .section { overflow-x: auto; } table { min-width: 760px; } }
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <div class="eyebrow">AI system telemetry</div>
      <h1>Day 13 Observability</h1>
      <div class="subtitle">A sixty-minute operational view from structured JSON logs. Use metrics to detect the symptom, then follow a correlation ID into traces and logs.</div>
    </div>
    <div class="meta">
      <div class="live"><span class="dot"></span> Auto-refresh active</div>
      <div id="range">Time range: —</div>
      <div id="refresh">Refresh: —</div>
      <div id="updated">Updated: —</div>
    </div>
  </header>
  <div id="error" class="error"></div>
  <div class="summary"><strong id="health">Waiting for data</strong><span id="recordCount">—</span></div>
  <div class="grid" id="panels"></div>
  <section class="section">
    <div class="section-title"><h2>Investigation queue</h2><span>Slowest responses in the selected window</span></div>
    <div id="slowRequests"></div>
  </section>
</main>
<script>
  let refreshTimer;
  const number = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 });
  const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 4, maximumFractionDigits: 6 });
  const statusLabel = {healthy: 'Within SLO', violated: 'SLO breach', no_data: 'No data', unknown: 'Unknown'};
  const badge = status => `<span class="badge ${status}">${statusLabel[status] || status}</span>`;
  const target = threshold => `${threshold.aggregation} ${threshold.operator === 'lte' ? '≤' : '≥'} ${number.format(threshold.value)}`;
  const esc = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  function sparkline(values, color = '#32d6c5') {
    if (!values.length) return '<div class="empty">No time-series data yet</div>';
    const width = 280, height = 50, max = Math.max(...values, 1);
    const points = values.map((v, i) => `${values.length === 1 ? width / 2 : i * width / (values.length - 1)},${height - (v / max) * (height - 8) - 4}`).join(' ');
    return `<svg class="spark" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Metric trend"><line x1="0" y1="46" x2="280" y2="46" stroke="#20394a"/><polyline fill="none" stroke="${color}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" points="${points}"/></svg>`;
  }
  function panel(title, status, content, threshold) {
    return `<article class="card"><div class="card-head"><h2>${esc(title)}</h2>${badge(status)}</div>${content}<div class="target">Threshold: ${esc(target(threshold))}</div></article>`;
  }
  function render(data) {
    const p = data.panels;
    const healthy = Object.values(p).filter(panel => panel.status === 'healthy').length;
    const breached = Object.values(p).filter(panel => panel.status === 'violated').length;
    document.getElementById('health').textContent = breached ? `${breached} threshold${breached > 1 ? 's' : ''} breached` : `${healthy}/6 signals within threshold`;
    document.getElementById('health').className = breached ? 'violated' : 'healthy';
    document.getElementById('recordCount').textContent = `${data.meta.records_in_window} log records · ${data.meta.skipped_lines} malformed lines skipped`;
    document.getElementById('range').textContent = `Time range: last ${data.meta.time_range_minutes} minutes`;
    document.getElementById('refresh').textContent = `Refresh: ${data.meta.refresh_seconds} seconds`;
    document.getElementById('updated').textContent = `Updated: ${new Date(data.meta.generated_at).toLocaleTimeString()}`;
    const maxTokens = Math.max(p.tokens.tokens_in, p.tokens.tokens_out, 1);
    const errorBreakdown = Object.entries(p.errors.breakdown).map(([k,v]) => `${esc(k)}: ${v}`).join(' · ') || 'No errors recorded';
    const cards = [
      panel(p.latency.title, p.latency.status, `<div class="split"><div class="metric"><span>P50</span><strong>${number.format(p.latency.values.p50)}</strong></div><div class="metric"><span>P95</span><strong>${number.format(p.latency.values.p95)}</strong></div><div class="metric"><span>P99</span><strong>${number.format(p.latency.values.p99)}</strong></div></div><div class="legend"><span>${p.latency.sample_count} responses</span><span>milliseconds</span></div>`, p.latency.threshold),
      panel(p.traffic.title, p.traffic.status, `<div class="primary">${number.format(p.traffic.rate_per_minute)}<span class="unit">req/min</span></div>${sparkline(data.series.map(x => x.traffic), '#55a7ff')}<div class="legend"><span>${p.traffic.count} requests total</span><span>latest active minute</span></div>`, p.traffic.threshold),
      panel(p.errors.title, p.errors.status, `<div class="primary">${number.format(p.errors.error_rate_pct)}<span class="unit">%</span></div>${sparkline(data.series.map(x => x.errors), '#ff6b6b')}<div class="legend"><span>${p.errors.error_count} failures</span><span>${errorBreakdown}</span></div>`, p.errors.threshold),
      panel(p.cost.title, p.cost.status, `<div class="primary">${money.format(p.cost.total)}</div>${sparkline(data.series.map(x => x.cost_usd), '#ffbe55')}<div class="legend"><span>Window total</span><span>USD</span></div>`, p.cost.threshold),
      panel(p.tokens.title, p.tokens.status, `<div class="split" style="grid-template-columns:1fr 1fr"><div class="metric"><span>Input</span><strong>${number.format(p.tokens.tokens_in)}</strong><div class="bar-track"><div class="bar-fill" style="width:${p.tokens.tokens_in/maxTokens*100}%"></div></div></div><div class="metric"><span>Output</span><strong>${number.format(p.tokens.tokens_out)}</strong><div class="bar-track"><div class="bar-fill" style="width:${p.tokens.tokens_out/maxTokens*100}%"></div></div></div></div><div class="legend"><span>Token totals</span><span>input vs output</span></div>`, p.tokens.threshold),
      panel(p.quality.title, p.quality.status, `<div class="primary">${number.format(p.quality.mean)}<span class="unit">/ 1.0</span></div><div class="bar-track"><div class="bar-fill" style="width:${Math.max(0, Math.min(100, p.quality.mean*100))}%"></div></div><div class="legend"><span>${p.quality.sample_count} responses</span><span>heuristic proxy</span></div>`, p.quality.threshold)
    ];
    document.getElementById('panels').innerHTML = cards.join('');
    if (!data.slow_requests.length) {
      document.getElementById('slowRequests').innerHTML = '<div class="empty">Run the load test to populate the investigation queue.</div>';
    } else {
      const rows = data.slow_requests.map(row => `<tr><td><code>${esc(row.correlation_id)}</code></td><td>${esc(row.feature)}</td><td>${esc(row.model)}</td><td class="number">${number.format(row.latency_ms)} ms</td><td class="number">${money.format(row.cost_usd)}</td><td class="number">${row.quality_score == null ? '—' : number.format(row.quality_score)}</td><td>${new Date(row.ts).toLocaleTimeString()}</td></tr>`).join('');
      document.getElementById('slowRequests').innerHTML = `<table><thead><tr><th>Correlation ID</th><th>Feature</th><th>Model</th><th style="text-align:right">Latency</th><th style="text-align:right">Cost</th><th style="text-align:right">Quality</th><th>Timestamp</th></tr></thead><tbody>${rows}</tbody></table>`;
    }
    clearInterval(refreshTimer);
    refreshTimer = setInterval(refresh, data.meta.refresh_seconds * 1000);
  }
  async function refresh() {
    const error = document.getElementById('error');
    try {
      const response = await fetch('/api/dashboard', {cache: 'no-store'});
      if (!response.ok) throw new Error(`Dashboard API returned ${response.status}`);
      render(await response.json());
      error.style.display = 'none';
    } catch (err) {
      error.textContent = `Unable to refresh telemetry: ${err.message}`;
      error.style.display = 'block';
    }
  }
  refresh();
</script>
</body>
</html>
"""

