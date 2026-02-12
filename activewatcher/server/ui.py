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
        --timeline-axis:48px;
        --timeline-gap:8px;
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
      body.stats .wrap{
        max-width:none;
        width:100%;
        padding:16px 12px 44px;
      }
      body.stats .grid{
        margin-top:12px;
        gap:12px;
      }
      @media (min-width: 920px){
        body.stats .grid{grid-template-columns: 1fr 1fr}
      }
      @media (min-width: 1280px){
        body.stats .grid{grid-template-columns: 1.2fr .8fr}
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
      .appsControls{
        display:flex;
        align-items:center;
        gap:8px;
        flex-wrap:wrap;
      }
      .t{
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
        letter-spacing:.08em;
        text-transform:uppercase;
        color:var(--muted);
      }
      .card .bd{padding:16px 16px}
      body.stats .card .hd{padding:10px 12px}
      body.stats .card .bd{padding:12px 12px}
      .controls{
        display:grid; grid-template-columns: 1fr 1fr; gap:10px;
      }
      body.stats .controls{gap:8px}
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
      .donutLegend .legendItem{
        display:grid;
        grid-template-columns: minmax(0, 1fr) auto;
        align-items:center;
        gap:10px;
      }
      .donutLegend .legendLeft{
        min-width:0;
      }
      .donutLegend .legendLeft span:last-child{
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
        max-width:220px;
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
      body.stats th, body.stats td{padding:8px 8px}
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
        position:relative;
        z-index:1;
      }
      .timelineWrap{
        display:grid;
        grid-template-columns: var(--timeline-axis) 1fr;
        gap: var(--timeline-gap);
        align-items:stretch;
      }
      .timelineAxis{
        display:flex;
        flex-direction:column;
        justify-content:space-between;
        height:118px;
        padding:4px 0 0;
        color:var(--muted);
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
      }
      .timelineAxis span{line-height:1}
      .timelinePlot{position:relative}
      .timelineGrid{
        position:absolute;
        inset:4px 2px 0 2px;
        display:flex;
        flex-direction:column;
        justify-content:space-between;
        pointer-events:none;
      }
      .timelineGrid span{
        display:block;
        height:1px;
        background:rgba(255,255,255,.10);
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
        position:relative;
      }
      .barSeg{width:100%}
      .barSeg.active{background:rgba(45,212,191,.80)}
      .barSeg.afk{background:rgba(251,191,36,.80)}
      .barSeg.afkOverlay{
        position:absolute;
        left:0;
        bottom:0;
        background:rgba(251,191,36,.80);
        mix-blend-mode:screen;
      }
      .barSeg.switch{background:rgba(96,165,250,.85)}
      .timelineLabels{
        display:flex;
        gap:4px;
        margin-top:6px;
        padding:0 2px;
      }
      .timelinePad{
        padding-left: calc(var(--timeline-axis) + var(--timeline-gap));
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
      .wsHeatmapWrap{
        margin-top:10px;
        overflow:auto;
        padding:8px;
        border:1px solid var(--line);
        border-radius:14px;
        background:rgba(255,255,255,.03);
      }
      .wsHeatmap{
        --ws-cols: 1;
        display:grid;
        grid-template-columns: minmax(140px, 1.2fr) repeat(var(--ws-cols), minmax(18px, 1fr));
        gap:4px;
        align-items:center;
      }
      .wsColLabel{
        text-align:center;
        color:var(--muted);
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:11px;
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
      }
      .wsApp{
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
        color:var(--ink);
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
        padding-right:6px;
      }
      .wsCell{
        height:18px;
        border-radius:4px;
        border:1px solid rgba(255,255,255,.10);
        background:rgba(255,255,255,.06);
      }
      .wsLegend{
        margin-top:8px;
        display:flex;
        align-items:center;
        gap:10px;
        color:var(--muted);
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
        flex-wrap:wrap;
      }
      .wsLegendBar{
        width:160px;
        height:8px;
        border-radius:999px;
        border:1px solid rgba(255,255,255,.18);
        background:linear-gradient(90deg, rgba(45,212,191,.18), rgba(251,113,133,.86));
      }
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
      .sitesNote{
        margin-top:8px;
        color:var(--muted);
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:11px;
      }
      .sitesChartWrap{
        margin-top:12px;
        border:1px solid var(--line);
        border-radius:14px;
        padding:10px 12px;
        background:rgba(255,255,255,.03);
      }
      .sitesChartHeader{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
        flex-wrap:wrap;
        margin-bottom:8px;
      }
      .sitesChart{
        display:flex;
        flex-direction:column;
        gap:8px;
      }
      .sitesBarRow{
        display:flex;
        align-items:center;
        gap:10px;
      }
      .sitesBarLabel{
        width:200px;
        max-width:200px;
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
        color:var(--ink);
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
      }
      .sitesBarTrack{
        flex:1 1 auto;
        height:10px;
        border-radius:999px;
        border:1px solid rgba(255,255,255,.12);
        background:rgba(255,255,255,.06);
        overflow:hidden;
      }
      .sitesBarFill{
        height:100%;
        background:linear-gradient(90deg, rgba(45,212,191,.35), rgba(96,165,250,.75));
        width:0%;
      }
      .sitesBarVal{
        min-width:130px;
        text-align:right;
        color:var(--muted);
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
      }
      .sitesEmpty{
        color:var(--muted);
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
      }
      .tabsChartWrap{
        margin-top:10px;
        border:1px solid var(--line);
        border-radius:14px;
        padding:10px 12px;
        background:rgba(255,255,255,.03);
      }
      body.stats .tabsChartWrap{padding:8px 10px}
      .tabsSvg{
        width:100%;
        height:160px;
        display:block;
      }
      .tabsGrid line{
        stroke:rgba(255,255,255,.08);
        stroke-width:1;
      }
      .tabsAxisLabel{
        fill:rgba(255,255,255,.55);
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:10px;
      }
      .tabsLine{
        fill:none;
        stroke:rgba(96,165,250,.92);
        stroke-width:2;
      }
      .tabsArea{
        fill:rgba(96,165,250,.16);
      }
      .tabsPoint{
        fill:rgba(125,211,252,.95);
        stroke:rgba(15,23,32,.9);
        stroke-width:1.2;
      }
      .tabsValue{
        fill:rgba(255,255,255,.90);
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:11px;
        text-anchor:middle;
        paint-order:stroke;
        stroke:rgba(0,0,0,.45);
        stroke-width:2;
      }
      .tabsSplit{
        margin-top:12px;
        display:grid;
        grid-template-columns: 1fr 1.3fr;
        gap:12px;
      }
      @media (max-width: 980px){
        .tabsSplit{grid-template-columns: 1fr}
      }
      .tabsPanel{
        border:1px solid var(--line);
        border-radius:14px;
        padding:12px 12px;
        background:rgba(255,255,255,.03);
      }
      body.stats .tabsPanel{padding:10px 10px}
      .tabsPanelHd{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
        flex-wrap:wrap;
      }
      .tabsDonutSvg{
        width:140px;
        height:140px;
        flex:0 0 auto;
      }
      .tabsDonutRing{
        stroke:rgba(255,255,255,.12);
      }
      .tabsDonutText{
        fill:rgba(255,255,255,.88);
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:4.2px;
      }
      .tabsLegend{
        display:flex;
        flex-direction:column;
        gap:6px;
        font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size:12px;
        color:var(--muted);
        flex:1 1 160px;
      }
      .tabsListUrl{
        color:var(--muted);
        font-size:11px;
        margin-top:2px;
        word-break:break-all;
      }
      .tabsFlags{
        color:var(--muted);
        font-size:11px;
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
                    <circle class="donutRing" cx="21" cy="21" r="11.5" fill="transparent" stroke-width="3"></circle>
                    <g id="donut_segs_outer"></g>
                    <g id="donut_segs_inner"></g>
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
              <div class="timelineWrap">
                <div class="timelineAxis" id="timeline_axis" aria-hidden="true"></div>
                <div class="timelinePlot">
                  <div class="timelineGrid" id="timeline_grid" aria-hidden="true"></div>
                  <div class="timeline" id="timeline"></div>
                </div>
              </div>
              <div class="timelineLabels timelinePad" id="timeline_labels" aria-label="timeline labels"></div>
              <div class="timelineScale timelinePad">
                <span id="tl_from">-</span>
                <span id="tl_to">-</span>
              </div>
              <div class="sub" id="current"></div>
            </div>

            <div id="error" class="err" style="display:none"></div>

          </div>
        </section>

        <section class="card">
          <div class="hd">
            <div class="t" id="apps_label">Top Apps</div>
            <div class="appsControls">
              <label for="apps_mode">Mode</label>
              <select id="apps_mode">
                <option value="active" selected>active</option>
                <option value="visible">visible</option>
              </select>
              <div class="status" id="apps_status"></div>
            </div>
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
            <div class="t">Apps × Workspaces</div>
            <div class="status" id="ws_app_status"></div>
          </div>
          <div class="bd">
            <form class="controls">
              <div class="row">
                <label for="ws_app_rows">Top Apps</label>
                <select id="ws_app_rows">
                  <option value="8">8</option>
                  <option value="12" selected>12</option>
                  <option value="20">20</option>
                </select>
              </div>
              <div class="row">
                <label>Metric</label>
                <input type="text" value="visible time" disabled />
              </div>
            </form>
            <div class="sub" id="ws_app_info"></div>
            <div class="wsHeatmapWrap">
              <div class="wsHeatmap" id="ws_app_heatmap"></div>
            </div>
            <div class="wsLegend" id="ws_app_legend"></div>
          </div>
        </section>

        <section class="card onlyStats" style="grid-column: 1 / -1">
          <div class="hd">
            <div class="t">Websites</div>
            <div class="status" id="sites_status"></div>
          </div>
          <div class="bd">
            <form class="controls">
              <div class="row">
                <label for="sites_filter">Filter (domain/title)</label>
                <input id="sites_filter" type="text" placeholder="youtube, github..." />
              </div>
              <div class="row">
                <label for="sites_mode">Mode</label>
                <select id="sites_mode">
                  <option value="active" selected>active</option>
                  <option value="visible">visible</option>
                </select>
              </div>
              <div class="row">
                <label for="sites_rows">Rows</label>
                <select id="sites_rows">
                  <option value="20">20</option>
                  <option value="50" selected>50</option>
                  <option value="100">100</option>
                </select>
              </div>
              <div class="row">
                <label for="sites_group_filter">Group Filter</label>
                <select id="sites_group_filter">
                  <option value="0" selected>off</option>
                  <option value="1">group matches</option>
                </select>
              </div>
              <div class="row">
                <label for="sites_group_domain">Group By Domain</label>
                <select id="sites_group_domain">
                  <option value="0" selected>off</option>
                  <option value="1">base domain</option>
                </select>
              </div>
            </form>
            <div class="sub" id="sites_info"></div>
            <table>
              <thead>
                <tr>
                  <th style="width:48px">Pick</th>
                  <th style="text-align:left">Site</th>
                  <th style="text-align:right">Time</th>
                  <th style="text-align:right">Visits</th>
                  <th style="text-align:left">Last</th>
                </tr>
              </thead>
              <tbody id="sites_tbody"></tbody>
            </table>
            <div class="sitesChartWrap">
              <div class="sitesChartHeader">
                <div class="t">Selected Sites</div>
                <div class="appsControls">
                  <label for="sites_chart_metric">Metric</label>
                  <select id="sites_chart_metric">
                    <option value="time" selected>time</option>
                    <option value="visits">visits</option>
                  </select>
                  <button class="secondary" id="sites_clear" type="button">Clear</button>
                </div>
              </div>
              <div class="sitesChart" id="sites_chart"></div>
            </div>
            <div class="sitesNote">Based on window titles; best‑effort domain parsing.</div>
          </div>
        </section>

        <section class="card onlyStats" style="grid-column: 1 / -1">
          <div class="hd">
            <div class="t">Browser Tabs</div>
            <div class="status" id="tabs_status"></div>
          </div>
          <div class="bd">
            <div class="sub" id="tabs_info"></div>
            <div class="tabsChartWrap">
              <svg class="tabsSvg" id="tabs_svg" viewBox="0 0 600 160" preserveAspectRatio="none">
                <g class="tabsGrid" id="tabs_grid"></g>
                <path class="tabsArea" id="tabs_area" d=""></path>
                <path class="tabsLine" id="tabs_line" d=""></path>
                <g id="tabs_points"></g>
                <g id="tabs_labels"></g>
                <g id="tabs_axis_labels"></g>
              </svg>
              <div class="timelineScale" style="margin-top:6px">
                <span id="tabs_from">-</span>
                <span id="tabs_to">-</span>
              </div>
            </div>
            <div class="tabsSplit">
              <div class="tabsPanel">
                <div class="tabsPanelHd">
                  <div class="t">Tab Domains</div>
                  <div class="appsControls">
                    <label for="tabs_domain_top">Top</label>
                    <select id="tabs_domain_top">
                      <option value="5">5</option>
                      <option value="8">8</option>
                      <option value="12" selected>12</option>
                      <option value="20">20</option>
                    </select>
                  </div>
                </div>
                <div class="donutWrap" style="margin-top:8px">
                  <svg class="tabsDonutSvg" id="tabs_domain_svg" viewBox="0 0 42 42" role="img" aria-label="tabs domain share">
                    <circle class="tabsDonutRing" cx="21" cy="21" r="15.915" fill="transparent" stroke-width="4"></circle>
                    <g id="tabs_domain_segs"></g>
                    <text id="tabs_domain_text" x="21" y="21" text-anchor="middle" dominant-baseline="middle" class="tabsDonutText">-</text>
                  </svg>
                  <div class="tabsLegend" id="tabs_domain_legend"></div>
                </div>
                <div class="sub" id="tabs_domain_info"></div>
              </div>
              <div class="tabsPanel">
                <div class="tabsPanelHd">
                  <div class="t">Open Tabs (Latest)</div>
                  <div class="status" id="tabs_list_status"></div>
                </div>
                <form class="controls" id="tabs_list_form" style="margin-top:8px">
                  <div class="row">
                    <label for="tabs_list_filter">Filter (domain/title)</label>
                    <input id="tabs_list_filter" type="text" placeholder="gitlab, docs..." />
                  </div>
                  <div class="row">
                    <label for="tabs_list_rows">Rows</label>
                    <select id="tabs_list_rows">
                      <option value="50">50</option>
                      <option value="100" selected>100</option>
                      <option value="200">200</option>
                      <option value="500">500</option>
                    </select>
                  </div>
                </form>
                <div class="sub" id="tabs_list_info"></div>
                <table style="margin-top:10px">
                  <thead>
                    <tr>
                      <th style="text-align:left">Tab</th>
                      <th style="text-align:left">Domain</th>
                      <th style="text-align:left">Browser</th>
                      <th style="text-align:left">Flags</th>
                    </tr>
                  </thead>
                  <tbody id="tabs_list_body"></tbody>
                </table>
              </div>
            </div>
          </div>
        </section>

        <section class="card onlyStats" style="grid-column: 1 / -1">
          <div class="hd">
            <div class="t">Workspace Switches</div>
            <div class="status" id="ws_status"></div>
          </div>
          <div class="bd">
            <div class="sub" id="ws_info"></div>
            <div class="timelineWrap">
              <div class="timelineAxis" id="ws_axis" aria-hidden="true"></div>
              <div class="timelinePlot">
                <div class="timelineGrid" id="ws_grid" aria-hidden="true"></div>
                <div class="timeline wsChart" id="ws_chart"></div>
              </div>
            </div>
            <div class="timelineLabels timelinePad" id="ws_labels" aria-label="workspace switch labels"></div>
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

      function fmtHours(hours){
        const v = Math.round((Number(hours) || 0) * 10) / 10;
        return Number.isInteger(v) ? `${v}h` : `${v}h`;
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
        const total = Number(data && data.total_seconds != null ? data.total_seconds : (active + unknown)) || 0;

        const segsOuter = $("donut_segs_outer");
        const segsInner = $("donut_segs_inner");
        const legend = $("donut_legend");
        const text = $("donut_text");
        if (!segsOuter || !segsInner || !legend || !text) return;

        segsOuter.textContent = "";
        segsInner.textContent = "";
        legend.textContent = "";
        text.textContent = fmtSecondsShort(active);

        const ns = "http://www.w3.org/2000/svg";
        function renderRing(target, parts, denom, radius, strokeWidth){
          let offset = 25;
          for (const p of parts){
            const pct = denom > 0 ? (p.seconds / denom) * 100.0 : 0.0;
            if (pct <= 0.0001) continue;
            const c = document.createElementNS(ns, "circle");
            c.setAttribute("cx", "21");
            c.setAttribute("cy", "21");
            c.setAttribute("r", String(radius));
            c.setAttribute("fill", "transparent");
            c.setAttribute("stroke-width", String(strokeWidth));
            c.setAttribute("stroke", p.color);
            c.setAttribute("stroke-dasharray", `${pct} ${Math.max(0, 100 - pct)}`);
            c.setAttribute("stroke-dashoffset", String(offset));
            c.setAttribute("stroke-linecap", "butt");
            target.appendChild(c);
            offset -= pct;
          }
        }

        const nonAfk = Math.max(0, active - afk);
        const outerParts = [
          {seconds: active, color: "#2dd4bf"},
          {seconds: unknown, color: "rgba(255,255,255,.28)"},
        ];
        const innerParts = [
          {seconds: nonAfk, color: "rgba(45,212,191,.45)"},
          {seconds: afk, color: "#fbbf24"},
        ];
        renderRing(segsOuter, outerParts, total, 15.915, 4);
        renderRing(segsInner, innerParts, active, 11.5, 3);

        const parts = [
          {
            label: "Active",
            seconds: active,
            color: "#2dd4bf",
            pct: total > 0 ? (active / total) * 100.0 : 0.0,
            pctSuffix: "",
          },
          {
            label: "AFK (of active)",
            seconds: afk,
            color: "#fbbf24",
            pct: active > 0 ? (afk / active) * 100.0 : 0.0,
            pctSuffix: " of active",
          },
          {
            label: "Off",
            seconds: unknown,
            color: "rgba(255,255,255,.28)",
            pct: total > 0 ? (unknown / total) * 100.0 : 0.0,
            pctSuffix: "",
          },
        ];

        for (const p of parts){
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
          const pctText = `${Math.round(p.pct * 10) / 10}%${p.pctSuffix}`;
          val.textContent = `${fmtSeconds(p.seconds)} · ${pctText}`;

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

      function setAppsStatus(msg){
        const el = $("apps_status");
        if (el) el.textContent = msg || "";
      }

      let lastSummary = null;
      let lastSites = null;
      let lastSitesRows = [];
      let lastSitesAll = [];
      let lastSitesByKey = {};
      let lastSitesGroupedByKey = {};
      let lastSitesGroupRow = null;
      let lastTabs = null;
      const selectedSites = new Set();

      function getAppsMode(){
        const el = $("apps_mode");
        if (el && el.value) return String(el.value || "").trim() || "active";
        try{
          const saved = localStorage.getItem("aw_apps_mode");
          if (saved) return saved;
        }catch(e){}
        return "active";
      }

      function setAppsMode(value){
        const v = value === "visible" ? "visible" : "active";
        const el = $("apps_mode");
        if (el) el.value = v;
        try{ localStorage.setItem("aw_apps_mode", v); }catch(e){}
      }

      function setSitesStatus(msg){
        const el = $("sites_status");
        if (el) el.textContent = msg || "";
      }

      function getSitesMode(){
        const el = $("sites_mode");
        if (el && el.value) return String(el.value || "").trim() || "active";
        try{
          const saved = localStorage.getItem("aw_sites_mode");
          if (saved) return saved;
        }catch(e){}
        return "active";
      }

      function setSitesMode(value){
        const v = value === "visible" ? "visible" : "active";
        const el = $("sites_mode");
        if (el) el.value = v;
        try{ localStorage.setItem("aw_sites_mode", v); }catch(e){}
      }

      function getSitesGroupDomain(){
        const el = $("sites_group_domain");
        return el && el.value === "1";
      }

      function baseDomainFromHost(host){
        const h = normalizeHost(host);
        if (!h || h.indexOf(".") === -1) return h;
        const parts = h.split(".").filter(Boolean);
        if (parts.length <= 2) return h;
        const tld2 = parts.slice(-2).join(".");
        const multi = new Set([
          "co.uk","org.uk","ac.uk","gov.uk",
          "com.au","net.au","org.au",
          "co.nz",
          "com.br","com.mx","com.ar","com.tr","com.pl","com.ru","com.cn","com.tw","com.hk","com.sg","com.my","com.ph","com.sa","com.ng",
          "co.in","co.jp","co.kr","co.id","co.il"
        ]);
        if (multi.has(tld2) && parts.length >= 3){
          return parts.slice(-3).join(".");
        }
        return parts.slice(-2).join(".");
      }

      function groupKeyForSite(site){
        const s = String(site || "").trim();
        if (!s) return "";
        const lower = s.toLowerCase();
        if (!lower.includes(" ") && lower.includes(".")){
          return baseDomainFromHost(lower);
        }
        const parts = s.split(/[·\\-–—|/]/).map((p) => p.trim()).filter(Boolean);
        const last = parts.length ? parts[parts.length - 1] : s;
        return String(last || "").toLowerCase();
      }

      const BROWSER_HINTS = [
        "firefox",
        "librewolf",
        "floorp",
        "zen",
        "brave",
        "chrome",
        "chromium",
        "vivaldi",
        "opera",
        "edge",
        "microsoft-edge",
        "thorium",
      ];

      function isBrowserApp(app){
        const a = String(app || "").toLowerCase();
        if (!a) return false;
        return BROWSER_HINTS.some((k) => a.includes(k));
      }

      function stripBrowserSuffix(title){
        const t = String(title || "").trim();
        if (!t) return "";
        return t.replace(/\\s+[\\-–—]\\s*(Mozilla Firefox|Firefox|Brave|Google Chrome|Chromium|Vivaldi|Opera|Microsoft Edge|Edge|Thorium|LibreWolf|Floorp|Zen)\\s*$/i, "").trim();
      }

      function extractHostFromTitle(title){
        const t = String(title || "");
        if (!t) return null;
        const urlMatch = t.match(/https?:\\/\\/[^\\s]+/i);
        if (urlMatch){
          try{
            const u = new URL(urlMatch[0]);
            return u.hostname;
          }catch(e){}
        }
        const wwwMatch = t.match(/\\bwww\\.[^\\s/]+\\.[^\\s)\\],.]+/i);
        if (wwwMatch){
          try{
            const u = new URL(`http://${wwwMatch[0]}`);
            return u.hostname;
          }catch(e){}
        }
        const hostMatch = t.match(/\\b([a-z0-9.-]+\\.[a-z]{2,})(?:\\b|\\/)/i);
        if (hostMatch){
          return hostMatch[1];
        }
        return null;
      }

      function normalizeHost(host){
        return String(host || "")
          .toLowerCase()
          .replace(/^www\\./, "")
          .replace(/[\\])},.]+$/, "");
      }

      function extractSite(app, title){
        const host = extractHostFromTitle(title);
        if (host){
          const h = normalizeHost(host);
          return h || null;
        }
        if (isBrowserApp(app)){
          const t = stripBrowserSuffix(title);
          return t || null;
        }
        return null;
      }

      function parseFilterTokens(raw){
        return String(raw || "")
          .toLowerCase()
          .split(/[,\\s]+/)
          .map((t) => t.trim())
          .filter(Boolean);
      }

      function parseUrlSafe(raw){
        const s = String(raw || "").trim();
        if (!s) return null;
        try{
          return new URL(s);
        }catch(e){}
        try{
          return new URL(`http://${s}`);
        }catch(e){}
        return null;
      }

      function tabDomainFromTab(tab){
        const url = String((tab && (tab.url || tab.pending_url || tab.pendingUrl)) || "").trim();
        if (url){
          const parsed = parseUrlSafe(url);
          if (parsed){
            const host = normalizeHost(parsed.hostname);
            const proto = String(parsed.protocol || "").replace(":", "");
            if (host){
              if (proto && proto !== "http" && proto !== "https" && host.indexOf(".") === -1){
                return proto;
              }
              return baseDomainFromHost(host);
            }
            if (proto && proto !== "http" && proto !== "https"){
              return proto;
            }
          }
        }
        const title = String((tab && tab.title) || "");
        if (title){
          const hostFromTitle = extractHostFromTitle(title);
          if (hostFromTitle){
            const h = normalizeHost(hostFromTitle);
            if (h) return baseDomainFromHost(h);
          }
        }
        return "internal";
      }

      function sourceToBrowserLabel(source){
        const s = String(source || "");
        if (s.startsWith("tabs:")) return s.slice(5);
        return s || "browser";
      }

      function tabFlags(tab){
        const flags = [];
        if (tab && tab.active) flags.push("active");
        if (tab && tab.pinned) flags.push("pinned");
        if (tab && tab.highlighted) flags.push("highlighted");
        if (tab && tab.incognito) flags.push("incognito");
        if (tab && tab.audible) flags.push("audible");
        if (tab && tab.muted) flags.push("muted");
        if (tab && tab.discarded) flags.push("discarded");
        if (tab && tab.status && !flags.includes(tab.status)) flags.push(tab.status);
        return flags.length ? flags.join(", ") : "-";
      }

      function renderTopAppsTable(apps, modeLabel, rangeKey, pctKey){
        const tbody = $("apps");
        if (!tbody) return;
        $("apps_label").textContent = `Top Apps (${modeLabel}) · ${rangeKey}`;
        tbody.textContent = "";

        const totalSeconds = apps.reduce((sum, a) => sum + (Number(a.seconds) || 0), 0);

        for (const a of apps.slice(0, 20)){
          const tr = document.createElement("tr");
          const tdApp = document.createElement("td");
          tdApp.textContent = a.app || "";
          const tdTime = document.createElement("td");
          tdTime.style.textAlign = "right";
          tdTime.textContent = fmtSeconds(a.seconds || 0);
          const tdPct = document.createElement("td");
          tdPct.style.textAlign = "right";
          const pctRaw = (pctKey && a[pctKey] != null)
            ? a[pctKey]
            : (totalSeconds > 0 ? ((Number(a.seconds) || 0) / totalSeconds) * 100.0 : 0.0);
          tdPct.textContent = `${Math.round(pctRaw * 10) / 10}%`;
          const tdBar = document.createElement("td");
          const bar = document.createElement("div");
          bar.className = "bar";
          const fill = document.createElement("div");
          const pctClamped = Math.max(0, Math.min(100, Number(pctRaw) || 0));
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
      }

      function renderTopAppsFromSummary(data, rangeKey){
        if (!data) return;
        const mode = getAppsMode();
        if (mode !== "active") return;
        setAppsStatus("");

        let apps = Array.isArray(data.top_apps_active) ? data.top_apps_active : [];
        let modeLabel = "active";
        let pctKey = "percent_active";

        if (!apps.length){
          const fallback = Array.isArray(data.top_apps_window) ? data.top_apps_window : [];
          if (fallback.length){
            apps = fallback;
            modeLabel = "window";
            pctKey = "percent_window";
            setAppsStatus("active: no idle data");
          }
        }

        renderTopAppsTable(apps, modeLabel, rangeKey, pctKey);
      }

      async function refreshTopApps(){
        const ctx = window.__aw_apps_ctx;
        const rangeKey = ctx ? ctx.rangeKey : "24h";
        const mode = getAppsMode();
        if (mode === "visible"){
          if (ctx){
            await loadTopAppsVisible(ctx);
          }else{
            renderTopAppsTable([], "visible", rangeKey, "percent_visible");
          }
          return;
        }
        renderTopAppsFromSummary(lastSummary, rangeKey);
      }

      async function loadTopAppsVisible({fromTs, toTs, rangeKey}){
        setAppsStatus("visible: fetching...");
        const url = new URL("/v1/events", window.location.origin);
        url.searchParams.set("bucket", "window_visible");
        if (toTs) url.searchParams.set("to", String(toTs));
        if (fromTs) url.searchParams.set("from", String(fromTs));

        const started = performance.now();
        let data;
        try{
          const res = await fetch(url.toString(), {cache:"no-store"});
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          data = await res.json();
        }catch(e){
          setAppsStatus("visible: error");
          renderTopAppsTable([], "visible", rangeKey, "percent_visible");
          return;
        }
        const ms = Math.round(performance.now() - started);
        setAppsStatus(`visible: ok (${ms}ms)`);

        const events = (data && Array.isArray(data.events)) ? data.events : [];
        if (!events.length){
          setAppsStatus("visible: no data");
          renderTopAppsTable([], "visible", rangeKey, "percent_visible");
          return;
        }
        const totals = {};
        for (const e of events){
          const d = (e && e.data) ? e.data : {};
          const app = d && d.app ? String(d.app) : "";
          if (!app || app.startsWith("__")) continue;
          const start = Date.parse(String(e.start_ts || ""));
          const end = Date.parse(String(e.end_ts || ""));
          if (isNaN(start) || isNaN(end) || end <= start) continue;
          const dur = (end - start) / 1000.0;
          totals[app] = (totals[app] || 0) + dur;
        }

        const apps = Object.keys(totals)
          .map((app) => ({app, seconds: totals[app]}))
          .sort((a, b) => b.seconds - a.seconds);

        const totalSeconds = apps.reduce((sum, a) => sum + (Number(a.seconds) || 0), 0);
        const withPct = apps.map((a) => ({
          app: a.app,
          seconds: a.seconds,
          percent_visible: totalSeconds > 0 ? (a.seconds / totalSeconds) * 100.0 : 0.0,
        }));

        renderTopAppsTable(withPct, "visible", rangeKey, "percent_visible");
      }

      function renderSitesChart(rangeKey){
        const chart = $("sites_chart");
        if (!chart) return;
        chart.textContent = "";

        const metric = $("sites_chart_metric")?.value || "time";
        const rows = [];
        const groupDomain = getSitesGroupDomain();
        const lookup = groupDomain ? lastSitesGroupedByKey : lastSitesByKey;
        for (const key of Array.from(selectedSites)){
          const r = (lastSitesGroupRow && lastSitesGroupRow.key === key)
            ? lastSitesGroupRow
            : lookup[key];
          if (!r) continue;
          rows.push(r);
        }
        rows.sort((a, b) => {
          const av = metric === "visits" ? (Number(a.visits) || 0) : (Number(a.seconds) || 0);
          const bv = metric === "visits" ? (Number(b.visits) || 0) : (Number(b.seconds) || 0);
          return bv - av;
        });

        if (!rows.length){
          const empty = document.createElement("div");
          empty.className = "sitesEmpty";
          empty.textContent = "Select sites from the table to compare.";
          chart.appendChild(empty);
          return;
        }

        const maxVal = rows.reduce((m, r) => {
          const v = metric === "visits" ? (Number(r.visits) || 0) : (Number(r.seconds) || 0);
          return Math.max(m, v);
        }, 0);

        for (const r of rows){
          const v = metric === "visits" ? (Number(r.visits) || 0) : (Number(r.seconds) || 0);
          const pct = maxVal > 0 ? (v / maxVal) * 100.0 : 0.0;

          const row = document.createElement("div");
          row.className = "sitesBarRow";

          const label = document.createElement("div");
          label.className = "sitesBarLabel";
          label.textContent = r.site;
          label.title = r.site;

          const track = document.createElement("div");
          track.className = "sitesBarTrack";
          const fill = document.createElement("div");
          fill.className = "sitesBarFill";
          fill.style.width = `${Math.max(0, Math.min(100, pct))}%`;
          track.appendChild(fill);

          const val = document.createElement("div");
          val.className = "sitesBarVal";
          if (metric === "visits"){
            val.textContent = `${r.visits} visits · ${fmtSeconds(r.seconds || 0)}`;
          }else{
            val.textContent = `${fmtSeconds(r.seconds || 0)} · ${r.visits} visits`;
          }

          row.appendChild(label);
          row.appendChild(track);
          row.appendChild(val);
          chart.appendChild(row);
        }
      }

      function renderSitesTable(rows, rangeKey){
        const tbody = $("sites_tbody");
        if (!tbody) return;
        tbody.textContent = "";
        lastSitesRows = rows.slice();

        for (const r of rows){
          const tr = document.createElement("tr");
          const tdPick = document.createElement("td");
          const cb = document.createElement("input");
          cb.type = "checkbox";
          const key = r.key || r.site;
          cb.checked = selectedSites.has(key);
          cb.addEventListener("change", () => {
            if (cb.checked) selectedSites.add(key);
            else selectedSites.delete(key);
            renderSitesChart(rangeKey);
          });
          tdPick.appendChild(cb);
          const tdSite = document.createElement("td");
          tdSite.textContent = r.site;
          tdSite.title = r.site;
          const tdTime = document.createElement("td");
          tdTime.style.textAlign = "right";
          tdTime.textContent = fmtSeconds(r.seconds || 0);
          const tdVisits = document.createElement("td");
          tdVisits.style.textAlign = "right";
          tdVisits.textContent = String(r.visits || 0);
          const tdLast = document.createElement("td");
          tdLast.textContent = r.last_ts ? fmtTsLocal(r.last_ts) : "";
          tdLast.title = r.last_ts || "";
          tr.appendChild(tdPick);
          tr.appendChild(tdSite);
          tr.appendChild(tdTime);
          tr.appendChild(tdVisits);
          tr.appendChild(tdLast);
          tbody.appendChild(tr);
        }

        if (!rows.length){
          const tr = document.createElement("tr");
          const td = document.createElement("td");
          td.colSpan = 4;
          td.style.color = "rgba(255,255,255,.66)";
          td.textContent = "No website data for this range.";
          tr.appendChild(td);
          tbody.appendChild(tr);
        }

        const info = $("sites_info");
        if (info){
          const totalSites = rows.length;
          const totalSeconds = rows.reduce((sum, r) => sum + (Number(r.seconds) || 0), 0);
          info.textContent = `${totalSites} sites · ${fmtSeconds(totalSeconds)} · ${rangeKey}`;
        }

        renderSitesChart(rangeKey);
      }

      function renderSitesFromEvents(events, rangeKey){
        const filterTokens = parseFilterTokens($("sites_filter")?.value || "");
        const groupFilter = String($("sites_group_filter")?.value || "0") === "1";
        const groupDomain = getSitesGroupDomain();
        const rowsLimit = parseInt($("sites_rows")?.value || "50", 10) || 50;
        const bySite = {};

        for (const e of events){
          const d = (e && e.data) ? e.data : {};
          const app = d && d.app ? String(d.app) : "";
          const title = d && d.title ? String(d.title) : "";
          const site = extractSite(app, title);
          if (!site) continue;

          const start = Date.parse(String(e.start_ts || ""));
          const end = Date.parse(String(e.end_ts || ""));
          if (isNaN(start) || isNaN(end) || end <= start) continue;
          const dur = (end - start) / 1000.0;

          if (!bySite[site]){
            bySite[site] = {site, seconds: 0, visits: 0, last_ts: ""};
          }
          bySite[site].seconds += dur;
          bySite[site].visits += 1;
          const endIso = String(e.end_ts || "");
          if (!bySite[site].last_ts || endIso > bySite[site].last_ts){
            bySite[site].last_ts = endIso;
          }
        }

        const allRows = Object.values(bySite).sort((a, b) => b.seconds - a.seconds);
        lastSitesAll = allRows;
        lastSitesByKey = {};
        for (const r of allRows){
          r.key = r.site;
          lastSitesByKey[r.key] = r;
        }
        lastSitesGroupedByKey = {};
        if (allRows.length){
          const grouped = {};
          for (const r of allRows){
            const g = groupKeyForSite(r.site);
            if (!g) continue;
            if (!grouped[g]){
              grouped[g] = {key: `domain:${g}`, site: g, seconds: 0, visits: 0, last_ts: ""};
            }
            grouped[g].seconds += Number(r.seconds) || 0;
            grouped[g].visits += Number(r.visits) || 0;
            if (r.last_ts && r.last_ts > grouped[g].last_ts) grouped[g].last_ts = r.last_ts;
          }
          for (const g of Object.keys(grouped)){
            lastSitesGroupedByKey[grouped[g].key] = grouped[g];
          }
        }

        let filteredRows = allRows;
        if (filterTokens.length){
          filteredRows = allRows.filter((r) =>
            filterTokens.some((t) => String(r.site || "").toLowerCase().includes(t))
          );
        }

        let viewRows = filteredRows;
        if (groupDomain && filteredRows.length){
          const groupSet = new Set(filteredRows.map((r) => groupKeyForSite(r.site)).filter(Boolean));
          const groupedView = [];
          for (const g of Array.from(groupSet)){
            const key = `domain:${g}`;
            const row = lastSitesGroupedByKey[key];
            if (row) groupedView.push(row);
          }
          groupedView.sort((a, b) => b.seconds - a.seconds);
          viewRows = groupedView;
        }

        lastSitesGroupRow = null;
        if (groupFilter && filterTokens.length && filteredRows.length){
          const groupKey = `group:${filterTokens.join("|")}`;
          let seconds = 0;
          let visits = 0;
          let lastTs = "";
          for (const r of filteredRows){
            seconds += Number(r.seconds) || 0;
            visits += Number(r.visits) || 0;
            if (r.last_ts && r.last_ts > lastTs) lastTs = r.last_ts;
          }
          lastSitesGroupRow = {
            key: groupKey,
            site: `group: ${filterTokens.join(", ")}`,
            seconds,
            visits,
            last_ts: lastTs,
          };
          viewRows = [lastSitesGroupRow, ...viewRows];
        }

        const rows = viewRows.slice(0, rowsLimit);
        renderSitesTable(rows, rangeKey);
      }

      async function loadSites({fromTs, toTs, rangeKey}){
        if (!IS_STATS_PAGE) return;
        const mode = getSitesMode();
        const bucket = mode === "visible" ? "window_visible" : "window";

        if (lastSites && lastSites.mode === mode && lastSites.fromTs === fromTs && lastSites.toTs === toTs){
          renderSitesFromEvents(lastSites.events, rangeKey);
          return;
        }

        setSitesStatus(`${mode}: fetching...`);
        const url = new URL("/v1/events", window.location.origin);
        url.searchParams.set("bucket", bucket);
        if (toTs) url.searchParams.set("to", String(toTs));
        if (fromTs) url.searchParams.set("from", String(fromTs));

        const started = performance.now();
        let data;
        try{
          const res = await fetch(url.toString(), {cache:"no-store"});
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          data = await res.json();
        }catch(e){
          setSitesStatus(`${mode}: error`);
          renderSitesTable([], rangeKey);
          return;
        }
        const ms = Math.round(performance.now() - started);
        setSitesStatus(`${mode}: ok (${ms}ms)`);

        const events = (data && Array.isArray(data.events)) ? data.events : [];
        lastSites = {mode, fromTs, toTs, events};
        selectedSites.clear();
        renderSitesFromEvents(events, rangeKey);
      }

      async function loadTabsChart({fromTs, toTs, rangeKey}){
        if (!IS_STATS_PAGE) return;
        const status = $("tabs_status");
        const info = $("tabs_info");
        const grid = $("tabs_grid");
        const line = $("tabs_line");
        const area = $("tabs_area");
        const pointsG = $("tabs_points");
        const labelsG = $("tabs_labels");
        const labels = $("tabs_axis_labels");
        if (grid) grid.textContent = "";
        if (labels) labels.textContent = "";
        if (pointsG) pointsG.textContent = "";
        if (labelsG) labelsG.textContent = "";
        if (line) line.setAttribute("d", "");
        if (area) area.setAttribute("d", "");

        const url = new URL("/v1/events", window.location.origin);
        url.searchParams.set("bucket", "browser_tabs");
        if (toTs) url.searchParams.set("to", String(toTs));
        if (fromTs) url.searchParams.set("from", String(fromTs));

        if (status) status.textContent = "fetching...";
        let data;
        const started = performance.now();
        try{
          const res = await fetch(url.toString(), {cache:"no-store"});
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          data = await res.json();
        }catch(e){
          if (status) status.textContent = "error";
          if (info) info.textContent = `Failed to load browser tabs: ${e}`;
          lastTabs = null;
          renderTabsDomains(null);
          renderTabsList(null);
          return;
        }
        const ms = Math.round(performance.now() - started);
        if (status) status.textContent = `ok (${ms}ms)`;

        const fromMs = Date.parse(String(fromTs || (data && data.from_ts) || ""));
        const toMs = Date.parse(String(toTs || (data && data.to_ts) || ""));
        if (isNaN(fromMs) || isNaN(toMs) || toMs <= fromMs){
          if (info) info.textContent = "No range for tabs.";
          lastTabs = null;
          renderTabsDomains(null);
          renderTabsList(null);
          return;
        }

        const events = (data && Array.isArray(data.events)) ? data.events : [];
        if (!events.length){
          if (info) info.textContent = "No browser tab data yet (install the tabs extension).";
          lastTabs = {events, fromMs, toMs, rangeKey};
          renderTabsDomains(lastTabs);
          renderTabsList(lastTabs);
          return;
        }

        const changes = [];
        for (const e of events){
          const d = (e && e.data) ? e.data : {};
          const count = Number(d.count ?? d.tabs ?? 0) || 0;
          const start = Date.parse(String(e.start_ts || ""));
          const end = Date.parse(String(e.end_ts || ""));
          if (isNaN(start) || isNaN(end) || end <= start) continue;
          if (end <= fromMs || start >= toMs) continue;
          changes.push({t: start, delta: count});
          changes.push({t: end, delta: -count});
        }
        changes.sort((a, b) => a.t - b.t);

        let total = 0;
        const points = [{t: fromMs, v: 0}];
        let i = 0;
        while (i < changes.length){
          const t = changes[i].t;
          let delta = 0;
          while (i < changes.length && changes[i].t === t){
            delta += changes[i].delta;
            i++;
          }
          if (t < fromMs){
            total += delta;
            points[0].v = total;
            continue;
          }
          if (t > toMs) break;
          total += delta;
          points.push({t, v: total});
        }
        const last = points[points.length - 1];
        if (!last || last.t !== toMs){
          points.push({t: toMs, v: total});
        }

        let maxVal = points[0] ? points[0].v : 0;
        let minVal = points[0] ? points[0].v : 0;
        let areaSum = 0;
        for (let j = 0; j < points.length - 1; j++){
          const v = points[j].v;
          const dt = Math.max(0, points[j + 1].t - points[j].t);
          areaSum += v * dt;
          if (v > maxVal) maxVal = v;
          if (v < minVal) minVal = v;
        }
        if (points.length){
          const vLast = points[points.length - 1].v;
          if (vLast > maxVal) maxVal = vLast;
          if (vLast < minVal) minVal = vLast;
        }

        const durationMs = Math.max(1, toMs - fromMs);
        const avg = areaSum / durationMs;
        if (info){
          info.textContent = `avg ${avg.toFixed(1)} · max ${maxVal} · min ${minVal} · ${rangeKey}`;
        }

        const svg = $("tabs_svg");
        let w = 600;
        let h = 160;
        if (svg){
          const rect = svg.getBoundingClientRect();
          if (rect && rect.width > 0 && rect.height > 0){
            w = Math.round(rect.width);
            h = Math.round(rect.height);
            svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
          }
        }
        const useIndexScale = points.length <= 8;
        const x = (t, idx) => {
          if (useIndexScale){
            const denom = Math.max(1, points.length - 1);
            return (idx / denom) * w;
          }
          return ((t - fromMs) / durationMs) * w;
        };
        const y = (v) => {
          if (maxVal <= 0) return h;
          return h - Math.max(0, Math.min(1, v / maxVal)) * h;
        };

        let dLine = "";
        let dArea = "";
        if (points.length){
          const x0 = x(points[0].t, 0);
          const y0 = y(points[0].v);
          dLine = `M ${x0} ${y0}`;
          dArea = `M ${x0} ${h} L ${x0} ${y0}`;
          for (let j = 1; j < points.length; j++){
            const xj = x(points[j].t, j);
            const yPrev = y(points[j - 1].v);
            const yj = y(points[j].v);
            dLine += ` L ${xj} ${yPrev} L ${xj} ${yj}`;
            dArea += ` L ${xj} ${yPrev} L ${xj} ${yj}`;
          }
          const xLast = x(points[points.length - 1].t, points.length - 1);
          dArea += ` L ${xLast} ${h} Z`;
        }
        if (line) line.setAttribute("d", dLine);
        if (area) area.setAttribute("d", dArea);

        if (pointsG){
          const labelEvery = points.length <= 12 ? 1 : Math.ceil(points.length / 12);
          for (let j = 0; j < points.length; j++){
            const pj = points[j];
            const xj = x(pj.t, j);
            const yj = y(pj.v);
            const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            c.setAttribute("class", "tabsPoint");
            c.setAttribute("cx", String(xj));
            c.setAttribute("cy", String(yj));
            c.setAttribute("r", "3.2");
            pointsG.appendChild(c);

            if (labelsG && (j % labelEvery === 0 || j === points.length - 1)){
              const t = document.createElementNS("http://www.w3.org/2000/svg", "text");
              t.setAttribute("class", "tabsValue");
              t.setAttribute("x", String(xj));
              t.setAttribute("y", String(Math.max(10, yj - 6)));
              t.textContent = String(pj.v);
              labelsG.appendChild(t);
            }
          }
        }

        if (grid){
          const ticks = [maxVal, Math.round(maxVal / 2), 0];
          for (const v of ticks){
            const yv = y(v);
            const ln = document.createElementNS("http://www.w3.org/2000/svg", "line");
            ln.setAttribute("x1", "0");
            ln.setAttribute("x2", String(w));
            ln.setAttribute("y1", String(yv));
            ln.setAttribute("y2", String(yv));
            grid.appendChild(ln);
          }
        }
        if (labels){
          const ticks = [maxVal, Math.round(maxVal / 2), 0];
          for (const v of ticks){
            const yv = y(v);
            const t = document.createElementNS("http://www.w3.org/2000/svg", "text");
            t.setAttribute("x", "4");
            t.setAttribute("y", String(Math.max(10, yv - 2)));
            t.setAttribute("class", "tabsAxisLabel");
            t.textContent = String(v);
            labels.appendChild(t);
          }
        }

        const tlFrom = $("tabs_from");
        const tlTo = $("tabs_to");
        if (tlFrom) tlFrom.textContent = fmtTsLocal(new Date(fromMs).toISOString());
        if (tlTo) tlTo.textContent = fmtTsLocal(new Date(toMs).toISOString());

        lastTabs = {events, fromMs, toMs, rangeKey};
        renderTabsDomains(lastTabs);
        renderTabsList(lastTabs);
      }

      function getTabsDomainTop(){
        const el = $("tabs_domain_top");
        const v = parseInt(el ? el.value : "12", 10);
        return isNaN(v) ? 12 : v;
      }

      function computeTabsDomainTotals(events, fromMs, toMs){
        const totals = new Map();
        let coveredSeconds = 0;
        let totalTabSeconds = 0;
        for (const e of events){
          const start = Date.parse(String(e.start_ts || ""));
          const end = Date.parse(String(e.end_ts || ""));
          if (isNaN(start) || isNaN(end) || end <= start) continue;
          if (end <= fromMs || start >= toMs) continue;
          const durSec = (Math.min(end, toMs) - Math.max(start, fromMs)) / 1000.0;
          if (durSec <= 0) continue;
          const d = (e && e.data) ? e.data : {};
          const tabs = Array.isArray(d.tabs) ? d.tabs : null;
          if (!tabs) continue;
          coveredSeconds += durSec;
          for (const tab of tabs){
            const key = tabDomainFromTab(tab);
            if (!key) continue;
            totals.set(key, (totals.get(key) || 0) + durSec);
            totalTabSeconds += durSec;
          }
        }
        return {totals, totalTabSeconds, coveredSeconds};
      }

      function renderTabsDomains(state){
        const segs = $("tabs_domain_segs");
        const legend = $("tabs_domain_legend");
        const text = $("tabs_domain_text");
        const info = $("tabs_domain_info");
        if (segs) segs.textContent = "";
        if (legend) legend.textContent = "";
        if (text) text.textContent = "-";
        if (info) info.textContent = "";

        if (!state || !Array.isArray(state.events)){
          if (info) info.textContent = "No tab data.";
          return;
        }
        const {events, fromMs, toMs} = state;
        const totalsResult = computeTabsDomainTotals(events, fromMs, toMs);
        const entries = Array.from(totalsResult.totals.entries()).map(([label, seconds]) => ({
          label,
          seconds,
        }));
        if (!entries.length){
          if (info) info.textContent = "No tab detail data yet (update the tabs extension).";
          return;
        }
        entries.sort((a, b) => b.seconds - a.seconds);
        const topN = getTabsDomainTop();
        let shown = entries;
        let otherSeconds = 0;
        if (topN > 0 && entries.length > topN){
          shown = entries.slice(0, topN);
          for (let i = topN; i < entries.length; i++){
            otherSeconds += entries[i].seconds;
          }
          if (otherSeconds > 0){
            shown = [...shown, {label: "Other", seconds: otherSeconds, color: "rgba(255,255,255,.22)"}];
          }
        }

        const total = shown.reduce((sum, item) => sum + item.seconds, 0);
        if (text) text.textContent = total > 0 ? fmtHours(total / 3600.0) : "0h";
        if (info){
          const rangeLabel = state.rangeKey ? ` · ${state.rangeKey}` : "";
          info.textContent = `${entries.length} domains · ${fmtSecondsShort(total)} tab-time${rangeLabel}`;
        }

        const colors = [];
        const n = shown.length;
        for (let i = 0; i < n; i++){
          if (shown[i].label === "Other"){
            colors.push("rgba(255,255,255,.22)");
          }else{
            const t = n <= 1 ? 0.5 : i / Math.max(1, n - 1);
            const hue = 180 + 160 * t;
            const sat = 78;
            const light = 58 - 6 * Math.abs(0.5 - t);
            colors.push(`hsl(${hue} ${sat}% ${light}%)`);
          }
        }

        if (segs){
          const ns = "http://www.w3.org/2000/svg";
          let offset = 25;
          for (let i = 0; i < shown.length; i++){
            const item = shown[i];
            const pct = total > 0 ? (item.seconds / total) * 100.0 : 0.0;
            if (pct <= 0.0001) continue;
            const c = document.createElementNS(ns, "circle");
            c.setAttribute("cx", "21");
            c.setAttribute("cy", "21");
            c.setAttribute("r", "15.915");
            c.setAttribute("fill", "transparent");
            c.setAttribute("stroke-width", "4");
            const color = item.color || colors[i];
            c.setAttribute("stroke", color);
            c.setAttribute("stroke-dasharray", `${pct} ${Math.max(0, 100 - pct)}`);
            c.setAttribute("stroke-dashoffset", String(offset));
            c.setAttribute("stroke-linecap", "butt");
            segs.appendChild(c);
            offset -= pct;
            item.color = color;
          }
        }

        if (legend){
          for (const item of shown){
            const row = document.createElement("div");
            row.className = "legendItem";
            const left = document.createElement("div");
            left.className = "legendLeft";
            const dot = document.createElement("span");
            dot.className = "dot";
            dot.style.background = item.color;
            const label = document.createElement("span");
            label.textContent = item.label;
            left.appendChild(dot);
            left.appendChild(label);
            const val = document.createElement("span");
            val.className = "legendVal";
            const pct = total > 0 ? Math.round((item.seconds / total) * 100.0) : 0;
            val.textContent = `${fmtSecondsShort(item.seconds)} (${pct}%)`;
            row.appendChild(left);
            row.appendChild(val);
            legend.appendChild(row);
          }
        }
      }

      function renderTabsList(state){
        const tbody = $("tabs_list_body");
        const info = $("tabs_list_info");
        const status = $("tabs_list_status");
        if (tbody) tbody.textContent = "";
        if (info) info.textContent = "";
        if (status) status.textContent = "";

        if (!state || !Array.isArray(state.events)){
          if (info) info.textContent = "No tab data.";
          return;
        }

        const events = state.events;
        const toMs = state.toMs;
        const latestBySource = new Map();
        for (const e of events){
          const d = (e && e.data) ? e.data : {};
          const tabs = Array.isArray(d.tabs) ? d.tabs : null;
          if (!tabs) continue;
          const start = Date.parse(String(e.start_ts || ""));
          const end = Date.parse(String(e.end_ts || ""));
          if (isNaN(start) || isNaN(end) || end <= start) continue;
          if (!isNaN(toMs) && start > toMs) continue;
          const t = !isNaN(toMs) ? Math.min(end, toMs) : end;
          const key = String(e.source || d.browser || "tabs");
          const prev = latestBySource.get(key);
          if (!prev || t > prev.t){
            latestBySource.set(key, {
              t,
              tabs,
              browser: d.browser || sourceToBrowserLabel(e.source),
              source: e.source || "",
            });
          }
        }

        if (!latestBySource.size){
          if (info) info.textContent = "No tab detail data yet (update the tabs extension).";
          return;
        }

        let latestTs = 0;
        let tabsAll = [];
        for (const entry of latestBySource.values()){
          if (entry.t > latestTs) latestTs = entry.t;
          const browser = entry.browser || sourceToBrowserLabel(entry.source);
          for (const t of entry.tabs || []){
            tabsAll.push({...t, __browser: browser});
          }
        }

        const filterTokens = parseFilterTokens($("tabs_list_filter") ? $("tabs_list_filter").value : "");
        if (filterTokens.length){
          tabsAll = tabsAll.filter((t) => {
            const title = String(t.title || "");
            const url = String(t.url || t.pending_url || t.pendingUrl || "");
            const domain = tabDomainFromTab(t);
            const hay = `${title} ${url} ${domain}`.toLowerCase();
            return filterTokens.some((tok) => hay.includes(tok));
          });
        }

        tabsAll.sort((a, b) => {
          const ab = String(a.__browser || "");
          const bb = String(b.__browser || "");
          if (ab !== bb) return ab.localeCompare(bb);
          const aw = Number(a.window_id ?? a.windowId ?? 0);
          const bw = Number(b.window_id ?? b.windowId ?? 0);
          if (aw !== bw) return aw - bw;
          const ai = Number(a.index ?? 0);
          const bi = Number(b.index ?? 0);
          return ai - bi;
        });

        const rowsLimit = parseInt($("tabs_list_rows") ? $("tabs_list_rows").value : "100", 10) || 100;
        const viewRows = tabsAll.slice(0, rowsLimit);
        const domainSet = new Set();
        for (const t of tabsAll){
          domainSet.add(tabDomainFromTab(t));
        }
        if (info){
          const rangeLabel = state.rangeKey ? ` · ${state.rangeKey}` : "";
          info.textContent = `${tabsAll.length} tabs · ${domainSet.size} domains${rangeLabel}`;
        }
        if (status && latestTs){
          status.textContent = `latest ${fmtTsLocal(new Date(latestTs).toISOString())}`;
        }

        if (!tbody) return;
        for (const t of viewRows){
          const tr = document.createElement("tr");
          const tdTab = document.createElement("td");
          const title = String(t.title || t.url || t.pending_url || t.pendingUrl || "(untitled)");
          const url = String(t.url || t.pending_url || t.pendingUrl || "");
          const titleDiv = document.createElement("div");
          titleDiv.textContent = title;
          tdTab.appendChild(titleDiv);
          if (url){
            const urlDiv = document.createElement("div");
            urlDiv.className = "tabsListUrl";
            urlDiv.textContent = url;
            tdTab.appendChild(urlDiv);
          }
          const tdDomain = document.createElement("td");
          tdDomain.textContent = tabDomainFromTab(t);
          const tdBrowser = document.createElement("td");
          tdBrowser.textContent = String(t.__browser || "");
          const tdFlags = document.createElement("td");
          tdFlags.textContent = tabFlags(t);
          tdFlags.className = "tabsFlags";
          tr.appendChild(tdTab);
          tr.appendChild(tdDomain);
          tr.appendChild(tdBrowser);
          tr.appendChild(tdFlags);
          tbody.appendChild(tr);
        }
      }

      function renderCountAxis(axisId, gridId, maxValue){
        const axis = $(axisId);
        const grid = $(gridId);
        if (axis) axis.textContent = "";
        if (grid) grid.textContent = "";
        if (!axis && !grid) return;

        const max = Math.max(0, Math.ceil(Number(maxValue) || 0));
        const mid = max > 0 ? Math.round(max / 2) : 0;
        const ticks = [max, mid, 0];

        if (axis){
          for (const v of ticks){
            const s = document.createElement("span");
            s.textContent = String(v);
            axis.appendChild(s);
          }
        }
        if (grid){
          for (let i = 0; i < ticks.length; i++){
            grid.appendChild(document.createElement("span"));
          }
        }
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
          const from = new Date(to.getTime() - (24 * 3600 * 1000));
          return {from, to};
        }
        if (rangeKey === "1w"){
          const from = new Date(to.getTime() - (7 * 24 * 3600 * 1000));
          return {from, to};
        }
        if (rangeKey === "1m"){
          const from = new Date(to.getTime() - (30 * 24 * 3600 * 1000));
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
        const visibleRaw = $("visible_raw");
        if (visibleRaw) visibleRaw.textContent = data ? JSON.stringify(data, null, 2) : "";

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

      async function loadWorkspaceSwitches({fromTs, toTs, chunkSeconds, rangeKey}){
        if (!IS_STATS_PAGE) return;
        const chart = $("ws_chart");
        const labels = $("ws_labels");
        const status = $("ws_status");
        const info = $("ws_info");
        if (!chart || !labels) return;

        if (status) status.textContent = "fetching...";
        if (info) info.textContent = "";
        chart.textContent = "";
        labels.textContent = "";

        const url = new URL("/v1/events", window.location.origin);
        url.searchParams.set("bucket", "workspace_switch");
        if (toTs) url.searchParams.set("to", String(toTs));
        if (fromTs) url.searchParams.set("from", String(fromTs));

        const started = performance.now();
        let data;
        try{
          const res = await fetch(url.toString(), {cache:"no-store"});
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          data = await res.json();
        }catch(e){
          if (status) status.textContent = "error";
          if (info) info.textContent = `Failed to load workspace switches: ${e}`;
          renderCountAxis("ws_axis", "ws_grid", 0);
          return;
        }
        const ms = Math.round(performance.now() - started);
        if (status) status.textContent = `ok (${ms}ms)`;

        const fromMs = Date.parse(String(fromTs || (data && data.from_ts) || ""));
        const toMs = Date.parse(String(toTs || (data && data.to_ts) || ""));
        if (isNaN(fromMs) || isNaN(toMs) || toMs <= fromMs){
          if (info) info.textContent = "No range for workspace switches.";
          renderCountAxis("ws_axis", "ws_grid", 0);
          return;
        }

        const chunkMs = Math.max(1, (Number(chunkSeconds) || 0) * 1000);
        const totalMs = Math.max(0, toMs - fromMs);
        const bucketCount = Math.max(1, Math.ceil(totalMs / chunkMs));
        const counts = new Array(bucketCount).fill(0);

        const events = (data && Array.isArray(data.events)) ? data.events : [];
        for (const e of events){
          const ts = Date.parse(String((e && e.start_ts) || (e && e.end_ts) || ""));
          if (isNaN(ts)) continue;
          if (ts < fromMs || ts > toMs) continue;
          let idx = Math.floor((ts - fromMs) / chunkMs);
          if (idx >= bucketCount) idx = bucketCount - 1;
          if (idx < 0) continue;
          counts[idx] += 1;
        }

        const maxCount = counts.reduce((m, v) => Math.max(m, v), 0);
        renderCountAxis("ws_axis", "ws_grid", maxCount);

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

        const bucketSeconds = chunkMs / 1000.0;
        const totalSwitches = counts.reduce((a, b) => a + b, 0);
        if (info){
          if (rangeKey === "24h") info.textContent = `${totalSwitches} switches · per hour`;
          else if (rangeKey === "1w") info.textContent = `${totalSwitches} switches · per day`;
          else if (rangeKey === "1m") info.textContent = `${totalSwitches} switches · per day`;
          else info.textContent = `${totalSwitches} switches · per ${fmtChunk(bucketSeconds)}`;
        }

        for (let i = 0; i < counts.length; i++){
          const c = counts[i];
          const col = document.createElement("div");
          col.className = "barCol";

          const seg = document.createElement("div");
          seg.className = "barSeg switch";
          const pct = maxCount > 0 ? (c / maxCount) * 100.0 : 0.0;
          seg.style.height = `${Math.max(0, Math.min(100, pct))}%`;
          col.appendChild(seg);

          const start = new Date(fromMs + i * chunkMs);
          const end = new Date(Math.min(toMs, start.getTime() + chunkMs));
          col.title = `${fmtTsLocal(start.toISOString())} → ${fmtTsLocal(end.toISOString())}\\n${c} switches`;
          chart.appendChild(col);

          const s = document.createElement("span");
          s.textContent = showLabel(i, counts.length) ? labelText(start) : "";
          labels.appendChild(s);
        }
      }

      async function loadWorkspaceAppHeatmap({fromTs, toTs, rangeKey}){
        if (!IS_STATS_PAGE) return;
        const status = $("ws_app_status");
        const info = $("ws_app_info");
        const legend = $("ws_app_legend");
        const container = $("ws_app_heatmap");
        const rowsSelect = $("ws_app_rows");
        if (!container || !rowsSelect) return;

        const rowsLimit = parseInt(rowsSelect.value, 10) || 12;

        if (status) status.textContent = "fetching...";
        if (info) info.textContent = "";
        if (legend) legend.textContent = "";
        container.textContent = "";

        const url = new URL("/v1/events", window.location.origin);
        url.searchParams.set("bucket", "window_visible");
        if (toTs) url.searchParams.set("to", String(toTs));
        if (fromTs) url.searchParams.set("from", String(fromTs));

        const started = performance.now();
        let data;
        try{
          const res = await fetch(url.toString(), {cache:"no-store"});
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          data = await res.json();
        }catch(e){
          if (status) status.textContent = "error";
          if (info) info.textContent = `Failed to load window_visible events: ${e}`;
          return;
        }
        const ms = Math.round(performance.now() - started);
        if (status) status.textContent = `ok (${ms}ms)`;

        const events = (data && Array.isArray(data.events)) ? data.events : [];
        if (!events.length){
          if (info) info.textContent = "No window_visible events for this range (enable --track-visible-windows).";
          return;
        }

        const totalsByApp = {};
        const totalsByWs = {};
        const byAppWs = {};

        for (const e of events){
          const d = (e && e.data) ? e.data : {};
          const app = d && d.app ? String(d.app) : "";
          const ws = d && d.workspace ? String(d.workspace) : "";
          if (!app || app.startsWith("__")) continue;
          if (!ws) continue;
          const start = Date.parse(String(e.start_ts || ""));
          const end = Date.parse(String(e.end_ts || ""));
          if (isNaN(start) || isNaN(end) || end <= start) continue;
          const dur = (end - start) / 1000.0;

          totalsByApp[app] = (totalsByApp[app] || 0) + dur;
          totalsByWs[ws] = (totalsByWs[ws] || 0) + dur;
          if (!byAppWs[app]) byAppWs[app] = {};
          byAppWs[app][ws] = (byAppWs[app][ws] || 0) + dur;
        }

        const apps = Object.keys(totalsByApp);
        const workspaces = Object.keys(totalsByWs);
        if (!apps.length || !workspaces.length){
          if (info) info.textContent = "No workspace/app data for this range.";
          return;
        }

        const topApps = apps
          .sort((a, b) => totalsByApp[b] - totalsByApp[a])
          .slice(0, rowsLimit);
        const wsSorted = workspaces.sort((a, b) => totalsByWs[b] - totalsByWs[a]);

        container.style.setProperty("--ws-cols", String(wsSorted.length));

        const headerSpacer = document.createElement("div");
        headerSpacer.className = "wsColLabel";
        container.appendChild(headerSpacer);
        for (const ws of wsSorted){
          const el = document.createElement("div");
          el.className = "wsColLabel";
          el.textContent = ws;
          el.title = `workspace ${ws}`;
          container.appendChild(el);
        }

        let maxCell = 0;
        for (const app of topApps){
          const row = byAppWs[app] || {};
          for (const ws of wsSorted){
            const v = row[ws] || 0;
            if (v > maxCell) maxCell = v;
          }
        }

        const heatColor = (t) => {
          const clamped = Math.max(0, Math.min(1, Number(t) || 0));
          const hueStart = 170; // teal
          const hueEnd = 330; // pink
          const hue = hueStart + (hueEnd - hueStart) * clamped;
          const sat = 80;
          const light = 70 - 18 * clamped;
          return {
            bg: `hsl(${hue} ${sat}% ${light}%)`,
            border: `hsl(${hue} ${sat}% ${Math.max(18, light - 10)}%)`,
          };
        };

        for (const app of topApps){
          const appCell = document.createElement("div");
          appCell.className = "wsApp";
          appCell.textContent = app;
          appCell.title = `${app} total ${fmtSeconds(totalsByApp[app] || 0)}`;
          container.appendChild(appCell);

          const row = byAppWs[app] || {};
          for (const ws of wsSorted){
            const v = row[ws] || 0;
            const cell = document.createElement("div");
            cell.className = "wsCell";
            const intensity = maxCell > 0 ? Math.min(1, v / maxCell) : 0;
            if (v > 0){
              const color = heatColor(intensity);
              cell.style.background = color.bg;
              cell.style.borderColor = color.border;
            }
            cell.title = `${app} @ ${ws}: ${fmtSeconds(v)}`;
            container.appendChild(cell);
          }
        }

        const totalApps = apps.length;
        if (info){
          const rangeLabel = rangeKey ? ` · ${rangeKey}` : "";
          info.textContent = `Top ${topApps.length}/${totalApps} apps · visible time (window_visible)${rangeLabel}`;
        }
        if (legend){
          const left = document.createElement("span");
          left.textContent = "low";
          const bar = document.createElement("div");
          bar.className = "wsLegendBar";
          const stops = [0, 0.25, 0.5, 0.75, 1].map((t) => {
            const c = heatColor(t).bg;
            return `${c} ${Math.round(t * 100)}%`;
          });
          bar.style.background = `linear-gradient(90deg, ${stops.join(", ")})`;
          const right = document.createElement("span");
          right.textContent = maxCell > 0 ? `high (${fmtSeconds(maxCell)})` : "high";
          legend.appendChild(left);
          legend.appendChild(bar);
          legend.appendChild(right);
        }
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

        const raw = $("raw");
        if (raw) raw.textContent = JSON.stringify(data, null, 2);
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
        lastSummary = data;
        window.__aw_apps_ctx = {fromTs: data.from_ts, toTs: data.to_ts, rangeKey};
        await refreshTopApps();

        function renderTimelineAxis(chunkSec){
          const axis = $("timeline_axis");
          const grid = $("timeline_grid");
          if (axis) axis.textContent = "";
          if (grid) grid.textContent = "";
          if (!axis && !grid) return;

          const maxHours = Math.max(0, (Number(chunkSec) || 0) / 3600.0);
          const midHours = maxHours / 2;
          const ticks = [maxHours, midHours, 0];

          if (axis){
            for (const h of ticks){
              const s = document.createElement("span");
              s.textContent = fmtHours(h);
              axis.appendChild(s);
            }
          }
          if (grid){
            for (let i = 0; i < ticks.length; i++){
              grid.appendChild(document.createElement("span"));
            }
          }
        }

        // Timeline buckets (hourly for 24h, daily for 1w/1m)
        renderTimelineAxis(chunkSeconds);
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
          const fPctC = Math.max(0, Math.min(aPctC, fPct));

          const col = document.createElement("div");
          col.className = "barCol";

          const segA = document.createElement("div");
          segA.className = "barSeg active";
          segA.style.height = `${aPctC}%`;

          const segF = document.createElement("div");
          segF.className = "barSeg afkOverlay";
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

        if (IS_STATS_PAGE){
          const wsCtx = {fromTs, toTs, chunkSeconds, rangeKey};
          window.__aw_ws_ctx = wsCtx;
          window.__aw_sites_ctx = {fromTs: data.from_ts, toTs: data.to_ts, rangeKey};
          loadWorkspaceSwitches(wsCtx);
          loadWorkspaceAppHeatmap(wsCtx);
          loadSites(window.__aw_sites_ctx);
          loadTabsChart({fromTs: data.from_ts, toTs: data.to_ts, rangeKey});
          if ((parseInt($("visible_autoload").value, 10) || 0) === 1){
            loadVisibleLogs();
          }
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
      const appsMode = $("apps_mode");
      if (appsMode){
        appsMode.addEventListener("change", () => {
          setAppsMode(appsMode.value);
          refreshTopApps();
        });
      }
      const sitesMode = $("sites_mode");
      if (sitesMode){
        sitesMode.addEventListener("change", () => {
          setSitesMode(sitesMode.value);
          if (window.__aw_sites_ctx){
            loadSites(window.__aw_sites_ctx);
          }
        });
      }
      const sitesFilter = $("sites_filter");
      if (sitesFilter){
        sitesFilter.addEventListener("input", () => {
          if (lastSites && window.__aw_sites_ctx){
            renderSitesFromEvents(lastSites.events, window.__aw_sites_ctx.rangeKey || "24h");
          }
        });
      }
      const sitesRows = $("sites_rows");
      if (sitesRows){
        sitesRows.addEventListener("change", () => {
          if (lastSites && window.__aw_sites_ctx){
            renderSitesFromEvents(lastSites.events, window.__aw_sites_ctx.rangeKey || "24h");
          }
        });
      }
      const sitesGroup = $("sites_group_filter");
      if (sitesGroup){
        sitesGroup.addEventListener("change", () => {
          if (lastSites && window.__aw_sites_ctx){
            renderSitesFromEvents(lastSites.events, window.__aw_sites_ctx.rangeKey || "24h");
          }
        });
      }
      const sitesGroupDomain = $("sites_group_domain");
      if (sitesGroupDomain){
        sitesGroupDomain.addEventListener("change", () => {
          if (lastSites && window.__aw_sites_ctx){
            renderSitesFromEvents(lastSites.events, window.__aw_sites_ctx.rangeKey || "24h");
          }
        });
      }
      const sitesMetric = $("sites_chart_metric");
      if (sitesMetric){
        sitesMetric.addEventListener("change", () => {
          if (window.__aw_sites_ctx){
            renderSitesChart(window.__aw_sites_ctx.rangeKey || "24h");
          }
        });
      }
      const sitesClear = $("sites_clear");
      if (sitesClear){
        sitesClear.addEventListener("click", () => {
          selectedSites.clear();
          if (lastSites && window.__aw_sites_ctx){
            renderSitesFromEvents(lastSites.events, window.__aw_sites_ctx.rangeKey || "24h");
          }else{
            renderSitesChart("24h");
          }
        });
      }
      const tabsDomainTop = $("tabs_domain_top");
      if (tabsDomainTop){
        tabsDomainTop.addEventListener("change", () => {
          if (lastTabs){
            renderTabsDomains(lastTabs);
          }
        });
      }
      const tabsListForm = $("tabs_list_form");
      if (tabsListForm){
        tabsListForm.addEventListener("submit", (e) => e.preventDefault());
      }
      const tabsListFilter = $("tabs_list_filter");
      if (tabsListFilter){
        tabsListFilter.addEventListener("input", () => {
          if (lastTabs){
            renderTabsList(lastTabs);
          }
        });
      }
      const tabsListRows = $("tabs_list_rows");
      if (tabsListRows){
        tabsListRows.addEventListener("change", () => {
          if (lastTabs){
            renderTabsList(lastTabs);
          }
        });
      }
      const wsRows = $("ws_app_rows");
      if (wsRows){
        wsRows.addEventListener("change", () => {
          if (window.__aw_ws_ctx){
            loadWorkspaceAppHeatmap(window.__aw_ws_ctx);
          }
        });
      }

      $("cal_form").addEventListener("submit", (e) => { e.preventDefault(); saveCalendarPrefs(); loadCalendar(); });
      $("cal_mode").addEventListener("change", () => { saveCalendarPrefs(); loadCalendar(); });
      $("cal_apps").addEventListener("change", () => saveCalendarPrefs());

      loadCalendarPrefs();
      try{
        const savedAppsMode = localStorage.getItem("aw_apps_mode");
        if (savedAppsMode) setAppsMode(savedAppsMode);
      }catch(e){}
      try{
        const savedSitesMode = localStorage.getItem("aw_sites_mode");
        if (savedSitesMode) setSitesMode(savedSitesMode);
      }catch(e){}
      initFromQuery();
      load();
      loadCalendar();
      loadCalendarAppOptions();
      startAutoRefresh();
    </script>
  </body>
</html>
"""
