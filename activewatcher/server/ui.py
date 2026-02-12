from __future__ import annotations

UI_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>activewatcher</title>
    <style>
      :root{
        --bg0:#0b0f14;
        --bg1:#0f1720;
        --card:rgba(255,255,255,.06);
        --card2:rgba(255,255,255,.09);
        --ink:rgba(255,255,255,.92);
        --muted:rgba(255,255,255,.66);
        --faint:rgba(255,255,255,.22);
        --line:rgba(255,255,255,.12);
        --ok:#2dd4bf;
        --warn:#fbbf24;
        --bad:#fb7185;
        --shadow: 0 10px 30px rgba(0,0,0,.35);
        --radius:16px;
        --cal-cell:12px;
        --cal-gap:3px;
      }
      *{box-sizing:border-box}
      html,body{height:100%}
      body{
        margin:0;
        color:var(--ink);
        background:
          radial-gradient(1200px 600px at 20% 0%, rgba(45,212,191,.20), transparent 60%),
          radial-gradient(900px 520px at 100% 10%, rgba(251,191,36,.16), transparent 55%),
          radial-gradient(800px 500px at 70% 110%, rgba(96,165,250,.14), transparent 60%),
          linear-gradient(180deg, var(--bg0), var(--bg1));
        font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Ubuntu, Cantarell, "Noto Sans", sans-serif;
        line-height:1.4;
      }
      a{color:inherit}
      .wrap{max-width:1200px; margin:0 auto; padding:26px 18px 56px}
      header{display:flex; gap:14px; align-items:flex-start; justify-content:space-between; flex-wrap:wrap}
      .brandTop{display:flex; gap:12px; align-items:center; flex-wrap:wrap}
      h1{
        margin:0;
        font-size:26px;
        letter-spacing:.02em;
        font-weight:650;
      }
      .sub{
        margin-top:6px;
        color:var(--muted);
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
      }
      .nav{
        display:flex; gap:10px; align-items:center; flex-wrap:wrap;
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
        color:var(--muted);
      }
      .rangeTabs{
        display:flex;
        gap:4px;
        padding:4px;
        border-radius:999px;
        border:1px solid var(--line);
        background:rgba(255,255,255,.04);
      }
      .rangeTabs button{
        appearance:none;
        border:0;
        background:transparent;
        color:var(--muted);
        padding:8px 10px;
        border-radius:999px;
        cursor:pointer;
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
        line-height:1;
        transition:transform .08s ease, background .08s ease, color .08s ease;
      }
      .rangeTabs button:hover{
        transform:translateY(-1px);
        background:rgba(255,255,255,.08);
        color:var(--ink);
      }
      .rangeTabs button.active{
        background:rgba(255,255,255,.10);
        color:var(--ink);
        box-shadow:0 10px 24px rgba(0,0,0,.28);
      }
      .pill{
        border:1px solid var(--line);
        background:rgba(255,255,255,.04);
        padding:8px 10px;
        border-radius:999px;
        text-decoration:none;
        transition:transform .08s ease, background .08s ease;
      }
      .pill:hover{transform:translateY(-1px); background:rgba(255,255,255,.07)}
      .grid{
        margin-top:20px;
        display:grid;
        grid-template-columns: 1fr;
        gap:16px;
      }
      @media (min-width: 920px){
        .grid{grid-template-columns: 1.15fr .85fr}
      }
      .card{
        border:1px solid var(--line);
        background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.03));
        border-radius:var(--radius);
        box-shadow:var(--shadow);
        overflow:hidden;
        transition:transform .08s ease, border-color .08s ease, background .08s ease;
        backdrop-filter: blur(10px);
      }
      .card:hover{
        transform:translateY(-1px);
        border-color:rgba(255,255,255,.16);
        background:linear-gradient(180deg, rgba(255,255,255,.07), rgba(255,255,255,.03));
      }
      .card .hd{
        padding:14px 16px;
        border-bottom:1px solid var(--line);
        display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap;
        background:rgba(0,0,0,.10);
      }
      .t{
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
        letter-spacing:.08em;
        text-transform:uppercase;
        color:var(--muted);
      }
      .card .bd{padding:16px 16px}
      .controls{
        display:grid; grid-template-columns: 1fr 1fr; gap:10px;
      }
      .controls .row{display:flex; flex-direction:column; gap:6px}
      label{font-size:12px; color:var(--muted); font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;}
      input, select, button{
        border:1px solid var(--line);
        background:rgba(10,14,20,.45);
        color:var(--ink);
        padding:10px 10px;
        border-radius:12px;
        outline:none;
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
      }
      button{
        cursor:pointer;
        background:linear-gradient(180deg, rgba(45,212,191,.22), rgba(45,212,191,.10));
        border-color:rgba(45,212,191,.35);
      }
      button.secondary{
        background:rgba(255,255,255,.06);
        border-color:var(--line);
      }
      .controls .actions{grid-column: 1 / -1; display:flex; gap:10px; align-items:center; flex-wrap:wrap}
      .status{font-size:12px; color:var(--muted)}
      .stats{
        margin-top:0;
        display:grid;
        grid-template-columns: 1.25fr .75fr;
        gap:12px;
        align-items:start;
      }
      @media (max-width: 920px){
        .stats{grid-template-columns: 1fr}
      }
      .kpis{
        display:flex;
        flex-wrap:wrap;
        gap:10px;
      }
      .donutCard{
        border:1px solid var(--line);
        background:rgba(255,255,255,.04);
        border-radius:14px;
        padding:12px 12px;
      }
      .donutWrap{
        display:flex;
        gap:12px;
        align-items:center;
        flex-wrap:wrap;
      }
      .donutSvg{
        width:140px;
        height:140px;
        flex:0 0 auto;
      }
      .donutRing{
        stroke:rgba(255,255,255,.10);
      }
      .donutText{
        fill:rgba(255,255,255,.88);
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:4.4px;
      }
      .donutLegend{
        display:flex;
        flex-direction:column;
        gap:6px;
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
        color:var(--muted);
        flex:1 1 160px;
      }
      .legendItem{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
      }
      .legendLeft{display:flex; align-items:center; gap:8px}
      .dot{width:10px; height:10px; border-radius:999px}
      .legendVal{color:rgba(255,255,255,.90)}
      .kpi{
        border:1px solid var(--line);
        background:rgba(255,255,255,.04);
        border-radius:14px;
        padding:10px 10px;
        flex:0 1 auto;
        min-width:150px;
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
      }
      .kpi .n{
        font-size:20px;
        font-weight:700;
        letter-spacing:.01em;
        margin-top:0;
        font-variant-numeric: tabular-nums;
        text-align:right;
      }
      .kpi .l{
        color:var(--muted);
        font-size:12px;
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        display:flex;
        align-items:center;
        gap:8px;
      }
      .kpi .l:before{
        content:"";
        width:8px;
        height:8px;
        border-radius:999px;
        background:rgba(255,255,255,.18);
        flex:0 0 auto;
      }
      .kpi.ok .l:before{background:rgba(45,212,191,.80)}
      .kpi.warn .l:before{background:rgba(251,191,36,.88)}
      .kpi.bad .l:before{background:rgba(251,113,133,.88)}
      .kpi.ok .n{color:var(--ok)}
      .kpi.warn .n{color:var(--warn)}
      .kpi.bad .n{color:var(--bad)}
      table{width:100%; border-collapse:collapse}
      th, td{
        padding:10px 10px;
        border-bottom:1px solid var(--line);
        font-variant-numeric: tabular-nums;
        font-size:13px;
      }
      th{
        color:var(--muted);
        font-weight:600;
        text-transform:uppercase;
        letter-spacing:.08em;
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
      }
      tbody tr:hover td{background:rgba(255,255,255,.03)}
      .bar{
        height:10px;
        background:rgba(255,255,255,.08);
        border:1px solid rgba(255,255,255,.10);
        border-radius:999px;
        overflow:hidden;
      }
      .bar > div{
        height:100%;
        background:linear-gradient(90deg, rgba(45,212,191,.95), rgba(96,165,250,.85));
        width:0%;
      }
      .timeline{
        display:flex;
        gap:4px;
        align-items:stretch;
        height:118px;
        padding:4px 2px 0;
        overflow:hidden;
      }
      .barCol{
        flex:1 1 0;
        min-width:6px;
        border-radius:10px;
        border:1px solid rgba(255,255,255,.10);
        background:rgba(255,255,255,.07); /* Off */
        overflow:hidden;
        display:flex;
        flex-direction:column-reverse;
      }
      .barSeg{width:100%}
      .barSeg.active{background:rgba(45,212,191,.80)}
      .barSeg.afk{background:rgba(251,191,36,.80)}
      .timelineLabels{
        display:flex;
        gap:4px;
        margin-top:6px;
        padding:0 2px;
      }
      .timelineLabels span{
        flex:1 1 0;
        min-width:6px;
        text-align:center;
        color:var(--muted);
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
        letter-spacing:.02em;
      }
      .timelineTop{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
        flex-wrap:wrap;
        margin-bottom:6px;
      }
      .timelineLegend{
        display:flex;
        gap:10px;
        align-items:center;
        color:var(--muted);
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
      }
      .timelineScale{
        margin-top:6px;
        display:flex;
        justify-content:space-between;
        gap:10px;
        color:var(--muted);
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
      }
      .calHeatmap{
        margin-top:12px;
        overflow-x:auto;
        padding:4px 2px 0;
        border:1px solid var(--line);
        border-radius:14px;
        background:rgba(255,255,255,.03);
      }
      .calMonths{
        display:grid;
        grid-auto-flow: column;
        grid-auto-columns: var(--cal-cell);
        grid-template-rows: 16px;
        gap: var(--cal-gap);
        padding:8px 10px 0;
        color:var(--muted);
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
        align-items:end;
      }
      .calMonths span{white-space:nowrap; transform:translateX(-2px)}
      .calGrid{
        display:grid;
        grid-auto-flow: column;
        grid-auto-columns: var(--cal-cell);
        grid-template-rows: repeat(7, var(--cal-cell));
        gap: var(--cal-gap);
        padding:6px 10px 10px;
      }
      .calCell{
        width: var(--cal-cell);
        height: var(--cal-cell);
        border-radius:4px;
        border:1px solid rgba(255,255,255,.10);
        background:rgba(255,255,255,.06);
        transition:transform .08s ease, border-color .08s ease;
      }
      .calCell.empty{
        border-color:transparent;
        background:transparent;
      }
      .calCell:hover{
        transform:translateY(-1px);
        border-color:rgba(255,255,255,.28);
      }
      .calCell.l0{background:rgba(255,255,255,.06)}
      .calCell.l1{background:rgba(45,212,191,.18); border-color:rgba(45,212,191,.24)}
      .calCell.l2{background:rgba(45,212,191,.34); border-color:rgba(45,212,191,.38)}
      .calCell.l3{background:rgba(45,212,191,.56); border-color:rgba(45,212,191,.62)}
      .calCell.l4{background:rgba(45,212,191,.86); border-color:rgba(45,212,191,.90)}
      .calLegend{
        margin-top:10px;
        display:flex;
        justify-content:flex-end;
        align-items:center;
        gap:8px;
        color:var(--muted);
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
        flex-wrap:wrap;
      }
      .calLegend .swatches{display:flex; gap:4px; align-items:center}
      .onlyStats{display:none}
      body.stats .onlyStats{display:block}
      details{
        margin-top:10px;
        border:1px solid var(--line);
        border-radius:14px;
        padding:10px 12px;
        background:rgba(255,255,255,.03);
      }
      summary{
        cursor:pointer;
        color:var(--muted);
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
      }
      pre{
        white-space:pre-wrap;
        word-break:break-word;
        margin:10px 0 0;
        color:rgba(255,255,255,.86);
        font-size:12px;
      }
      .err{
        border:1px solid rgba(251,113,133,.35);
        background:rgba(251,113,133,.12);
        color:rgba(255,255,255,.92);
        padding:10px 12px;
        border-radius:14px;
        margin-top:12px;
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
      }
    </style>
  </head>
  <body>
    <div class="wrap">
      <header>
        <div>
          <div class="brandTop">
            <h1>activewatcher</h1>
            <div class="rangeTabs" id="rangeTabs" aria-label="time range">
              <button type="button" data-range="24h">24h</button>
              <button type="button" data-range="1w">1w</button>
              <button type="button" data-range="1m">1m</button>
              <button type="button" data-range="all">all</button>
            </div>
          </div>
          <div class="sub" id="range">loading...</div>
        </div>
        <div class="nav">
          <a class="pill" href="/ui">dashboard</a>
          <a class="pill" href="/ui/stats">stats</a>
          <a class="pill" href="/docs" target="_blank" rel="noreferrer">/docs</a>
          <a class="pill" href="/v1/summary" target="_blank" rel="noreferrer">/v1/summary</a>
          <a class="pill" href="/v1/events?bucket=window" target="_blank" rel="noreferrer">window events</a>
          <a class="pill" href="/v1/events?bucket=window_visible" target="_blank" rel="noreferrer">visible windows</a>
          <a class="pill" href="/v1/events?bucket=app_open" target="_blank" rel="noreferrer">open apps</a>
        </div>
      </header>

      <div class="grid">
        <section class="card">
          <div class="hd">
            <div class="t">Overview</div>
            <div class="status" id="status"></div>
          </div>
          <div class="bd">
            <div class="stats">
              <div class="kpis">
                <div class="kpi ok">
                  <div class="l">Active</div>
                  <div class="n" id="k_active">-</div>
                </div>
                <div class="kpi warn">
                  <div class="l">AFK</div>
                  <div class="n" id="k_afk">-</div>
                </div>
              <div class="kpi">
                <div class="l">Off</div>
                <div class="n" id="k_unknown">-</div>
              </div>
                <div class="kpi">
                  <div class="l">Total</div>
                  <div class="n" id="k_total">-</div>
                </div>
              </div>

              <div class="donutCard">
                <div class="t" style="margin-bottom:8px">Activity share</div>
                <div class="donutWrap">
                  <svg class="donutSvg" id="donut_svg" viewBox="0 0 42 42" role="img" aria-label="activity donut chart">
                    <circle class="donutRing" cx="21" cy="21" r="15.915" fill="transparent" stroke-width="4"></circle>
                    <g id="donut_segs"></g>
                    <text id="donut_text" x="21" y="21" text-anchor="middle" dominant-baseline="middle" class="donutText">-</text>
                  </svg>
                  <div class="donutLegend" id="donut_legend"></div>
                </div>
              </div>
            </div>

            <div style="margin-top:14px">
              <div class="timelineTop">
                <div class="t">Timeline</div>
                <div class="timelineLegend" aria-label="timeline legend">
                  <span class="legendLeft"><span class="dot" style="background:rgba(45,212,191,.70)"></span>Active</span>
                  <span class="legendLeft"><span class="dot" style="background:rgba(251,191,36,.72)"></span>AFK</span>
                  <span class="legendLeft"><span class="dot" style="background:rgba(255,255,255,.18)"></span>Off</span>
                </div>
              </div>
              <div class="sub" id="timeline_info"></div>
              <div class="timeline" id="timeline"></div>
              <div class="timelineLabels" id="timeline_labels" aria-label="timeline labels"></div>
              <div class="timelineScale">
                <span id="tl_from">-</span>
                <span id="tl_to">-</span>
              </div>
              <div class="sub" id="current"></div>
            </div>

            <div id="error" class="err" style="display:none"></div>

            <details>
              <summary>Raw /v1/summary JSON</summary>
              <pre id="raw"></pre>
            </details>
          </div>
        </section>

        <section class="card">
          <div class="hd">
            <div class="t" id="apps_label">Top Apps</div>
          </div>
          <div class="bd">
            <table>
              <thead>
                <tr>
                  <th style="text-align:left">App</th>
                  <th style="text-align:right">Time</th>
                  <th style="text-align:right">%</th>
                  <th style="width:38%">Share</th>
                </tr>
              </thead>
              <tbody id="apps"></tbody>
            </table>
          </div>
        </section>

        <section class="card" style="grid-column: 1 / -1">
          <div class="hd">
            <div class="t">Calendar</div>
            <div class="status" id="cal_status"></div>
          </div>
          <div class="bd">
            <form id="cal_form" class="controls">
              <div class="row" style="grid-column: 1 / -1">
                <label for="cal_apps">Apps (comma-separated)</label>
                <input id="cal_apps" type="text" placeholder="brave-browser, code..." list="cal_apps_list" />
                <datalist id="cal_apps_list"></datalist>
              </div>
              <div class="row">
                <label for="cal_mode">Mode</label>
                <select id="cal_mode">
                  <option value="auto" selected>auto (active if idle data)</option>
                  <option value="active">active only</option>
                  <option value="window">window (ignore afk)</option>
                </select>
              </div>
              <div class="actions">
                <button class="secondary" id="cal_refresh" type="submit">Load</button>
                <div class="status" id="cal_info"></div>
              </div>
            </form>

            <div class="calHeatmap">
              <div class="calMonths" id="cal_months"></div>
              <div class="calGrid" id="cal_grid" role="grid" aria-label="calendar heatmap"></div>
            </div>
            <div class="calLegend" id="cal_legend"></div>
          </div>
        </section>

        <section class="card onlyStats" style="grid-column: 1 / -1">
          <div class="hd">
            <div class="t">window_visible logs</div>
            <div class="status" id="visible_status"></div>
          </div>
          <div class="bd">
            <form id="visible_form" class="controls">
              <div class="row">
                <label for="visible_rows">Rows</label>
                <select id="visible_rows">
                  <option value="50">50</option>
                  <option value="100" selected>100</option>
                  <option value="200">200</option>
                  <option value="500">500</option>
                </select>
              </div>
              <div class="row">
                <label for="visible_filter">Filter (app/title)</label>
                <input id="visible_filter" type="text" placeholder="steam, brave..." />
              </div>
              <div class="row">
                <label for="visible_open">Only open now</label>
                <select id="visible_open">
                  <option value="1" selected>yes</option>
                  <option value="0">no</option>
                </select>
              </div>
              <div class="row">
                <label for="visible_autoload">Auto update</label>
                <select id="visible_autoload">
                  <option value="0">off</option>
                  <option value="1" selected>with refresh</option>
                </select>
              </div>
              <div class="actions">
                <button class="secondary" id="visible_refresh" type="submit">Load</button>
                <div class="status" id="visible_count"></div>
              </div>
            </form>

            <div id="visible_error" class="err" style="display:none"></div>

            <table style="margin-top:12px">
              <thead>
                <tr>
                  <th style="text-align:left">Start</th>
                  <th style="text-align:left">End</th>
                  <th style="text-align:right">Dur</th>
                  <th style="text-align:left">App</th>
                  <th style="text-align:left">Title</th>
                  <th style="text-align:left">WS</th>
                  <th style="text-align:left">Mon</th>
                </tr>
              </thead>
              <tbody id="visible_tbody"></tbody>
            </table>

            <details>
              <summary>Raw /v1/events?bucket=window_visible JSON</summary>
              <pre id="visible_raw"></pre>
            </details>
          </div>
        </section>
      </div>
    </div>

    <script>
      const $ = (id) => document.getElementById(id);
      const IS_STATS_PAGE = (() => {
        let p = String(window.location.pathname || "");
        while (p.length > 1 && p.endsWith("/")) p = p.slice(0, -1);
        return p === "/ui/stats";
      })();
      document.body.classList.toggle("stats", IS_STATS_PAGE);

      function fmtSeconds(sec){
        sec = Math.max(0, Math.round(sec));
        const h = Math.floor(sec / 3600);
        const m = Math.floor((sec % 3600) / 60);
        const s = sec % 60;
        if (h > 0) return `${h}h ${m}m ${s}s`;
        if (m > 0) return `${m}m ${s}s`;
        return `${s}s`;
      }

      function fmtSecondsShort(sec){
        sec = Math.max(0, Math.round(sec));
        const h = Math.floor(sec / 3600);
        const m = Math.floor((sec % 3600) / 60);
        const s = sec % 60;
        if (h > 0) return `${h}h ${m}m`;
        if (m > 0) return `${m}m`;
        return `${s}s`;
      }

      function fmtChunk(sec){
        sec = Math.max(0, Math.round(sec));
        if (sec >= 86400) return `${Math.round(sec / 86400)}d`;
        if (sec >= 3600) return `${Math.round(sec / 3600)}h`;
        return `${Math.max(1, Math.round(sec / 60))}m`;
      }

      function fmtTsLocal(ts){
        if (!ts) return "";
        const d = new Date(ts);
        if (isNaN(d.getTime())) return String(ts);
        return d.toLocaleString(undefined, {
          year: "2-digit",
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });
      }

      const CALENDAR_DAYS = 365;

      function fmtDateKey(d){
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, "0");
        const day = String(d.getDate()).padStart(2, "0");
        return `${y}-${m}-${day}`;
      }

      function parseDateKey(s){
        const parts = String(s || "").split("-");
        if (parts.length !== 3) return null;
        const y = parseInt(parts[0], 10);
        const m = parseInt(parts[1], 10);
        const d = parseInt(parts[2], 10);
        if (!y || !m || !d) return null;
        return new Date(y, m - 1, d);
      }

      function getTzName(){
        try{
          return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
        }catch(e){
          return "UTC";
        }
      }

      function calendarBounds(now){
        const to = new Date(now);
        const from = new Date(to);
        from.setHours(0, 0, 0, 0);
        from.setDate(from.getDate() - (CALENDAR_DAYS - 1));
        return {from, to};
      }

      function parseAppsInput(raw){
        return String(raw || "")
          .split(",")
          .map((s) => s.trim())
          .filter((s) => !!s);
      }

      function getCalendarMode(){
        const el = $("cal_mode");
        const v = el ? String(el.value || "").trim().toLowerCase() : "";
        return (v === "active" || v === "window" || v === "auto") ? v : "auto";
      }

      function saveCalendarPrefs(){
        try{
          localStorage.setItem("aw_cal_apps", String($("cal_apps").value || ""));
          localStorage.setItem("aw_cal_mode", getCalendarMode());
        }catch(e){}
      }

      function loadCalendarPrefs(){
        try{
          const apps = localStorage.getItem("aw_cal_apps");
          const mode = localStorage.getItem("aw_cal_mode");
          if (apps !== null && $("cal_apps")) $("cal_apps").value = apps;
          if (mode !== null && $("cal_mode")) $("cal_mode").value = mode;
        }catch(e){}
      }

      function calendarLevel(seconds, maxSeconds){
        const s = Number(seconds) || 0;
        if (s <= 0) return 0;
        const max = Number(maxSeconds) || 0;
        if (max <= 0) return 1;
        const r = s / max;
        if (r <= 0.25) return 1;
        if (r <= 0.50) return 2;
        if (r <= 0.75) return 3;
        return 4;
      }

      function renderCalendarMonths(startAligned, weekCount){
        const el = $("cal_months");
        if (!el) return;
        el.textContent = "";
        const fmt = new Intl.DateTimeFormat(undefined, {month: "short"});
        let last = null;
        for (let w = 0; w < weekCount; w++){
          const d = new Date(startAligned);
          d.setDate(d.getDate() + w * 7);
          const m = d.getMonth();
          const span = document.createElement("span");
          if (last === null || m !== last){
            span.textContent = fmt.format(d);
            last = m;
          }else{
            span.textContent = "";
          }
          el.appendChild(span);
        }
      }

      function renderCalendarLegend(maxSeconds){
        const el = $("cal_legend");
        if (!el) return;
        el.textContent = "";

        const less = document.createElement("span");
        less.textContent = "less";

        const swatches = document.createElement("div");
        swatches.className = "swatches";
        for (const lvl of [0, 1, 2, 3, 4]){
          const s = document.createElement("span");
          s.className = `calCell l${lvl}`;
          swatches.appendChild(s);
        }

        const more = document.createElement("span");
        more.textContent = "more";

        const max = document.createElement("span");
        max.textContent = (Number(maxSeconds) || 0) > 0 ? `max ${fmtSecondsShort(maxSeconds)}/day` : "no data";

        el.appendChild(less);
        el.appendChild(swatches);
        el.appendChild(more);
        el.appendChild(document.createTextNode(" · "));
        el.appendChild(max);
      }

      function renderCalendar(data){
        const grid = $("cal_grid");
        if (!grid) return;
        grid.textContent = "";

        const days = Array.isArray(data && data.days) ? data.days : [];
        const fromDate = data && data.from_date ? String(data.from_date) : "";
        const toDate = data && data.to_date ? String(data.to_date) : "";
        const start = parseDateKey(fromDate);
        const end = parseDateKey(toDate);
        if (!start || !end){
          renderCalendarMonths(new Date(), 0);
          renderCalendarLegend(0);
          return;
        }

        const map = new Map();
        for (const it of days){
          if (!it) continue;
          const k = it.date ? String(it.date) : "";
          if (!k) continue;
          map.set(k, Number(it.seconds || 0) || 0);
        }

        const maxSeconds = Number(data && data.max_seconds != null ? data.max_seconds : 0) || 0;

        const startAligned = new Date(start);
        startAligned.setDate(startAligned.getDate() - startAligned.getDay());

        const endAligned = new Date(end);
        endAligned.setDate(endAligned.getDate() + (6 - endAligned.getDay()));

        const apps = parseAppsInput($("cal_apps") ? $("cal_apps").value : "");

        let cells = 0;
        for (let d = new Date(startAligned); d <= endAligned; d.setDate(d.getDate() + 1)){
          const key = fmtDateKey(d);
          const inRange = d >= start && d <= end;

          const cell = document.createElement("div");
          if (!inRange){
            cell.className = "calCell empty";
          }else{
            const seconds = map.has(key) ? map.get(key) : 0;
            const lvl = calendarLevel(seconds, maxSeconds);
            cell.className = `calCell l${lvl}`;
            const hours = (Number(seconds) || 0) / 3600.0;
            const appsHint = apps.length ? `\\napps: ${apps.join(", ")}` : "";
            cell.title = `${key}\\n${fmtSeconds(seconds)} (${Math.round(hours * 10) / 10}h)${appsHint}`;
          }

          grid.appendChild(cell);
          cells += 1;
        }

        const weekCount = Math.max(0, Math.round(cells / 7));
        renderCalendarMonths(startAligned, weekCount);
        renderCalendarLegend(maxSeconds);
      }

      let calLoading = false;
      async function loadCalendar(){
        if (calLoading) return;
        calLoading = true;

        const status = $("cal_status");
        const info = $("cal_info");
        if (status) status.textContent = "fetching...";
        if (info) info.textContent = "";

        const bounds = calendarBounds(new Date());

        const url = new URL("/v1/heatmap", window.location.origin);
        url.searchParams.set("from", bounds.from.toISOString());
        url.searchParams.set("to", bounds.to.toISOString());
        url.searchParams.set("tz", getTzName());
        url.searchParams.set("mode", getCalendarMode());

        const apps = parseAppsInput($("cal_apps") ? $("cal_apps").value : "");
        for (const a of apps){
          url.searchParams.append("app", a);
        }

        const started = performance.now();
        try{
          const res = await fetch(url.toString(), {cache:"no-store"});
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data = await res.json();
          const ms = Math.round(performance.now() - started);
          if (status) status.textContent = `ok (${ms}ms)`;
          if (info){
            const appsLabel = (data.apps && data.apps.length) ? `${data.apps.length} app(s)` : "all apps";
            info.textContent = `${data.from_date} → ${data.to_date} · ${data.mode} · ${appsLabel}`;
          }
          renderCalendar(data);
        }catch(e){
          if (status) status.textContent = "error";
          if (info) info.textContent = String(e);
          renderCalendarMonths(new Date(), 0);
          renderCalendarLegend(0);
          if ($("cal_grid")) $("cal_grid").textContent = "";
        }

        calLoading = false;
      }

      let calAppsLoading = false;
      async function loadCalendarAppOptions(){
        if (calAppsLoading) return;
        calAppsLoading = true;

        const list = $("cal_apps_list");
        if (!list){
          calAppsLoading = false;
          return;
        }
        list.textContent = "";

        const bounds = calendarBounds(new Date());
        const url = new URL("/v1/apps", window.location.origin);
        url.searchParams.set("from", bounds.from.toISOString());
        url.searchParams.set("to", bounds.to.toISOString());
        url.searchParams.set("limit", "500");

        try{
          const res = await fetch(url.toString(), {cache:"no-store"});
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data = await res.json();
          const apps = Array.isArray(data.apps) ? data.apps : [];
          for (const a of apps){
            const opt = document.createElement("option");
            opt.value = String(a || "");
            list.appendChild(opt);
          }
        }catch(e){}

        calAppsLoading = false;
      }

      function renderDonut(data){
        const active = Number(data && data.active_seconds != null ? data.active_seconds : 0) || 0;
        const afk = Number(data && data.afk_seconds != null ? data.afk_seconds : 0) || 0;
        const unknown = Number(data && data.unknown_seconds != null ? data.unknown_seconds : 0) || 0;
        const total = Number(data && data.total_seconds != null ? data.total_seconds : (active + afk + unknown)) || 0;

        const segs = $("donut_segs");
        const legend = $("donut_legend");
        const text = $("donut_text");
        if (!segs || !legend || !text) return;

        segs.textContent = "";
        legend.textContent = "";
        text.textContent = fmtSecondsShort(total);

        const parts = [
          {label: "Active", seconds: active, color: "#2dd4bf"},
          {label: "AFK", seconds: afk, color: "#fbbf24"},
          {label: "Off", seconds: unknown, color: "rgba(255,255,255,.28)"},
        ];

        let offset = 25;
        const ns = "http://www.w3.org/2000/svg";
        const radius = "15.915";

        for (const p of parts){
          const pct = total > 0 ? (p.seconds / total) * 100.0 : 0.0;
          if (pct <= 0.0001) continue;
          const c = document.createElementNS(ns, "circle");
          c.setAttribute("cx", "21");
          c.setAttribute("cy", "21");
          c.setAttribute("r", radius);
          c.setAttribute("fill", "transparent");
          c.setAttribute("stroke-width", "4");
          c.setAttribute("stroke", p.color);
          c.setAttribute("stroke-dasharray", `${pct} ${Math.max(0, 100 - pct)}`);
          c.setAttribute("stroke-dashoffset", String(offset));
          c.setAttribute("stroke-linecap", "butt");
          segs.appendChild(c);
          offset -= pct;
        }

        for (const p of parts){
          const pct = total > 0 ? (p.seconds / total) * 100.0 : 0.0;
          const item = document.createElement("div");
          item.className = "legendItem";

          const left = document.createElement("div");
          left.className = "legendLeft";
          const dot = document.createElement("span");
          dot.className = "dot";
          dot.style.background = p.color;
          const label = document.createElement("span");
          label.textContent = p.label;
          left.appendChild(dot);
          left.appendChild(label);

          const val = document.createElement("span");
          val.className = "legendVal";
          val.textContent = `${fmtSeconds(p.seconds)} · ${Math.round(pct * 10) / 10}%`;

          item.appendChild(left);
          item.appendChild(val);
          legend.appendChild(item);
        }
      }

      function setError(msg){
        const el = $("error");
        if (!msg){
          el.style.display = "none";
          el.textContent = "";
          return;
        }
        el.style.display = "block";
        el.textContent = msg;
      }

      function setVisibleError(msg){
        const el = $("visible_error");
        if (!msg){
          el.style.display = "none";
          el.textContent = "";
          return;
        }
        el.style.display = "block";
        el.textContent = msg;
      }

      function qp(){
        return new URLSearchParams(window.location.search);
      }

      function setQP(params){
        const url = new URL(window.location.href);
        url.search = params.toString();
        window.history.replaceState({}, "", url.toString());
      }

      const AUTO_REFRESH_SECONDS = 30;
      const RANGE_KEYS = ["24h", "1w", "1m", "all"];
      function normalizeRangeKey(value){
        const v = (value || "").trim();
        return RANGE_KEYS.includes(v) ? v : null;
      }

      function chunkSecondsForRange(rangeKey, durationSeconds){
        if (rangeKey === "24h") return 3600; // 1h
        if (rangeKey === "1w") return 86400; // 1d
        if (rangeKey === "1m") return 86400; // 1d

        // all (dynamic)
        const days = (Number(durationSeconds) || 0) / 86400.0;
        if (days <= 2) return 3600; // 1h
        if (days <= 90) return 86400; // 1d
        if (days <= 365) return 604800; // 7d
        return 2592000; // 30d
      }

      function rangeBounds(rangeKey, now){
        const to = new Date(now);
        if (rangeKey === "24h"){
          const from = new Date(to);
          from.setMinutes(0, 0, 0);
          from.setHours(from.getHours() - 23);
          return {from, to};
        }
        if (rangeKey === "1w"){
          const from = new Date(to);
          from.setHours(0, 0, 0, 0);
          from.setDate(from.getDate() - 6);
          return {from, to};
        }
        if (rangeKey === "1m"){
          const from = new Date(to);
          from.setHours(0, 0, 0, 0);
          from.setDate(from.getDate() - 29);
          return {from, to};
        }
        return {from: null, to};
      }

      function getRangeKey(){
        const fromQP = normalizeRangeKey(qp().get("range"));
        if (fromQP) return fromQP;
        try{
          const fromLS = normalizeRangeKey(localStorage.getItem("aw_range"));
          if (fromLS) return fromLS;
        }catch(e){}
        return "24h";
      }

      function renderRangeTabs(){
        const root = $("rangeTabs");
        if (!root) return;
        const active = getRangeKey();
        const btns = root.querySelectorAll("button[data-range]");
        for (const b of btns){
          const r = b.dataset.range || "";
          if (r === active) b.classList.add("active");
          else b.classList.remove("active");
        }
      }

      function setRangeKey(value){
        const v = normalizeRangeKey(value) || "24h";
        const params = qp();
        params.set("range", v);
        setQP(params);
        try{ localStorage.setItem("aw_range", v); }catch(e){}
        renderRangeTabs();
      }

      let allFromResolved = false;
      let allFromTs = null;
      let allFromInFlight = null;
      async function getAllFromTs(){
        if (allFromResolved) return allFromTs;
        if (allFromInFlight) return allFromInFlight;

        allFromInFlight = (async () => {
          async function fetchFrom(bucket){
            const url = new URL("/v1/range", window.location.origin);
            url.searchParams.set("bucket", bucket);
            const res = await fetch(url.toString(), {cache:"no-store"});
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            return (data && data.from_ts) ? String(data.from_ts) : null;
          }

          return (await fetchFrom("window")) || (await fetchFrom("idle")) || null;
        })();

        try{
          allFromTs = await allFromInFlight;
          allFromResolved = true;
          return allFromTs;
        }catch(e){
          allFromResolved = false;
          allFromTs = null;
          return null;
        }finally{
          allFromInFlight = null;
        }
      }

      let visibleLast = null;
      let visibleLoading = false;

      function renderVisibleLogs(){
        const data = visibleLast;
        const tbody = $("visible_tbody");
        tbody.textContent = "";
        $("visible_raw").textContent = data ? JSON.stringify(data, null, 2) : "";

        const rowsLimit = parseInt($("visible_rows").value, 10) || 100;
        const q = ($("visible_filter").value || "").trim().toLowerCase();
        const onlyOpen = (parseInt($("visible_open").value, 10) || 0) === 1;

        const events = (data && Array.isArray(data.events)) ? data.events : [];
        const toTs = data && data.to_ts ? String(data.to_ts) : "";

        let filtered = events;
        if (onlyOpen && toTs){
          filtered = filtered.filter((e) => (e && e.end_ts) ? String(e.end_ts) === toTs : false);
        }
        if (q){
          filtered = filtered.filter((e) => {
            const d = (e && e.data) ? e.data : {};
            const app = (d && d.app) ? String(d.app).toLowerCase() : "";
            const title = (d && d.title) ? String(d.title).toLowerCase() : "";
            const src = (e && e.source) ? String(e.source).toLowerCase() : "";
            return app.includes(q) || title.includes(q) || src.includes(q);
          });
        }

        const sorted = filtered.slice().sort((a, b) => {
          const at = Date.parse((a && a.start_ts) ? String(a.start_ts) : "");
          const bt = Date.parse((b && b.start_ts) ? String(b.start_ts) : "");
          return (isNaN(bt) ? 0 : bt) - (isNaN(at) ? 0 : at);
        });
        const shown = sorted.slice(0, rowsLimit);

        $("visible_count").textContent = data
          ? `showing ${shown.length} / ${filtered.length} (total ${events.length})`
          : "";

        for (const e of shown){
          const d = (e && e.data) ? e.data : {};
          const tr = document.createElement("tr");

          const start = (e && e.start_ts) ? String(e.start_ts) : "";
          const end = (e && e.end_ts) ? String(e.end_ts) : "";
          const dur = (() => {
            const a = Date.parse(start);
            const b = Date.parse(end);
            if (isNaN(a) || isNaN(b)) return "";
            return fmtSeconds((b - a) / 1000.0);
          })();

          const tdStart = document.createElement("td");
          tdStart.textContent = fmtTsLocal(start);
          tdStart.title = start;
          const tdEnd = document.createElement("td");
          tdEnd.textContent = fmtTsLocal(end);
          tdEnd.title = end;
          const tdDur = document.createElement("td");
          tdDur.style.textAlign = "right";
          tdDur.textContent = dur;
          const tdApp = document.createElement("td");
          tdApp.textContent = d.app ? String(d.app) : "";
          const tdTitle = document.createElement("td");
          tdTitle.textContent = d.title ? String(d.title) : "";
          const tdWs = document.createElement("td");
          tdWs.textContent = d.workspace ? String(d.workspace) : "";
          const tdMon = document.createElement("td");
          tdMon.textContent = d.monitor ? String(d.monitor) : "";

          tr.appendChild(tdStart);
          tr.appendChild(tdEnd);
          tr.appendChild(tdDur);
          tr.appendChild(tdApp);
          tr.appendChild(tdTitle);
          tr.appendChild(tdWs);
          tr.appendChild(tdMon);
          tbody.appendChild(tr);
        }

        if (data && !shown.length){
          const tr = document.createElement("tr");
          const td = document.createElement("td");
          td.colSpan = 7;
          td.style.color = "rgba(255,255,255,.66)";
          td.textContent = "No window_visible events for this range / filter (start watchers and wait for a few events).";
          tr.appendChild(td);
          tbody.appendChild(tr);
        }
      }

      async function loadVisibleLogs(){
        if (visibleLoading) return;
        visibleLoading = true;
        setVisibleError("");
        $("visible_status").textContent = "fetching...";

        const url = new URL("/v1/events", window.location.origin);
        url.searchParams.set("bucket", "window_visible");

        const rangeKey = getRangeKey();
        const now = new Date();
        const bounds = rangeBounds(rangeKey, now);
        url.searchParams.set("to", bounds.to.toISOString());
        let fromTs = null;
        if (rangeKey === "all") fromTs = await getAllFromTs();
        else if (bounds.from) fromTs = bounds.from.toISOString();
        if (fromTs) url.searchParams.set("from", String(fromTs));

        const started = performance.now();
        try{
          const res = await fetch(url.toString(), {cache:"no-store"});
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          visibleLast = await res.json();
        }catch(e){
          $("visible_status").textContent = "error";
          setVisibleError(`Failed to load window_visible events: ${e}`);
          visibleLast = null;
          renderVisibleLogs();
          visibleLoading = false;
          return;
        }
        const ms = Math.round(performance.now() - started);
        $("visible_status").textContent = `ok (${ms}ms)`;
        renderVisibleLogs();
        visibleLoading = false;
      }

      async function load(){
        setError("");
        $("status").textContent = "fetching...";

        const uiParams = qp();
        const rangeKey = getRangeKey();
        uiParams.set("range", rangeKey);
        uiParams.delete("chunk_seconds");

        setQP(uiParams);
        renderRangeTabs();

        const now = new Date();
        const bounds = rangeBounds(rangeKey, now);
        const toTs = bounds.to.toISOString();
        let fromTs = null;
        if (rangeKey === "all") fromTs = await getAllFromTs();
        else if (bounds.from) fromTs = bounds.from.toISOString();

        let durationSeconds = 0;
        if (fromTs){
          const fromMs = Date.parse(String(fromTs));
          if (!isNaN(fromMs)){
            durationSeconds = Math.max(0.0, (bounds.to.getTime() - fromMs) / 1000.0);
          }
        }

        const chunkSeconds = chunkSecondsForRange(rangeKey, durationSeconds);

        const url = new URL("/v1/summary", window.location.origin);
        url.searchParams.set("chunk_seconds", String(chunkSeconds));
        url.searchParams.set("to", toTs);
        if (fromTs) url.searchParams.set("from", String(fromTs));

        let data;
        const started = performance.now();
        try{
          const res = await fetch(url.toString(), {cache:"no-store"});
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          data = await res.json();
        }catch(e){
          $("status").textContent = "error";
          setError(`Failed to load summary: ${e}`);
          return;
        }
        const ms = Math.round(performance.now() - started);
        const updatedAt = new Date().toLocaleTimeString(undefined, {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });
        $("status").textContent = `ok (${ms}ms) · updated ${updatedAt} · auto ${AUTO_REFRESH_SECONDS}s`;

        $("raw").textContent = JSON.stringify(data, null, 2);
        const fromLocal = fmtTsLocal(data.from_ts);
        const toLocal = fmtTsLocal(data.to_ts);
        $("range").textContent = `range: ${rangeKey} · ${fromLocal} → ${toLocal}`;
        $("range").title = `${data.from_ts} -> ${data.to_ts}`;

        $("k_total").textContent = fmtSecondsShort(data.total_seconds || 0);
        $("k_active").textContent = fmtSecondsShort(data.active_seconds || 0);
        $("k_afk").textContent = fmtSecondsShort(data.afk_seconds || 0);
        $("k_unknown").textContent = fmtSecondsShort(data.unknown_seconds || 0);
        renderDonut(data);

        // Current (best-effort: last timeline segment)
        const tl = Array.isArray(data.timeline) ? data.timeline : [];
        const last = tl.length ? tl[tl.length - 1] : null;
        if (last && last.window){
          const w = last.window;
          const app = w.app || "";
          const title = w.title || "";
          const ws = w.workspace ? ` ws:${w.workspace}` : "";
          const mon = w.monitor ? ` mon:${w.monitor}` : "";
          const afk = (last.afk === true) ? " AFK" : (last.afk === false) ? " ACTIVE" : " OFF";
          $("current").textContent = `current: ${app}${ws}${mon}${afk}  ${title}`;
        }else if (last){
          const afk = (last.afk === true) ? "AFK" : (last.afk === false) ? "ACTIVE" : "OFF";
          $("current").textContent = `current: (no window) ${afk}`;
        }else{
          $("current").textContent = "current: (no data yet)";
        }

        // Top apps
        const apps = Array.isArray(data.top_apps) ? data.top_apps : [];
        const mode = data.top_apps_mode || "window";
        $("apps_label").textContent = `${mode === "active" ? "Top Apps (active)" : "Top Apps (window)"} · ${rangeKey}`;
        const tbody = $("apps");
        tbody.textContent = "";
        for (const a of apps.slice(0, 20)){
          const tr = document.createElement("tr");
          const tdApp = document.createElement("td");
          tdApp.textContent = a.app || "";
          const tdTime = document.createElement("td");
          tdTime.style.textAlign = "right";
          tdTime.textContent = fmtSeconds(a.seconds || 0);
          const tdPct = document.createElement("td");
          tdPct.style.textAlign = "right";
          const pct = (a.percent_active != null) ? a.percent_active : (a.percent_window != null) ? a.percent_window : 0;
          tdPct.textContent = `${Math.round(pct * 10) / 10}%`;
          const tdBar = document.createElement("td");
          const bar = document.createElement("div");
          bar.className = "bar";
          const fill = document.createElement("div");
          const pctClamped = Math.max(0, Math.min(100, Number(pct) || 0));
          fill.style.width = `${pctClamped}%`;
          bar.appendChild(fill);
          tdBar.appendChild(bar);
          tr.appendChild(tdApp);
          tr.appendChild(tdTime);
          tr.appendChild(tdPct);
          tr.appendChild(tdBar);
          tbody.appendChild(tr);

          tr.style.cursor = "pointer";
          tr.title = "Click to filter calendar (Shift-click to add)";
          tr.addEventListener("click", (ev) => {
            const app = a.app || "";
            if (!app) return;
            const input = $("cal_apps");
            if (!input) return;
            if (ev && ev.shiftKey){
              const cur = parseAppsInput(input.value);
              if (!cur.includes(app)) cur.push(app);
              input.value = cur.join(", ");
            }else{
              input.value = app;
            }
            saveCalendarPrefs();
            loadCalendar();
          });
        }
        if (!apps.length){
          const tr = document.createElement("tr");
          const td = document.createElement("td");
          td.colSpan = 4;
          td.style.color = "rgba(255,255,255,.66)";
          td.textContent = "No app data yet (start watchers and wait for a few events).";
          tr.appendChild(td);
          tbody.appendChild(tr);
        }

        // Timeline buckets (hourly for 24h, daily for 1w/1m)
        const chunks = Array.isArray(data.timeline_chunks) ? data.timeline_chunks : [];
        const container = $("timeline");
        const labels = $("timeline_labels");
        if (container) container.textContent = "";
        if (labels) labels.textContent = "";

        const labelText = (startTs) => {
          const d = new Date(startTs);
          if (isNaN(d.getTime())) return "";
          if (rangeKey === "24h"){
            return String(d.getHours()).padStart(2, "0");
          }
          if (rangeKey === "1w"){
            return d.toLocaleDateString(undefined, {weekday: "short"});
          }
          return d.toLocaleDateString(undefined, {month: "2-digit", day: "2-digit"});
        };

        const showLabel = (i, n) => {
          if (rangeKey === "24h") return i % 3 === 0 || i === n - 1;
          if (rangeKey === "1w") return true;
          if (rangeKey === "1m") return i % 5 === 0 || i === n - 1;
          const step = Math.max(1, Math.round(n / 6));
          return i % step === 0 || i === n - 1;
        };

        for (let i = 0; i < chunks.length; i++){
          const c = chunks[i] || {};
          const startTs = c.start_ts ? String(c.start_ts) : "";
          const endTs = c.end_ts ? String(c.end_ts) : "";
          const startMs = Date.parse(startTs);
          const endMs = Date.parse(endTs);
          const bucketSec = (!isNaN(startMs) && !isNaN(endMs) && endMs > startMs)
            ? (endMs - startMs) / 1000.0
            : chunkSeconds;

          const active = Number(c.active_seconds || 0) || 0;
          const afk = Number(c.afk_seconds || 0) || 0;
          const off = Number(c.unknown_seconds || 0) || 0;

          const aPct = bucketSec > 0 ? (active / bucketSec) * 100.0 : 0.0;
          const fPct = bucketSec > 0 ? (afk / bucketSec) * 100.0 : 0.0;
          const aPctC = Math.max(0, Math.min(100, aPct));
          const fPctC = Math.max(0, Math.min(100 - aPctC, fPct));

          const col = document.createElement("div");
          col.className = "barCol";

          const segA = document.createElement("div");
          segA.className = "barSeg active";
          segA.style.height = `${aPctC}%`;

          const segF = document.createElement("div");
          segF.className = "barSeg afk";
          segF.style.height = `${fPctC}%`;

          col.appendChild(segA);
          col.appendChild(segF);

          const top = c.top_app ? ` top:${c.top_app}` : "";
          col.title = `${fmtTsLocal(startTs)} → ${fmtTsLocal(endTs)}\\nactive ${fmtSeconds(active)} | afk ${fmtSeconds(afk)} | off ${fmtSeconds(off)}${top}`;

          if (container) container.appendChild(col);

          if (labels){
            const s = document.createElement("span");
            s.textContent = showLabel(i, chunks.length) ? labelText(startTs) : "";
            labels.appendChild(s);
          }
        }

        const tlInfo = $("timeline_info");
        if (tlInfo){
          if (rangeKey === "24h") tlInfo.textContent = "per hour";
          else if (rangeKey === "1w") tlInfo.textContent = "per day";
          else if (rangeKey === "1m") tlInfo.textContent = "per day";
          else tlInfo.textContent = `per ${fmtChunk(chunkSeconds)}`;
        }
        const tlFrom = $("tl_from");
        const tlTo = $("tl_to");
        if (tlFrom) tlFrom.textContent = fmtTsLocal(data.from_ts);
        if (tlTo) tlTo.textContent = fmtTsLocal(data.to_ts);

        if (IS_STATS_PAGE && (parseInt($("visible_autoload").value, 10) || 0) === 1){
          loadVisibleLogs();
        }
      }

      function initFromQuery(){
        const params = qp();
        const rangeKey = normalizeRangeKey(params.get("range")) || getRangeKey();
        params.set("range", rangeKey);
        setQP(params);
        try{ localStorage.setItem("aw_range", rangeKey); }catch(e){}
        renderRangeTabs();
      }

      let timer = null;
      function startAutoRefresh(){
        if (timer) clearInterval(timer);
        timer = setInterval(() => load(), AUTO_REFRESH_SECONDS * 1000);
      }

      for (const btn of document.querySelectorAll("#rangeTabs button[data-range]")){
        btn.addEventListener("click", () => {
          setRangeKey(btn.dataset.range || "24h");
          load();
        });
      }

      $("visible_form").addEventListener("submit", (e) => { e.preventDefault(); loadVisibleLogs(); });
      $("visible_rows").addEventListener("change", () => renderVisibleLogs());
      $("visible_filter").addEventListener("input", () => renderVisibleLogs());
      $("visible_open").addEventListener("change", () => renderVisibleLogs());
      $("visible_autoload").addEventListener("change", () => {
        if ((parseInt($("visible_autoload").value, 10) || 0) === 1 && !visibleLast){
          loadVisibleLogs();
        }
      });

      $("cal_form").addEventListener("submit", (e) => { e.preventDefault(); saveCalendarPrefs(); loadCalendar(); });
      $("cal_mode").addEventListener("change", () => { saveCalendarPrefs(); loadCalendar(); });
      $("cal_apps").addEventListener("change", () => saveCalendarPrefs());

      loadCalendarPrefs();
      initFromQuery();
      load();
      loadCalendar();
      loadCalendarAppOptions();
      startAutoRefresh();
    </script>
  </body>
</html>
"""
