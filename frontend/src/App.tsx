import { Fragment, type MouseEvent, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

type RangeKey = "24h" | "1w" | "1m" | "all";
type TopicId = "all" | "overview" | "apps" | "categories" | "websites" | "workspaces" | "monitors" | "tabs" | "logs";
type MonitorSetupFilter = "all" | "single" | "multi";

type SummaryApp = {
  app: string;
  seconds: number;
  percent_active?: number;
  percent_window?: number;
};

type TimelineChunk = {
  start_ts: string;
  end_ts: string;
  active_seconds: number;
  afk_seconds: number;
  unknown_seconds: number;
  top_app?: string | null;
};

type SummaryResponse = {
  from_ts: string;
  to_ts: string;
  total_seconds: number;
  active_seconds: number;
  afk_seconds: number;
  unknown_seconds: number;
  top_apps_mode: "active" | "window";
  top_apps: SummaryApp[];
  timeline_chunks: TimelineChunk[];
};

type CategoryRow = {
  category: string;
  label: string;
  color: string;
  seconds: number;
  percent: number;
};

type CategoryDetailRow = {
  name: string;
  seconds: number;
};

type CategoryAppDetail = {
  top_apps?: CategoryDetailRow[];
  top_titles?: CategoryDetailRow[];
};

type CategoryTabDetail = {
  top_domains?: CategoryDetailRow[];
  top_titles?: CategoryDetailRow[];
  top_browsers?: CategoryDetailRow[];
};

type CategoriesResponse = {
  from_ts: string;
  to_ts: string;
  mode: string;
  apps_total_seconds: number;
  tabs_total_seconds: number;
  apps: CategoryRow[];
  tabs: CategoryRow[];
  app_details?: Record<string, CategoryAppDetail>;
  tab_details?: Record<string, CategoryTabDetail>;
};

type ApiEvent = {
  id?: number;
  source?: string;
  start_ts: string;
  end_ts: string;
  data: Record<string, unknown>;
};

type EventsResponse = {
  events: ApiEvent[];
};

type TimeWindow = { from: string; to: string };

type SliceRow = {
  id: string;
  label: string;
  seconds: number;
  color?: string;
  percent?: number;
  details?: SliceDetailsSection[];
};

type SliceDetailsItem = {
  label: string;
  value?: string;
};

type SliceDetailsSection = {
  title: string;
  items: SliceDetailsItem[];
  emptyText?: string;
};

type BarRow = {
  id: string;
  label: string;
  value: number;
  sub?: string;
  color?: string;
};

type LinePoint = {
  t: number;
  value: number;
};

type SiteRow = {
  site: string;
  seconds: number;
  visits: number;
  lastTs: string;
};

type VisibleRow = {
  start: string;
  end: string;
  app: string;
  title: string;
  workspace: string;
  monitor: string;
};

type WorkspaceHeatmapRow = {
  id: string;
  label: string;
  total: number;
  cells: number[];
};

type HoverTooltip = {
  x: number;
  y: number;
  label: string;
  meta?: string;
  color?: string;
};

type WorkspaceTransitionMatrix = {
  workspaces: string[];
  counts: number[][];
  outTotals: number[];
  inTotals: number[];
  maxCell: number;
  total: number;
};

type MonitorEnabledPeriodRow = {
  monitor: string;
  start: string;
  end: string;
  durationSeconds: number;
  setup: "single" | "multi" | "unknown";
  maxMonitorCount: number;
  signature: string;
};

const RANGES: Array<{ key: RangeKey; label: string }> = [
  { key: "24h", label: "24h" },
  { key: "1w", label: "1w" },
  { key: "1m", label: "1m" },
  { key: "all", label: "all" }
];

const TOPICS: Array<{ id: TopicId; label: string }> = [
  { id: "all", label: "all" },
  { id: "overview", label: "overview" },
  { id: "apps", label: "apps" },
  { id: "categories", label: "categories" },
  { id: "websites", label: "websites" },
  { id: "workspaces", label: "workspaces" },
  { id: "monitors", label: "monitors" },
  { id: "tabs", label: "tabs" },
  { id: "logs", label: "logs" }
];

const MONITOR_SETUP_FILTERS: Array<{ key: MonitorSetupFilter; label: string }> = [
  { key: "all", label: "all monitors" },
  { key: "single", label: "single monitor" },
  { key: "multi", label: "multi monitor" }
];

function parseRangeKey(v: string | null | undefined): RangeKey {
  const s = String(v || "");
  if (s === "24h" || s === "1w" || s === "1m" || s === "all") return s;
  return "24h";
}

function parseTopicId(v: string | null | undefined): TopicId {
  const s = String(v || "");
  if (
    s === "all" ||
    s === "overview" ||
    s === "apps" ||
    s === "categories" ||
    s === "websites" ||
    s === "workspaces" ||
    s === "monitors" ||
    s === "tabs" ||
    s === "logs"
  ) {
    return s;
  }
  return "all";
}

function pathPrefixBeforeUi(pathname: string): string {
  const p = String(pathname || "");
  const idx = p.indexOf("/ui");
  if (idx <= 0) return "";
  return p.slice(0, idx);
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
  "thorium"
];

const MULTI_TLD = new Set([
  "co.uk",
  "org.uk",
  "ac.uk",
  "gov.uk",
  "com.au",
  "net.au",
  "org.au",
  "co.nz",
  "com.br",
  "com.mx",
  "com.ar",
  "com.tr",
  "com.pl",
  "com.ru",
  "com.cn",
  "com.tw",
  "com.hk",
  "com.sg",
  "com.my",
  "com.ph",
  "com.sa",
  "com.ng",
  "co.in",
  "co.jp",
  "co.kr",
  "co.id",
  "co.il"
]);

function fmtSeconds(sec: number): string {
  const s = Math.max(0, Math.round(sec || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  if (h > 0) return `${h}h ${m}m ${ss}s`;
  if (m > 0) return `${m}m ${ss}s`;
  return `${ss}s`;
}

function fmtSecondsShort(sec: number): string {
  const s = Math.max(0, Math.round(sec || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m`;
  return `${s}s`;
}

function fmtPct(v: number): string {
  return `${Math.round((Number(v) || 0) * 10) / 10}%`;
}

function fmtHours(hours: number): string {
  const v = Math.round((Number(hours) || 0) * 10) / 10;
  return `${v}h`;
}

function fmtTs(ts: string): string {
  if (!ts) return "";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString();
}

function trimLabel(text: string, max = 72): string {
  const s = String(text || "").trim();
  if (s.length <= max) return s;
  return `${s.slice(0, Math.max(0, max - 1))}…`;
}

function buildTopDetailItems(map: Map<string, number>, limit = 8): SliceDetailsItem[] {
  return Array.from(map.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([label, seconds]) => ({
      label: trimLabel(label, 84),
      value: fmtSeconds(seconds)
    }));
}

function asString(v: unknown): string {
  if (typeof v === "string") return v;
  if (typeof v === "number") return String(v);
  return "";
}

function asNumber(v: unknown): number {
  if (typeof v === "number") return v;
  if (typeof v === "string") {
    const n = Number(v);
    return Number.isFinite(n) ? n : 0;
  }
  return 0;
}

function normalizeMonitorName(v: unknown): string {
  const s = String(v || "").trim();
  if (!s || s === "null" || s === "undefined") return "";
  return s;
}

function uniqueMonitorNames(values: string[]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const raw of values) {
    const name = normalizeMonitorName(raw);
    if (!name) continue;
    const key = name.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(name);
  }
  return out;
}

function monitorNamesFromUnknown(v: unknown): string[] {
  if (Array.isArray(v)) {
    const values = v.map((it) => normalizeMonitorName(it)).filter(Boolean);
    return uniqueMonitorNames(values);
  }
  const raw = normalizeMonitorName(v);
  if (!raw) return [];
  const parts = raw.includes("|") ? raw.split("|") : raw.includes(",") ? raw.split(",") : raw.includes(";") ? raw.split(";") : [raw];
  return uniqueMonitorNames(parts);
}

function connectedMonitorsFromData(data: Record<string, unknown> | undefined): string[] {
  if (!data || typeof data !== "object") return [];
  const listCandidates = [data.connected_monitors, data.connectedMonitors];
  for (const candidate of listCandidates) {
    const names = monitorNamesFromUnknown(candidate);
    if (names.length) return names;
  }

  const signatureCandidates = [data.monitor_signature, data.monitorSignature];
  for (const candidate of signatureCandidates) {
    const names = monitorNamesFromUnknown(candidate);
    if (names.length) return names;
  }

  return uniqueMonitorNames([asString(data.monitor), asString(data.focused_monitor)]);
}

function monitorCountFromData(data: Record<string, unknown> | undefined): number | null {
  if (!data || typeof data !== "object") return null;
  const candidates = [data.monitor_count, data.monitorCount, data.monitors_count, data.monitorsCount];
  for (const c of candidates) {
    const n = asNumber(c);
    if (Number.isFinite(n) && n > 0) return Math.round(n);
  }
  const names = connectedMonitorsFromData(data);
  if (names.length) return names.length;
  return null;
}

function monitorSetupFromData(data: Record<string, unknown> | undefined): Exclude<MonitorSetupFilter, "all"> | null {
  if (!data || typeof data !== "object") return null;
  const setupCandidates = [data.monitor_setup, data.monitorSetup, data.to_monitor_setup, data.from_monitor_setup];
  for (const raw of setupCandidates) {
    const s = String(raw || "").trim().toLowerCase();
    if (s === "single" || s === "multi") return s;
  }

  const count = monitorCountFromData(data);
  if (count != null) return count >= 2 ? "multi" : "single";

  const connected = connectedMonitorsFromData(data);
  if (connected.length >= 2) return "multi";
  if (connected.length === 1) return "single";

  return null;
}

function matchesMonitorSetupFilter(event: ApiEvent, filter: MonitorSetupFilter): boolean {
  if (filter === "all") return true;
  const data = (event?.data && typeof event.data === "object" ? event.data : undefined) as Record<string, unknown> | undefined;
  const setup = monitorSetupFromData(data);
  if (!setup) return false;
  return setup === filter;
}

function parseUrlSafe(raw: string): URL | null {
  const s = String(raw || "").trim();
  if (!s) return null;
  try {
    return new URL(s);
  } catch {
    try {
      return new URL(`http://${s}`);
    } catch {
      return null;
    }
  }
}

function normalizeHost(host: string): string {
  return String(host || "")
    .toLowerCase()
    .replace(/^www\./, "")
    .replace(/[\])},.]+$/, "");
}

function baseDomainFromHost(host: string): string {
  const h = normalizeHost(host);
  if (!h || !h.includes(".")) return h;
  const parts = h.split(".").filter(Boolean);
  if (parts.length <= 2) return h;
  const tld2 = parts.slice(-2).join(".");
  if (MULTI_TLD.has(tld2) && parts.length >= 3) {
    return parts.slice(-3).join(".");
  }
  return parts.slice(-2).join(".");
}

function isBrowserApp(app: string): boolean {
  const a = String(app || "").toLowerCase();
  if (!a) return false;
  return BROWSER_HINTS.some((k) => a.includes(k));
}

function stripBrowserSuffix(title: string): string {
  const t = String(title || "").trim();
  if (!t) return "";
  return t
    .replace(
      /\s+[\-–—]\s*(Mozilla Firefox|Firefox|Brave|Google Chrome|Chromium|Vivaldi|Opera|Microsoft Edge|Edge|Thorium|LibreWolf|Floorp|Zen)\s*$/i,
      ""
    )
    .trim();
}

function extractHostFromTitle(title: string): string | null {
  const t = String(title || "");
  if (!t) return null;

  const urlMatch = t.match(/https?:\/\/[^\s]+/i);
  if (urlMatch) {
    try {
      const u = new URL(urlMatch[0]);
      return u.hostname;
    } catch {
      // ignore
    }
  }

  const wwwMatch = t.match(/\bwww\.[^\s/]+\.[^\s)\],.]+/i);
  if (wwwMatch) {
    try {
      const u = new URL(`http://${wwwMatch[0]}`);
      return u.hostname;
    } catch {
      // ignore
    }
  }

  const hostMatch = t.match(/\b([a-z0-9.-]+\.[a-z]{2,})(?:\b|\/)/i);
  if (hostMatch) return hostMatch[1];
  return null;
}

function extractSite(app: string, title: string): string | null {
  const host = extractHostFromTitle(title);
  if (host) {
    const h = normalizeHost(host);
    return h || null;
  }
  if (isBrowserApp(app)) {
    const stripped = stripBrowserSuffix(title);
    return stripped || null;
  }
  return null;
}

function tabDomainFromTab(tab: Record<string, unknown>): string {
  const url = asString(tab.url) || asString(tab.pending_url) || asString(tab.pendingUrl);
  if (url) {
    const parsed = parseUrlSafe(url);
    if (parsed) {
      const host = normalizeHost(parsed.hostname);
      const proto = String(parsed.protocol || "").replace(":", "");
      if (host) {
        if (proto && proto !== "http" && proto !== "https" && !host.includes(".")) {
          return proto;
        }
        return baseDomainFromHost(host);
      }
      if (proto && proto !== "http" && proto !== "https") return proto;
    }
  }

  const title = asString(tab.title);
  if (title) {
    const host = extractHostFromTitle(title);
    if (host) return baseDomainFromHost(host);
  }
  return "internal";
}

function qs(window: TimeWindow): string {
  const p = new URLSearchParams();
  p.set("from", window.from);
  p.set("to", window.to);
  return p.toString();
}

function nowIso(): string {
  return new Date().toISOString();
}

function addMs(iso: string, deltaMs: number): string {
  const d = new Date(iso);
  return new Date(d.getTime() + deltaMs).toISOString();
}

async function resolveWindow(range: RangeKey): Promise<TimeWindow> {
  const to = nowIso();
  if (range === "24h") return { from: addMs(to, -24 * 3600 * 1000), to };
  if (range === "1w") return { from: addMs(to, -7 * 24 * 3600 * 1000), to };
  if (range === "1m") return { from: addMs(to, -30 * 24 * 3600 * 1000), to };

  const res = await fetch("/v1/range?bucket=window", { cache: "no-store" });
  if (!res.ok) return { from: addMs(to, -24 * 3600 * 1000), to };
  const data = (await res.json()) as { empty?: boolean; from_ts?: string };
  const from = data.empty || !data.from_ts ? addMs(to, -24 * 3600 * 1000) : data.from_ts;
  return { from, to };
}

function chunkSecondsForRange(range: RangeKey, durationSeconds: number): number {
  if (range === "24h") return 3600;
  if (range === "1w") return 86400;
  if (range === "1m") return 86400;
  if (!Number.isFinite(durationSeconds) || durationSeconds <= 0) return 3600;

  const targetBars = 180;
  const candidate = Math.max(60, Math.round(durationSeconds / targetBars));
  const choices = [
    300, 600, 900, 1800, 3600, 7200, 10800, 21600, 43200, 86400, 172800, 604800
  ];
  for (const c of choices) {
    if (candidate <= c) return c;
  }
  return choices[choices.length - 1];
}

function workspaceBinLabel(range: RangeKey, startMs: number, stepMs: number): string {
  const d = new Date(startMs);
  if (Number.isNaN(d.getTime())) return "";
  if (range === "24h") return `${String(d.getHours()).padStart(2, "0")}:00`;
  if (range === "1w" || range === "1m") {
    return d.toLocaleDateString(undefined, { month: "2-digit", day: "2-digit" });
  }
  if (stepMs >= 86400_000) {
    return d.toLocaleDateString(undefined, { month: "2-digit", day: "2-digit" });
  }
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function workspaceBinSizeLabel(stepMs: number): string {
  if (stepMs >= 86400_000) return `${Math.max(1, Math.round(stepMs / 86400_000))}d`;
  if (stepMs >= 3600_000) return `${Math.max(1, Math.round(stepMs / 3600_000))}h`;
  if (stepMs >= 60_000) return `${Math.max(1, Math.round(stepMs / 60_000))}m`;
  return `${Math.max(1, Math.round(stepMs / 1000))}s`;
}

function workspaceHeatColor(ratio: number): string {
  const t = Math.max(0, Math.min(1, ratio));
  const stops = [
    [250, 204, 21], // yellow
    [245, 158, 11], // amber
    [220, 38, 38], // red
    [127, 29, 29] // dark red
  ] as const;
  const scaled = t * (stops.length - 1);
  const idx = Math.min(stops.length - 2, Math.floor(scaled));
  const localT = Math.max(0, Math.min(1, scaled - idx));
  const from = stops[idx];
  const to = stops[idx + 1];
  const r = Math.round(from[0] + (to[0] - from[0]) * localT);
  const g = Math.round(from[1] + (to[1] - from[1]) * localT);
  const b = Math.round(from[2] + (to[2] - from[2]) * localT);
  const a = t > 0 ? 0.2 + t * 0.75 : 0.06;
  return `rgba(${r}, ${g}, ${b}, ${a.toFixed(3)})`;
}

function stableHash(text: string): number {
  const s = String(text || "");
  let h = 2166136261;
  for (let i = 0; i < s.length; i += 1) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function workspaceTransitionColors(workspace: string): { bg: string; border: string; text: string } {
  const hue = stableHash(String(workspace || "?")) % 360;
  return {
    bg: `hsla(${hue}, 85%, 55%, 0.16)`,
    border: `hsla(${hue}, 90%, 72%, 0.44)`,
    text: `hsl(${hue}, 92%, 85%)`
  };
}

function workspaceLabel(workspace: string): string {
  const v = String(workspace || "?").trim() || "?";
  return /^ws\s+/i.test(v) ? v : `WS ${v}`;
}

function workspaceOrderValue(workspace: string): number | null {
  const s = String(workspace || "").trim();
  if (!s) return null;
  const direct = Number(s);
  if (Number.isFinite(direct)) return direct;
  const wsMatch = s.match(/^ws\s*([+-]?\d+)(?:\b|$)/i);
  if (wsMatch) {
    const n = Number(wsMatch[1]);
    if (Number.isFinite(n)) return n;
  }
  const anyNum = s.match(/[+-]?\d+/);
  if (anyNum) {
    const n = Number(anyNum[0]);
    if (Number.isFinite(n)) return n;
  }
  return null;
}

function compareWorkspaceIds(a: string, b: string): number {
  const an = workspaceOrderValue(a);
  const bn = workspaceOrderValue(b);
  if (an != null && bn != null) return an - bn;
  if (an != null && bn == null) return -1;
  if (an == null && bn != null) return 1;
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });
}

function monitorSetupLabel(setup: "single" | "multi" | "unknown"): string {
  if (setup === "single") return "single monitor";
  if (setup === "multi") return "multi monitor";
  return "unknown setup";
}

function monitorSetupBarColor(setup: "single" | "multi" | "unknown"): string {
  if (setup === "single") return "linear-gradient(90deg, rgba(45,212,191,.84), rgba(94,201,255,.96))";
  if (setup === "multi") return "linear-gradient(90deg, rgba(250,204,21,.86), rgba(185,28,28,.93))";
  return "linear-gradient(90deg, rgba(148,163,184,.62), rgba(100,116,139,.8))";
}

function tooltipPoint(e: MouseEvent<Element>): { x: number; y: number } {
  const offsetX = 14;
  const x = e.clientX + offsetX;
  const y = e.clientY;
  if (typeof window === "undefined") return { x, y };
  return {
    x: Math.max(10, Math.min(window.innerWidth - 10, x)),
    y: Math.max(16, Math.min(window.innerHeight - 10, y))
  };
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`${url} -> HTTP ${res.status}`);
  return (await res.json()) as T;
}

function TooltipPortal({ tooltip }: { tooltip: HoverTooltip | null }) {
  if (!tooltip || typeof document === "undefined") return null;
  return createPortal(
    <div className="uiTooltip" style={{ left: tooltip.x, top: tooltip.y }}>
      <div className="uiTooltipLabel">
        {tooltip.color ? <span className="dot" style={{ background: tooltip.color }} /> : null}
        {tooltip.label}
      </div>
      {tooltip.meta ? <div className="uiTooltipMeta">{tooltip.meta}</div> : null}
    </div>,
    document.body
  );
}

function DonutChart({ rows, total, title }: { rows: SliceRow[]; total: number; title: string }) {
  const [hovered, setHovered] = useState<{
    id: string;
    label: string;
    seconds: number;
    pct: number;
    color: string;
    x: number;
    y: number;
  } | null>(null);
  const [selected, setSelected] = useState<{
    id: string;
    label: string;
    seconds: number;
    pct: number;
    color: string;
    rank: number;
    details?: SliceDetailsSection[];
  } | null>(null);

  let offset = 25;
  const slices = rows
    .filter((r) => (r.seconds || 0) > 0)
    .sort((a, b) => b.seconds - a.seconds)
    .map((r) => {
      const pct = total > 0 ? (r.seconds / total) * 100 : 0;
      const start = offset;
      offset -= pct;
      return { ...r, pct, start };
    });

  useEffect(() => {
    if (!selected) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSelected(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selected]);

  useEffect(() => {
    if (!selected || typeof document === "undefined") return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [selected]);

  const updateHover = (
    e: MouseEvent<SVGCircleElement>,
    s: { id: string; label: string; seconds: number; pct: number; color?: string }
  ) => {
    const p = tooltipPoint(e);
    setHovered({
      id: s.id,
      label: s.label,
      seconds: s.seconds,
      pct: s.pct,
      color: s.color || "#7dd3fc",
      x: p.x,
      y: p.y
    });
  };

  return (
    <div className="donutWrap">
      <svg className="donut" viewBox="0 0 42 42" role="img" aria-label={title}>
        <circle cx="21" cy="21" r="15.915" fill="transparent" strokeWidth="4" className="donutRing" />
        {slices.map((s, idx) => {
          const isActive = hovered?.id === s.id;
          const detail = {
            id: s.id,
            label: s.label,
            seconds: s.seconds,
            pct: s.pct,
            color: s.color || "#7dd3fc",
            rank: idx + 1,
            details: s.details
          };
          return (
            <circle
              key={s.id}
              cx="21"
              cy="21"
              r={isActive ? "16.4" : "15.915"}
              fill="transparent"
              strokeWidth={isActive ? "5.4" : "4"}
              stroke={s.color || "#7dd3fc"}
              strokeDasharray={`${s.pct} ${Math.max(0, 100 - s.pct)}`}
              strokeDashoffset={String(s.start)}
              className="donutSlice"
              onMouseEnter={(e) => updateHover(e, s)}
              onMouseMove={(e) => updateHover(e, s)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => setSelected(detail)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  setSelected(detail);
                }
              }}
              tabIndex={0}
              role="button"
              aria-label={`Show details for ${s.label}`}
              style={isActive ? { filter: "drop-shadow(0 0 4px rgba(180,235,255,.55))" } : undefined}
            />
          );
        })}
        <text x="21" y="21" textAnchor="middle" dominantBaseline="middle" className="donutText">
          {total > 0 ? fmtSecondsShort(total) : "-"}
        </text>
      </svg>
      <div className="legend">
        {slices.slice(0, 10).map((s, idx) => (
          <button
            type="button"
            className={`legendRow legendButton ${hovered?.id === s.id ? "active" : ""}`}
            key={s.id}
            onClick={() =>
              setSelected({
                id: s.id,
                label: s.label,
                seconds: s.seconds,
                pct: s.pct,
                color: s.color || "#7dd3fc",
                rank: idx + 1,
                details: s.details
              })
            }
          >
            <span className="dot" style={{ background: s.color || "#7dd3fc" }} />
            <span className="label">{s.label}</span>
            <span className="value">{fmtPct(s.pct)}</span>
          </button>
        ))}
      </div>
      <TooltipPortal
        tooltip={
          hovered
            ? {
                x: hovered.x,
                y: hovered.y,
                label: hovered.label,
                meta: `${fmtSeconds(hovered.seconds)} · ${fmtPct(hovered.pct)}`,
                color: hovered.color
              }
            : null
        }
      />
      {selected && typeof document !== "undefined"
        ? createPortal(
            <div className="chartModalBackdrop" onClick={() => setSelected(null)}>
              <div className="chartModal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
                <div className="chartModalHd">
                  <h3>{title}</h3>
                  <button type="button" className="pill" onClick={() => setSelected(null)}>
                    close
                  </button>
                </div>
                <div className="chartModalBd">
                  <div className="chartModalTitle">
                    <span className="dot" style={{ background: selected.color }} />
                    <strong>{selected.label}</strong>
                  </div>
                  <div className="chartMetricGrid">
                    <div className="chartMetric">
                      <span>Time</span>
                      <strong>{fmtSeconds(selected.seconds)}</strong>
                    </div>
                    <div className="chartMetric">
                      <span>Share</span>
                      <strong>{fmtPct(selected.pct)}</strong>
                    </div>
                    <div className="chartMetric">
                      <span>Rank</span>
                      <strong>
                        #{selected.rank} / {slices.length}
                      </strong>
                    </div>
                    <div className="chartMetric">
                      <span>Remaining</span>
                      <strong>{fmtSeconds(Math.max(0, total - selected.seconds))}</strong>
                    </div>
                  </div>
                  <div className="chartProgress">
                    <div className="chartProgressFill" style={{ width: `${Math.max(0, Math.min(100, selected.pct))}%`, background: selected.color }} />
                  </div>
                  <div className="sub">chart total: {fmtSeconds(total)}</div>
                  {selected.details && selected.details.length > 0 ? (
                    <div className="chartDetails">
                      {selected.details.map((section) => (
                        <div className="chartDetailSection" key={section.title}>
                          <div className="chartDetailTitle">{section.title}</div>
                          {section.items.length > 0 ? (
                            <div className="chartDetailList">
                              {section.items.map((it, idx) => (
                                <div className="chartDetailRow" key={`${section.title}-${it.label}-${idx}`}>
                                  <span className="chartDetailLabel">{it.label}</span>
                                  <span className="chartDetailValue">{it.value || ""}</span>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="chartDetailEmpty">{section.emptyText || "No details available."}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            </div>,
            document.body
          )
        : null}
    </div>
  );
}

function HorizontalBars({ rows, valueFormatter }: { rows: BarRow[]; valueFormatter: (n: number) => string }) {
  const [hovered, setHovered] = useState<HoverTooltip | null>(null);
  const items = rows.filter((r) => r.value > 0);
  const maxVal = items.reduce((m, r) => Math.max(m, r.value), 0);

  const updateHover = (e: MouseEvent<HTMLDivElement>, row: BarRow) => {
    const p = tooltipPoint(e);
    setHovered({
      x: p.x,
      y: p.y,
      label: row.label,
      meta: `${valueFormatter(row.value)}${row.sub ? ` · ${row.sub}` : ""}`
    });
  };

  if (!items.length) {
    return <div className="empty">No data.</div>;
  }

  return (
    <div className="barList">
      {items.map((r) => {
        const w = maxVal > 0 ? (r.value / maxVal) * 100 : 0;
        return (
          <div key={r.id} className="barRow">
            <div
              className="barLabel"
              onMouseEnter={(e) => updateHover(e, r)}
              onMouseMove={(e) => updateHover(e, r)}
              onMouseLeave={() => setHovered(null)}
            >
              {r.label}
              {r.sub ? <span className="barSub">{r.sub}</span> : null}
            </div>
            <div className="barTrack">
              <div className="barFill" style={{ width: `${w}%`, background: r.color || undefined }} />
            </div>
            <div className="barValue">{valueFormatter(r.value)}</div>
          </div>
        );
      })}
      <TooltipPortal tooltip={hovered} />
    </div>
  );
}

function MiniLineChart({ points }: { points: LinePoint[] }) {
  const width = 700;
  const height = 200;
  const padX = 20;
  const padY = 18;

  if (points.length < 2) {
    return <div className="empty">No line data.</div>;
  }

  const sorted = [...points].sort((a, b) => a.t - b.t);
  const rawMinX = sorted[0].t;
  const rawMaxX = sorted[sorted.length - 1].t;
  if (!Number.isFinite(rawMinX) || !Number.isFinite(rawMaxX) || rawMaxX <= rawMinX) {
    return <div className="empty">No line data.</div>;
  }

  const valueChanges = sorted.filter((p, i) => i === 0 || p.value !== sorted[i - 1].value);
  const sparseSeries = valueChanges.length <= Math.max(4, Math.round(sorted.length * 0.2));

  let minX = rawMinX;
  let maxX = rawMaxX;
  if (sparseSeries) {
    const focus = sorted.filter((p) => p.value > 0);
    const focusPoints = focus.length ? focus : valueChanges;
    const focusMin = Math.min(...focusPoints.map((p) => p.t));
    const focusMax = Math.max(...focusPoints.map((p) => p.t));
    const fullRange = rawMaxX - rawMinX;
    const focusRange = Math.max(1, focusMax - focusMin);
    const pad = Math.max(focusRange * 0.35, fullRange * 0.06, 5 * 60_000);
    minX = Math.max(rawMinX, focusMin - pad);
    maxX = Math.min(rawMaxX, focusMax + pad);
    if (maxX - minX < Math.max(30 * 60_000, fullRange * 0.16)) {
      const minRange = Math.max(30 * 60_000, fullRange * 0.16);
      const mid = (minX + maxX) / 2;
      minX = Math.max(rawMinX, mid - minRange / 2);
      maxX = Math.min(rawMaxX, mid + minRange / 2);
    }
  }
  if (maxX <= minX) {
    minX = rawMinX;
    maxX = rawMaxX;
  }

  const valueAt = (ts: number): number => {
    if (ts <= sorted[0].t) return sorted[0].value;
    for (let i = 1; i < sorted.length; i += 1) {
      const a = sorted[i - 1];
      const b = sorted[i];
      if (ts <= b.t) {
        if (b.t === a.t) return b.value;
        const r = (ts - a.t) / (b.t - a.t);
        return a.value + (b.value - a.value) * r;
      }
    }
    return sorted[sorted.length - 1].value;
  };

  const zoomedPoints = sorted.filter((p) => p.t >= minX && p.t <= maxX);
  if (!zoomedPoints.length || zoomedPoints[0].t > minX) {
    zoomedPoints.unshift({ t: minX, value: valueAt(minX) });
  }
  if (zoomedPoints[zoomedPoints.length - 1].t < maxX) {
    zoomedPoints.push({ t: maxX, value: valueAt(maxX) });
  }

  const minVal = Math.min(...zoomedPoints.map((p) => p.value));
  const maxVal = Math.max(...zoomedPoints.map((p) => p.value));
  let minY = 0;
  let maxY = Math.max(1, maxVal);
  if (sparseSeries) {
    if (maxVal > minVal) {
      const yPad = Math.max(0.5, (maxVal - minVal) * 0.18);
      minY = Math.max(0, minVal - yPad);
      maxY = maxVal + yPad;
    } else {
      minY = Math.max(0, minVal - 1);
      maxY = maxVal + 1;
    }
  }
  if (maxY <= minY) maxY = minY + 1;

  const toX = (t: number): number => {
    return padX + ((t - minX) / (maxX - minX)) * (width - padX * 2);
  };

  const toY = (v: number): number => {
    const vv = Math.max(minY, Math.min(maxY, Number.isFinite(v) ? v : minY));
    return height - padY - ((vv - minY) / (maxY - minY)) * (height - padY * 2);
  };

  const d = zoomedPoints
    .map((p, i) => `${i === 0 ? "M" : "L"} ${toX(p.t).toFixed(2)} ${toY(p.value).toFixed(2)}`)
    .join(" ");

  const baselineY = toY(minY);
  const area = `${d} L ${toX(maxX).toFixed(2)} ${baselineY.toFixed(2)} L ${toX(minX).toFixed(2)} ${baselineY.toFixed(2)} Z`;

  const showPoints = zoomedPoints.filter(
    (_, i) => i % Math.max(1, Math.floor(zoomedPoints.length / 16)) === 0 || i === zoomedPoints.length - 1
  );
  const maxYLabel = Math.round(maxY * 10) / 10;

  return (
    <svg className="lineSvg" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <line x1={padX} y1={height - padY} x2={width - padX} y2={height - padY} className="axis" />
      <line x1={padX} y1={padY} x2={padX} y2={height - padY} className="axis" />
      <path d={area} className="lineArea" />
      <path d={d} className="linePath" />
      {showPoints.map((p, i) => (
        <circle key={i} cx={toX(p.t)} cy={toY(p.value)} r={2.8} className="linePoint" />
      ))}
      <text x={padX} y={padY + 3} className="lineYLabel">
        {maxYLabel}
      </text>
      {sparseSeries ? (
        <text x={width - padX} y={padY + 3} textAnchor="end" className="lineYLabel">
          zoom
        </text>
      ) : null}
      <text x={padX} y={height - 4} className="lineXLabel">
        {fmtTs(new Date(minX).toISOString())}
      </text>
      <text x={width - padX} y={height - 4} textAnchor="end" className="lineXLabel">
        {fmtTs(new Date(maxX).toISOString())}
      </text>
    </svg>
  );
}

function WorkspaceHeatmap({
  labels,
  rows,
  maxCellSeconds
}: {
  labels: string[];
  rows: WorkspaceHeatmapRow[];
  maxCellSeconds: number;
}) {
  const [hovered, setHovered] = useState<HoverTooltip | null>(null);

  const updateHover = (e: MouseEvent<HTMLDivElement>, label: string, meta?: string) => {
    const p = tooltipPoint(e);
    setHovered({ x: p.x, y: p.y, label, meta });
  };

  if (!labels.length || !rows.length) {
    return <div className="empty">No workspace heatmap data.</div>;
  }

  const cols = `minmax(72px,auto) repeat(${labels.length}, minmax(14px,1fr)) minmax(60px,auto)`;

  return (
    <div className="wsHeatmapWrap">
      <div className="wsHeatmapLegend">
        <span>low</span>
        <span className="wsHeatmapGradient" />
        <span>high</span>
      </div>
      <div className="wsHeatmapScroll">
        <div className="wsHeatmapGrid" style={{ gridTemplateColumns: cols }}>
          <div className="wsHeatmapCorner" />
          {labels.map((label, idx) => (
            <div key={`ws-head-${idx}`} className="wsHeatmapHeader">
              {label}
            </div>
          ))}
          <div className="wsHeatmapHeader wsHeatmapHeaderTotal">total</div>
          {rows.map((row) => (
            <Fragment key={row.id}>
              <div
                className="wsHeatmapRowLabel"
                onMouseEnter={(e) => updateHover(e, row.label, `total ${fmtSeconds(row.total)}`)}
                onMouseMove={(e) => updateHover(e, row.label, `total ${fmtSeconds(row.total)}`)}
                onMouseLeave={() => setHovered(null)}
              >
                {row.label}
              </div>
              {row.cells.map((seconds, idx) => {
                const ratio = maxCellSeconds > 0 ? Math.max(0, Math.min(1, seconds / maxCellSeconds)) : 0;
                const label = `${row.label} · ${labels[idx]}`;
                const meta = fmtSeconds(seconds);
                return (
                  <div
                    key={`${row.id}-${idx}`}
                    className="wsHeatmapCell"
                    style={{ background: workspaceHeatColor(ratio) }}
                    onMouseEnter={(e) => updateHover(e, label, meta)}
                    onMouseMove={(e) => updateHover(e, label, meta)}
                    onMouseLeave={() => setHovered(null)}
                  />
                );
              })}
              <div className="wsHeatmapRowTotal">{fmtSecondsShort(row.total)}</div>
            </Fragment>
          ))}
        </div>
      </div>
      <TooltipPortal tooltip={hovered} />
    </div>
  );
}

function WorkspaceTransitionMatrixView({ matrix }: { matrix: WorkspaceTransitionMatrix }) {
  const [hovered, setHovered] = useState<HoverTooltip | null>(null);
  const { workspaces, counts, outTotals, inTotals, maxCell, total } = matrix;

  const updateHover = (e: MouseEvent<HTMLDivElement>, label: string, meta?: string) => {
    const p = tooltipPoint(e);
    setHovered({ x: p.x, y: p.y, label, meta });
  };

  if (!workspaces.length) {
    return <div className="empty">No transitions in this range.</div>;
  }

  const cols = `minmax(94px,auto) repeat(${workspaces.length}, minmax(30px,1fr)) minmax(64px,auto)`;

  return (
    <div className="wsMatrixWrap">
      <div className="wsMatrixNote sub">rows: from workspace · columns: to workspace · total switches: {total}</div>
      <div className="wsMatrixScroll">
        <div className="wsMatrixGrid" style={{ gridTemplateColumns: cols }}>
          <div className="wsMatrixCorner">from \ to</div>
          {workspaces.map((ws) => (
            <div key={`to-${ws}`} className="wsMatrixHead">
              {workspaceLabel(ws)}
            </div>
          ))}
          <div className="wsMatrixHead wsMatrixHeadTotal">out</div>

          {workspaces.map((from, i) => {
            const fromColor = workspaceTransitionColors(from);
            return (
              <Fragment key={`row-${from}`}>
                <div
                  className="wsMatrixRowLabel"
                  onMouseEnter={(e) => updateHover(e, workspaceLabel(from), `outgoing switches: ${outTotals[i] || 0}`)}
                  onMouseMove={(e) => updateHover(e, workspaceLabel(from), `outgoing switches: ${outTotals[i] || 0}`)}
                  onMouseLeave={() => setHovered(null)}
                >
                  <span
                    className="wsTransitionTag"
                    style={{ background: fromColor.bg, borderColor: fromColor.border, color: fromColor.text }}
                  >
                    {workspaceLabel(from)}
                  </span>
                </div>
                {workspaces.map((to, j) => {
                  const count = counts[i]?.[j] || 0;
                  const ratio = maxCell > 0 ? Math.max(0, Math.min(1, count / maxCell)) : 0;
                  const toColor = workspaceTransitionColors(to);
                  return (
                    <div
                      key={`cell-${from}-${to}`}
                      className={`wsMatrixCell ${count > 0 ? "active" : ""}`}
                      style={{ background: workspaceHeatColor(ratio) }}
                      onMouseEnter={(e) =>
                        updateHover(
                          e,
                          `${workspaceLabel(from)} → ${workspaceLabel(to)}`,
                          `${count} switches${total > 0 ? ` · ${fmtPct((count / total) * 100)}` : ""}`
                        )
                      }
                      onMouseMove={(e) =>
                        updateHover(
                          e,
                          `${workspaceLabel(from)} → ${workspaceLabel(to)}`,
                          `${count} switches${total > 0 ? ` · ${fmtPct((count / total) * 100)}` : ""}`
                        )
                      }
                      onMouseLeave={() => setHovered(null)}
                    >
                      {count > 0 ? (
                        <span className="wsMatrixCellText" style={{ color: toColor.text }}>
                          {count}
                        </span>
                      ) : (
                        <span className="wsMatrixCellDot" />
                      )}
                    </div>
                  );
                })}
                <div className="wsMatrixRowTotal">{outTotals[i] || 0}</div>
              </Fragment>
            );
          })}

          <div className="wsMatrixFooterLabel">in</div>
          {inTotals.map((count, idx) => (
            <div key={`in-${workspaces[idx]}`} className="wsMatrixColTotal">
              {count}
            </div>
          ))}
          <div className="wsMatrixFooterTotal">{total}</div>
        </div>
      </div>
      <TooltipPortal tooltip={hovered} />
    </div>
  );
}

function LegacyTimeline({
  chunks,
  range,
  fromTs,
  toTs
}: {
  chunks: TimelineChunk[];
  range: RangeKey;
  fromTs: string;
  toTs: string;
}) {
  const [hovered, setHovered] = useState<HoverTooltip | null>(null);

  const updateHover = (
    ev: MouseEvent<HTMLDivElement>,
    entry: { start_ts: string; end_ts: string; active: number; afk: number; off: number; top_app?: string | null }
  ) => {
    const p = tooltipPoint(ev);
    setHovered({
      x: p.x,
      y: p.y,
      label: `${fmtTs(entry.start_ts)} → ${fmtTs(entry.end_ts)}`,
      meta: `active ${fmtSeconds(entry.active)} · afk ${fmtSeconds(entry.afk)} · off ${fmtSeconds(entry.off)}${
        entry.top_app ? ` · top ${entry.top_app}` : ""
      }`
    });
  };

  if (!chunks.length) return <div className="empty">No timeline data.</div>;

  let inferredChunkSeconds = 0;
  for (const c of chunks) {
    const s = Date.parse(c.start_ts);
    const e = Date.parse(c.end_ts);
    if (!Number.isNaN(s) && !Number.isNaN(e) && e > s) {
      inferredChunkSeconds = (e - s) / 1000;
      break;
    }
  }
  if (inferredChunkSeconds <= 0 && fromTs && toTs && chunks.length > 0) {
    const fromMs = Date.parse(fromTs);
    const toMs = Date.parse(toTs);
    if (!Number.isNaN(fromMs) && !Number.isNaN(toMs) && toMs > fromMs) {
      inferredChunkSeconds = (toMs - fromMs) / chunks.length / 1000;
    }
  }

  const entries = chunks.map((c, i) => {
    const startMs = Date.parse(c.start_ts);
    const endMs = Date.parse(c.end_ts);
    const bucketSec =
      !Number.isNaN(startMs) && !Number.isNaN(endMs) && endMs > startMs
        ? (endMs - startMs) / 1000
        : inferredChunkSeconds;
    const active = Number(c.active_seconds || 0) || 0;
    const afk = Number(c.afk_seconds || 0) || 0;
    const off = Number(c.unknown_seconds || 0) || 0;
    const aPct = bucketSec > 0 ? (active / bucketSec) * 100 : 0;
    const fPct = bucketSec > 0 ? (afk / bucketSec) * 100 : 0;
    const aPctC = Math.max(0, Math.min(100, aPct));
    const fPctC = Math.max(0, Math.min(aPctC, fPct));
    return {
      idx: i,
      ...c,
      active,
      afk,
      off,
      activePct: aPctC,
      afkPct: fPctC
    };
  });

  const avgActivePct =
    entries.length > 0 ? entries.reduce((sum, e) => sum + e.activePct, 0) / entries.length : 0;
  const peak = entries.reduce((best, e) => (best == null || e.activePct > best.activePct ? e : best), null as
    | (typeof entries)[number]
    | null);

  const labelText = (start: string): string => {
    const d = new Date(start);
    if (Number.isNaN(d.getTime())) return "";
    if (range === "24h") return String(d.getHours()).padStart(2, "0");
    if (range === "1w") return d.toLocaleDateString(undefined, { weekday: "short" });
    return d.toLocaleDateString(undefined, { month: "2-digit", day: "2-digit" });
  };

  const showLabel = (i: number, n: number): boolean => {
    if (range === "24h") return i % 3 === 0 || i === n - 1;
    if (range === "1w") return true;
    if (range === "1m") return i % 5 === 0 || i === n - 1;
    const step = Math.max(1, Math.round(n / 6));
    return i % step === 0 || i === n - 1;
  };

  const maxHours = Math.max(0, inferredChunkSeconds / 3600);
  const midHours = maxHours / 2;
  let infoBase = "";
  if (range === "24h") infoBase = "per hour";
  else if (range === "1w" || range === "1m") infoBase = "per day";
  else {
    const chunk = Math.max(1, Math.round(inferredChunkSeconds));
    if (chunk >= 86400) infoBase = `per ${Math.round(chunk / 86400)}d`;
    else if (chunk >= 3600) infoBase = `per ${Math.round(chunk / 3600)}h`;
    else infoBase = `per ${Math.max(1, Math.round(chunk / 60))}m`;
  }

  const peakLeftPct = peak && entries.length > 0 ? ((peak.idx + 0.5) / entries.length) * 100 : 0;

  return (
    <div>
      <div className="timelineTopLegacy">
        <div className="timelineLegendLegacy">
          <span className="legendItemLegacy">
            <span className="legendDotLegacy" style={{ background: "rgba(45,212,191,.70)" }} />
            Active
          </span>
          <span className="legendItemLegacy">
            <span className="legendDotLegacy" style={{ background: "rgba(251,191,36,.72)" }} />
            AFK
          </span>
          <span className="legendItemLegacy">
            <span className="legendDotLegacy" style={{ background: "rgba(255,255,255,.18)" }} />
            Off
          </span>
        </div>
      </div>
      <div className="sub timelineInfoLegacy">
        {infoBase} · avg {Math.round(avgActivePct * 10) / 10}% · peak{" "}
        {peak ? Math.round(peak.activePct * 10) / 10 : 0}%
      </div>
      <div className="timelineWrapLegacy">
        <div className="timelineAxisLegacy" aria-hidden="true">
          <span>{fmtHours(maxHours)}</span>
          <span>{fmtHours(midHours)}</span>
          <span>0h</span>
        </div>
        <div className="timelinePlotLegacy">
          <div className="timelineGridLegacy" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          {entries.length > 0 ? (
            <div className="timelineAvgLegacy" style={{ bottom: `${Math.max(0, Math.min(100, avgActivePct))}%` }} />
          ) : null}
          {peak && peak.activePct > 0 ? (
            <div className="timelinePeakLegacy" style={{ left: `${peakLeftPct}%` }} />
          ) : null}
          <div className="timelineLegacy">
            {entries.map((e) => (
              <div
                key={`${e.start_ts}-${e.idx}`}
                className="barColLegacy"
                onMouseEnter={(ev) => updateHover(ev, e)}
                onMouseMove={(ev) => updateHover(ev, e)}
                onMouseLeave={() => setHovered(null)}
              >
                <div className="barSegLegacy active" style={{ height: `${e.activePct}%` }} />
                <div className="barSegLegacy afkOverlay" style={{ height: `${e.afkPct}%` }} />
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="timelineLabelsLegacy timelinePadLegacy" aria-label="timeline labels">
        {entries.map((e, i) => (
          <span key={`${e.start_ts}-lbl`}>{showLabel(i, entries.length) ? labelText(e.start_ts) : ""}</span>
        ))}
      </div>
      <div className="timelineScaleLegacy timelinePadLegacy">
        <span>{fmtTs(fromTs)}</span>
        <span>{fmtTs(toTs)}</span>
      </div>
      <TooltipPortal tooltip={hovered} />
    </div>
  );
}

export default function App() {
  const pathname = String(window.location.pathname || "").replace(/\/+$/, "");
  const page: "dashboard" | "stats" = pathname.endsWith("/ui/stats") ? "stats" : "dashboard";
  const searchParams = new URLSearchParams(String(window.location.search || ""));
  const uiPrefix = pathPrefixBeforeUi(pathname);
  const uiBase = `${uiPrefix}/ui`;
  const initialRange = parseRangeKey(searchParams.get("range"));
  const initialTopic = parseTopicId(searchParams.get("topic"));

  const [range, setRange] = useState<RangeKey>(initialRange);
  const [topic, setTopic] = useState<TopicId>(initialTopic);
  const [monitorSetupFilter, setMonitorSetupFilter] = useState<MonitorSetupFilter>("all");
  const [reloadKey, setReloadKey] = useState(0);

  function replaceQuery(nextRange: RangeKey, nextTopic: TopicId): void {
    const params = new URLSearchParams(String(window.location.search || ""));
    params.set("range", nextRange);
    if (page === "stats") params.set("topic", nextTopic);
    else params.delete("topic");
    const query = params.toString();
    const nextUrl = `${window.location.pathname}${query ? `?${query}` : ""}`;
    window.history.replaceState(null, "", nextUrl);
  }

  function onRangeChange(next: RangeKey): void {
    setRange(next);
    replaceQuery(next, topic);
  }

  function onTopicChange(next: TopicId): void {
    setTopic(next);
    replaceQuery(range, next);
  }

  function hrefFor(target: "dashboard" | "stats"): string {
    const params = new URLSearchParams();
    params.set("range", range);
    if (target === "stats") params.set("topic", topic);
    const qs = params.toString();
    return target === "dashboard"
      ? `${uiBase}/${qs ? `?${qs}` : ""}`
      : `${uiBase}/stats${qs ? `?${qs}` : ""}`;
  }

  const [windowRange, setWindowRange] = useState<TimeWindow | null>(null);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [categories, setCategories] = useState<CategoriesResponse | null>(null);
  const [windowEvents, setWindowEvents] = useState<ApiEvent[]>([]);
  const [workspaceEvents, setWorkspaceEvents] = useState<ApiEvent[]>([]);
  const [workspaceSwitchEvents, setWorkspaceSwitchEvents] = useState<ApiEvent[]>([]);
  const [tabsEvents, setTabsEvents] = useState<ApiEvent[]>([]);
  const [visibleEvents, setVisibleEvents] = useState<ApiEvent[]>([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [updatedAt, setUpdatedAt] = useState("");

  const workspaceEventsFiltered = useMemo(
    () => workspaceEvents.filter((e) => matchesMonitorSetupFilter(e, monitorSetupFilter)),
    [workspaceEvents, monitorSetupFilter]
  );
  const workspaceSwitchEventsFiltered = useMemo(
    () => workspaceSwitchEvents.filter((e) => matchesMonitorSetupFilter(e, monitorSetupFilter)),
    [workspaceSwitchEvents, monitorSetupFilter]
  );

  useEffect(() => {
    let cancelled = false;
    let timer: number | null = null;

    async function load() {
      if (!cancelled) setLoading(true);
      const errors: string[] = [];

      const timeWindow = await resolveWindow(range);
      if (cancelled) return;
      setWindowRange(timeWindow);

      const query = qs(timeWindow);
      const fromMs = Date.parse(timeWindow.from);
      const toMs = Date.parse(timeWindow.to);
      const durationSeconds =
        !Number.isNaN(fromMs) && !Number.isNaN(toMs) && toMs > fromMs ? (toMs - fromMs) / 1000 : 0;
      const chunkSeconds = chunkSecondsForRange(range, durationSeconds);
      const summaryQuery = `${query}&chunk_seconds=${chunkSeconds}`;

      async function safe<T>(label: string, fn: () => Promise<T>, fallback: T): Promise<T> {
        try {
          return await fn();
        } catch (e) {
          errors.push(`${label}: ${String(e)}`);
          return fallback;
        }
      }

      const [
        summaryData,
        categoriesData,
        windowData,
        workspaceData,
        workspaceSwitchData,
        tabsData,
        visibleData
      ] = await Promise.all([
        safe(
          "summary",
          () => fetchJson<SummaryResponse>(`/v1/summary?${summaryQuery}`),
          null as SummaryResponse | null
        ),
        safe(
          "categories",
          () => fetchJson<CategoriesResponse>(`/v1/categories?mode=auto&${query}`),
          null as CategoriesResponse | null
        ),
        safe("window", () => fetchJson<EventsResponse>(`/v1/events?bucket=window&${query}`), { events: [] }),
        safe("workspace", () => fetchJson<EventsResponse>(`/v1/events?bucket=workspace&${query}`), { events: [] }),
        safe(
          "workspace_switch",
          () => fetchJson<EventsResponse>(`/v1/events?bucket=workspace_switch&${query}`),
          { events: [] }
        ),
        safe("browser_tabs", () => fetchJson<EventsResponse>(`/v1/events?bucket=browser_tabs&${query}`), { events: [] }),
        safe("window_visible", () => fetchJson<EventsResponse>(`/v1/events?bucket=window_visible&${query}`), {
          events: []
        })
      ]);

      if (cancelled) return;

      setSummary(summaryData);
      setCategories(categoriesData);
      setWindowEvents(Array.isArray(windowData.events) ? windowData.events : []);
      setWorkspaceEvents(Array.isArray(workspaceData.events) ? workspaceData.events : []);
      setWorkspaceSwitchEvents(Array.isArray(workspaceSwitchData.events) ? workspaceSwitchData.events : []);
      setTabsEvents(Array.isArray(tabsData.events) ? tabsData.events : []);
      setVisibleEvents(Array.isArray(visibleData.events) ? visibleData.events : []);

      setError(errors.join(" | "));
      setUpdatedAt(new Date().toLocaleTimeString());
      setLoading(false);
    }

    void load();
    timer = window.setInterval(() => void load(), 30_000);

    return () => {
      cancelled = true;
      if (timer != null) window.clearInterval(timer);
    };
  }, [range, reloadKey]);

  const topApps = useMemo(() => {
    if (!summary) return [] as SummaryApp[];
    return [...(summary.top_apps || [])].sort((a, b) => (b.seconds || 0) - (a.seconds || 0)).slice(0, 20);
  }, [summary]);

  const activitySlices = useMemo<SliceRow[]>(() => {
    if (!summary) return [];

    const activeAppItems = topApps.slice(0, 8).map((a) => ({
      label: a.app,
      value: fmtSeconds(a.seconds || 0)
    }));

    const afkByTopApp = new Map<string, number>();
    let afkChunkCount = 0;
    let offChunkCount = 0;
    for (const chunk of summary.timeline_chunks || []) {
      const afk = Number(chunk.afk_seconds || 0);
      const off = Number(chunk.unknown_seconds || 0);
      if (afk > 0) {
        afkChunkCount += 1;
        const app = trimLabel(String(chunk.top_app || "unknown"), 84);
        afkByTopApp.set(app, (afkByTopApp.get(app) || 0) + afk);
      }
      if (off > 0) offChunkCount += 1;
    }

    const afkTopItems = Array.from(afkByTopApp.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
      .map(([label, seconds]) => ({ label, value: fmtSeconds(seconds) }));

    return [
      {
        id: "active",
        label: "Active",
        seconds: summary.active_seconds || 0,
        color: "#2dd4bf",
        details: [
          {
            title: "Top apps",
            items: activeAppItems,
            emptyText: "No app data available."
          }
        ]
      },
      {
        id: "afk",
        label: "AFK",
        seconds: summary.afk_seconds || 0,
        color: "#fbbf24",
        details: [
          {
            title: "AFK chunks",
            items: [{ label: "Chunks with AFK time", value: String(afkChunkCount) }]
          },
          {
            title: "Top apps during AFK chunks",
            items: afkTopItems,
            emptyText: "No app hints found in AFK chunks."
          }
        ]
      },
      {
        id: "off",
        label: "Off",
        seconds: summary.unknown_seconds || 0,
        color: "rgba(255,255,255,.35)",
        details: [
          {
            title: "Off chunks",
            items: [{ label: "Chunks with Off time", value: String(offChunkCount) }]
          }
        ]
      }
    ];
  }, [summary, topApps]);

  const websites = useMemo<SiteRow[]>(() => {
    const map = new Map<string, SiteRow>();
    for (const e of windowEvents) {
      const app = asString(e?.data?.app);
      const title = asString(e?.data?.title);
      const site = extractSite(app, title);
      if (!site) continue;
      const start = Date.parse(e.start_ts);
      const end = Date.parse(e.end_ts);
      if (Number.isNaN(start) || Number.isNaN(end) || end <= start) continue;
      const dur = (end - start) / 1000;
      const prev = map.get(site) || { site, seconds: 0, visits: 0, lastTs: "" };
      prev.seconds += dur;
      prev.visits += 1;
      if (!prev.lastTs || e.end_ts > prev.lastTs) prev.lastTs = e.end_ts;
      map.set(site, prev);
    }
    return Array.from(map.values()).sort((a, b) => b.seconds - a.seconds).slice(0, 25);
  }, [windowEvents]);

  const workspaceInsights = useMemo(() => {
    const empty = {
      heatmapRows: [] as WorkspaceHeatmapRow[],
      heatmapLabels: [] as string[],
      heatmapMaxCellSeconds: 0,
      heatmapBinSize: "",
      timeRows: [] as BarRow[],
      shareSlices: [] as SliceRow[],
      totalSeconds: 0,
      switchSeries: [] as LinePoint[],
      switchCount: 0
    };

    if (!windowRange) return empty;
    const fromMs = Date.parse(windowRange.from);
    const toMs = Date.parse(windowRange.to);
    if (Number.isNaN(fromMs) || Number.isNaN(toMs) || toMs <= fromMs) return empty;

    let stepMs = 3600_000;
    if (range === "1w" || range === "1m") {
      stepMs = 86400_000;
    } else if (range === "all") {
      const durationMs = toMs - fromMs;
      const targetCols = 28;
      const rawStepMs = Math.max(3600_000, Math.ceil(durationMs / targetCols));
      const stepChoices = [
        3600_000, 7200_000, 10800_000, 21600_000, 43200_000, 86400_000, 172800_000, 259200_000, 604800_000,
        1209600_000, 2592000_000
      ];
      stepMs = stepChoices.find((v) => rawStepMs <= v) || rawStepMs;
    }

    const starts: number[] = [];
    const ends: number[] = [];
    const labels: string[] = [];
    for (let s = fromMs; s < toMs; s += stepMs) {
      const e = Math.min(toMs, s + stepMs);
      starts.push(s);
      ends.push(e);
      labels.push(workspaceBinLabel(range, s, stepMs));
    }
    if (!starts.length) return empty;

    const byWorkspace = new Map<string, { total: number; cells: number[] }>();
    const ensureWorkspace = (ws: string) => {
      let cur = byWorkspace.get(ws);
      if (!cur) {
        cur = { total: 0, cells: new Array(starts.length).fill(0) };
        byWorkspace.set(ws, cur);
      }
      return cur;
    };

    for (const e of workspaceEventsFiltered) {
      const ws = asString(e?.data?.workspace) || asString(e?.data?.workspace_id) || "unknown";
      const start = Date.parse(e.start_ts);
      const end = Date.parse(e.end_ts);
      if (Number.isNaN(start) || Number.isNaN(end) || end <= start) continue;
      if (end <= fromMs || start >= toMs) continue;
      const clippedStart = Math.max(fromMs, start);
      const clippedEnd = Math.min(toMs, end);
      if (clippedEnd <= clippedStart) continue;

      const row = ensureWorkspace(ws);
      row.total += (clippedEnd - clippedStart) / 1000;

      let curMs = clippedStart;
      while (curMs < clippedEnd) {
        const idx = Math.max(0, Math.min(starts.length - 1, Math.floor((curMs - fromMs) / stepMs)));
        const segEnd = Math.min(clippedEnd, ends[idx]);
        const segSeconds = (segEnd - curMs) / 1000;
        if (segSeconds > 0) row.cells[idx] += segSeconds;
        if (segEnd <= curMs) break;
        curMs = segEnd;
      }
    }

    const ordered = Array.from(byWorkspace.entries()).sort((a, b) => b[1].total - a[1].total);
    const palette = ["#2dd4bf", "#60a5fa", "#a78bfa", "#f472b6", "#f59e0b", "#22c55e", "#fb7185", "#38bdf8"];

    const heatmapRows: WorkspaceHeatmapRow[] = ordered.slice(0, 12).map(([ws, row]) => ({
      id: ws,
      label: `WS ${ws}`,
      total: row.total,
      cells: row.cells
    }));

    const heatmapMaxCellSeconds = heatmapRows.reduce((m, row) => {
      const rowMax = row.cells.reduce((r, cell) => Math.max(r, cell), 0);
      return Math.max(m, rowMax);
    }, 0);

    const timeRows: BarRow[] = ordered
      .slice(0, 20)
      .map(([ws, row]) => ({ id: ws, label: `WS ${ws}`, value: row.total, color: "linear-gradient(90deg,#60a5fa,#22d3ee)" }));

    const shareSlices: SliceRow[] = ordered.slice(0, 12).map(([ws, row], idx) => {
      let peakIdx = 0;
      for (let i = 1; i < row.cells.length; i += 1) {
        if ((row.cells[i] || 0) > (row.cells[peakIdx] || 0)) peakIdx = i;
      }
      const peakSeconds = row.cells[peakIdx] || 0;
      return {
        id: ws,
        label: `WS ${ws}`,
        seconds: row.total,
        color: palette[idx % palette.length],
        details: [
          {
            title: "Usage",
            items: [
              { label: "Total", value: fmtSeconds(row.total) },
              {
                label: "Peak slot",
                value: peakSeconds > 0 && labels[peakIdx] ? `${labels[peakIdx]} · ${fmtSeconds(peakSeconds)}` : "n/a"
              }
            ]
          }
        ]
      };
    });

    const switchCells = new Array(starts.length).fill(0);
    for (const e of workspaceSwitchEventsFiltered) {
      const ts = Date.parse(e.start_ts || e.end_ts);
      if (Number.isNaN(ts) || ts < fromMs || ts >= toMs) continue;
      const idx = Math.max(0, Math.min(starts.length - 1, Math.floor((ts - fromMs) / stepMs)));
      switchCells[idx] += 1;
    }

    const switchSeries: LinePoint[] = starts.map((s, idx) => ({
      t: s + Math.round((ends[idx] - s) / 2),
      value: switchCells[idx]
    }));

    if (switchSeries.length === 1) {
      switchSeries.push({ t: toMs, value: switchSeries[0].value });
    }

    const totalSeconds = ordered.reduce((sum, [, row]) => sum + row.total, 0);
    const switchCount = switchCells.reduce((sum, value) => sum + value, 0);

    return {
      heatmapRows,
      heatmapLabels: labels,
      heatmapMaxCellSeconds,
      heatmapBinSize: workspaceBinSizeLabel(stepMs),
      timeRows,
      shareSlices,
      totalSeconds,
      switchSeries,
      switchCount
    };
  }, [workspaceEventsFiltered, workspaceSwitchEventsFiltered, windowRange, range]);

  const workspaceTransitionMatrix = useMemo<WorkspaceTransitionMatrix>(() => {
    const outTotalsMap = new Map<string, number>();
    const inTotalsMap = new Map<string, number>();
    const pairMap = new Map<string, Map<string, number>>();

    for (const e of workspaceSwitchEventsFiltered) {
      const from =
        asString(e?.data?.from_workspace) || asString(e?.data?.prev_workspace) || asString(e?.data?.workspace) || "?";
      const to = asString(e?.data?.to_workspace) || asString(e?.data?.workspace) || "?";

      outTotalsMap.set(from, (outTotalsMap.get(from) || 0) + 1);
      inTotalsMap.set(to, (inTotalsMap.get(to) || 0) + 1);

      const row = pairMap.get(from) || new Map<string, number>();
      row.set(to, (row.get(to) || 0) + 1);
      pairMap.set(from, row);
    }

    const involvement = new Map<string, number>();
    for (const [ws, count] of outTotalsMap.entries()) involvement.set(ws, (involvement.get(ws) || 0) + count);
    for (const [ws, count] of inTotalsMap.entries()) involvement.set(ws, (involvement.get(ws) || 0) + count);

    const workspaces = Array.from(involvement.keys()).sort(compareWorkspaceIds);

    if (!workspaces.length) {
      return { workspaces: [], counts: [], outTotals: [], inTotals: [], maxCell: 0, total: 0 };
    }

    const counts = Array.from({ length: workspaces.length }, () => new Array<number>(workspaces.length).fill(0));
    let maxCell = 0;
    for (let i = 0; i < workspaces.length; i += 1) {
      const from = workspaces[i];
      for (let j = 0; j < workspaces.length; j += 1) {
        const to = workspaces[j];
        const count = pairMap.get(from)?.get(to) || 0;
        counts[i][j] = count;
        if (count > maxCell) maxCell = count;
      }
    }

    const outTotals = workspaces.map((ws) => outTotalsMap.get(ws) || 0);
    const inTotals = workspaces.map((ws) => inTotalsMap.get(ws) || 0);
    const total = Array.from(outTotalsMap.values()).reduce((sum, v) => sum + v, 0);

    return {
      workspaces,
      counts,
      outTotals,
      inTotals,
      maxCell,
      total
    };
  }, [workspaceSwitchEventsFiltered]);

  const monitorInsights = useMemo(() => {
    const empty = {
      setupSlices: [] as SliceRow[],
      totalSeconds: 0,
      countSeries: [] as LinePoint[],
      avgCount: 0,
      peakCount: 0,
      heatmapRows: [] as WorkspaceHeatmapRow[],
      heatmapLabels: [] as string[],
      heatmapMaxCellSeconds: 0,
      heatmapBinSize: "",
      setupRows: [] as BarRow[],
      monitorPeriods: [] as MonitorEnabledPeriodRow[]
    };

    if (!windowRange) return empty;
    const fromMs = Date.parse(windowRange.from);
    const toMs = Date.parse(windowRange.to);
    if (Number.isNaN(fromMs) || Number.isNaN(toMs) || toMs <= fromMs) return empty;

    let stepMs = 3600_000;
    if (range === "1w" || range === "1m") {
      stepMs = 86400_000;
    } else if (range === "all") {
      const durationMs = toMs - fromMs;
      const targetCols = 28;
      const rawStepMs = Math.max(3600_000, Math.ceil(durationMs / targetCols));
      const stepChoices = [
        3600_000, 7200_000, 10800_000, 21600_000, 43200_000, 86400_000, 172800_000, 259200_000, 604800_000,
        1209600_000, 2592000_000
      ];
      stepMs = stepChoices.find((v) => rawStepMs <= v) || rawStepMs;
    }

    const starts: number[] = [];
    const ends: number[] = [];
    const labels: string[] = [];
    for (let s = fromMs; s < toMs; s += stepMs) {
      const e = Math.min(toMs, s + stepMs);
      starts.push(s);
      ends.push(e);
      labels.push(workspaceBinLabel(range, s, stepMs));
    }
    if (!starts.length) return empty;

    type MonitorSetupKey = "single" | "multi" | "unknown";
    type RawPeriod = {
      startMs: number;
      endMs: number;
      setup: MonitorSetupKey;
      monitorCount: number;
      monitors: string[];
      signature: string;
    };

    const byMonitor = new Map<string, { total: number; cells: number[] }>();
    const ensureMonitor = (name: string) => {
      let cur = byMonitor.get(name);
      if (!cur) {
        cur = { total: 0, cells: new Array(starts.length).fill(0) };
        byMonitor.set(name, cur);
      }
      return cur;
    };

    const setupSeconds: Record<MonitorSetupKey, number> = { single: 0, multi: 0, unknown: 0 };
    const setupCombos: Record<MonitorSetupKey, Map<string, number>> = {
      single: new Map(),
      multi: new Map(),
      unknown: new Map()
    };

    const countWeightedCells = new Array(starts.length).fill(0);
    const countSecondsCells = new Array(starts.length).fill(0);
    const periodsRaw: RawPeriod[] = [];

    for (const e of workspaceEventsFiltered) {
      const data = (e?.data && typeof e.data === "object" ? e.data : undefined) as Record<string, unknown> | undefined;
      const start = Date.parse(e.start_ts);
      const end = Date.parse(e.end_ts);
      if (Number.isNaN(start) || Number.isNaN(end) || end <= start) continue;
      if (end <= fromMs || start >= toMs) continue;
      const clippedStart = Math.max(fromMs, start);
      const clippedEnd = Math.min(toMs, end);
      if (clippedEnd <= clippedStart) continue;

      const setupDetected = monitorSetupFromData(data);
      const setup: MonitorSetupKey = setupDetected || "unknown";
      let monitors = connectedMonitorsFromData(data);
      let monitorCount = monitorCountFromData(data);
      if (monitorCount == null || monitorCount <= 0) {
        if (monitors.length) monitorCount = monitors.length;
        else if (setup === "multi") monitorCount = 2;
        else if (setup === "single") monitorCount = 1;
        else monitorCount = 0;
      }

      if (!monitors.length && setup === "single") {
        monitors = uniqueMonitorNames([asString(data?.monitor), asString(data?.focused_monitor)]);
      }

      const durationSeconds = (clippedEnd - clippedStart) / 1000;
      setupSeconds[setup] += durationSeconds;

      const comboLabel =
        monitors.length > 0 ? monitors.join(" + ") : monitorCount > 0 ? `${monitorCount} monitors` : "unknown monitors";
      const comboMap = setupCombos[setup];
      comboMap.set(comboLabel, (comboMap.get(comboLabel) || 0) + durationSeconds);

      const signature = monitors.length > 0 ? monitors.join("|") : `${setup}:${monitorCount}`;
      periodsRaw.push({
        startMs: clippedStart,
        endMs: clippedEnd,
        setup,
        monitorCount,
        monitors,
        signature
      });

      let curMs = clippedStart;
      while (curMs < clippedEnd) {
        const idx = Math.max(0, Math.min(starts.length - 1, Math.floor((curMs - fromMs) / stepMs)));
        const segEnd = Math.min(clippedEnd, ends[idx]);
        const segSeconds = (segEnd - curMs) / 1000;
        if (segSeconds > 0) {
          if (monitorCount > 0) {
            countWeightedCells[idx] += monitorCount * segSeconds;
            countSecondsCells[idx] += segSeconds;
          }
          for (const monitorName of monitors) {
            const row = ensureMonitor(monitorName);
            row.total += segSeconds;
            row.cells[idx] += segSeconds;
          }
        }
        if (segEnd <= curMs) break;
        curMs = segEnd;
      }
    }

    const totalSeconds = setupSeconds.single + setupSeconds.multi + setupSeconds.unknown;
    const setupSlices: SliceRow[] = [
      {
        id: "single",
        label: "single monitor",
        seconds: setupSeconds.single,
        color: "#2dd4bf",
        details: [
          {
            title: "Top setups",
            items: buildTopDetailItems(setupCombos.single, 8),
            emptyText: "No single-monitor setup samples."
          }
        ]
      },
      {
        id: "multi",
        label: "multi monitor",
        seconds: setupSeconds.multi,
        color: "#f59e0b",
        details: [
          {
            title: "Top setups",
            items: buildTopDetailItems(setupCombos.multi, 8),
            emptyText: "No multi-monitor setup samples."
          }
        ]
      },
      {
        id: "unknown",
        label: "unknown",
        seconds: setupSeconds.unknown,
        color: "rgba(148,163,184,.72)",
        details: [
          {
            title: "Top setups",
            items: buildTopDetailItems(setupCombos.unknown, 8),
            emptyText: "No monitor details in these samples."
          }
        ]
      }
    ].filter((slice) => slice.seconds > 0);

    const countSeries: LinePoint[] = starts.map((s, idx) => ({
      t: s + Math.round((ends[idx] - s) / 2),
      value: countSecondsCells[idx] > 0 ? countWeightedCells[idx] / countSecondsCells[idx] : 0
    }));
    if (countSeries.length === 1) {
      countSeries.push({ t: toMs, value: countSeries[0].value });
    }

    const totalCountWeighted = countWeightedCells.reduce((sum, value) => sum + value, 0);
    const totalCountSeconds = countSecondsCells.reduce((sum, value) => sum + value, 0);
    const avgCount = totalCountSeconds > 0 ? totalCountWeighted / totalCountSeconds : 0;
    const peakCount = countSeries.reduce((max, point) => Math.max(max, point.value), 0);

    const heatmapRows: WorkspaceHeatmapRow[] = Array.from(byMonitor.entries())
      .sort((a, b) => {
        const diff = b[1].total - a[1].total;
        if (diff !== 0) return diff;
        return a[0].localeCompare(b[0], undefined, { sensitivity: "base" });
      })
      .slice(0, 14)
      .map(([monitor, row]) => ({
        id: monitor,
        label: monitor,
        total: row.total,
        cells: row.cells
      }));

    const heatmapMaxCellSeconds = heatmapRows.reduce((max, row) => {
      const rowMax = row.cells.reduce((m, cell) => Math.max(m, cell), 0);
      return Math.max(max, rowMax);
    }, 0);

    const setupRowsSource: Array<{ label: string; setup: MonitorSetupKey; seconds: number }> = [];
    for (const key of ["multi", "single", "unknown"] as const) {
      for (const [label, seconds] of setupCombos[key].entries()) {
        setupRowsSource.push({ label, setup: key, seconds });
      }
    }
    const setupRows: BarRow[] = setupRowsSource
      .sort((a, b) => b.seconds - a.seconds)
      .slice(0, 16)
      .map((it, idx) => ({
        id: `setup-${it.setup}-${idx}-${it.label}`,
        label: it.label,
        value: it.seconds,
        sub: monitorSetupLabel(it.setup),
        color: monitorSetupBarColor(it.setup)
      }));

    periodsRaw.sort((a, b) => a.startMs - b.startMs || a.endMs - b.endMs);
    const merged: RawPeriod[] = [];
    for (const cur of periodsRaw) {
      const prev = merged[merged.length - 1];
      if (
        prev &&
        prev.setup === cur.setup &&
        prev.signature === cur.signature &&
        cur.startMs <= prev.endMs + 60_000
      ) {
        prev.endMs = Math.max(prev.endMs, cur.endMs);
        prev.monitorCount = Math.max(prev.monitorCount, cur.monitorCount);
      } else {
        merged.push({ ...cur, monitors: [...cur.monitors] });
      }
    }

    const monitorPeriodsRaw: Array<{
      monitor: string;
      startMs: number;
      endMs: number;
      maxMonitorCount: number;
      hasSingle: boolean;
      hasMulti: boolean;
      signature: string;
    }> = [];
    for (const p of merged) {
      for (const monitor of p.monitors) {
        monitorPeriodsRaw.push({
          monitor,
          startMs: p.startMs,
          endMs: p.endMs,
          maxMonitorCount: p.monitorCount,
          hasSingle: p.setup === "single",
          hasMulti: p.setup === "multi",
          signature: p.signature
        });
      }
    }

    monitorPeriodsRaw.sort(
      (a, b) =>
        a.monitor.localeCompare(b.monitor, undefined, { sensitivity: "base" }) || a.startMs - b.startMs || a.endMs - b.endMs
    );
    const mergedMonitorPeriods: typeof monitorPeriodsRaw = [];
    for (const cur of monitorPeriodsRaw) {
      const prev = mergedMonitorPeriods[mergedMonitorPeriods.length - 1];
      if (
        prev &&
        prev.monitor.toLowerCase() === cur.monitor.toLowerCase() &&
        cur.startMs <= prev.endMs + 60_000
      ) {
        prev.endMs = Math.max(prev.endMs, cur.endMs);
        prev.maxMonitorCount = Math.max(prev.maxMonitorCount, cur.maxMonitorCount);
        prev.hasSingle = prev.hasSingle || cur.hasSingle;
        prev.hasMulti = prev.hasMulti || cur.hasMulti;
      } else {
        mergedMonitorPeriods.push({ ...cur });
      }
    }

    const monitorPeriods: MonitorEnabledPeriodRow[] = mergedMonitorPeriods
      .map((p): MonitorEnabledPeriodRow => {
        const setup: MonitorEnabledPeriodRow["setup"] = p.hasMulti
          ? "multi"
          : p.hasSingle
            ? "single"
            : "unknown";
        return {
          monitor: p.monitor,
          start: new Date(p.startMs).toISOString(),
          end: new Date(p.endMs).toISOString(),
          durationSeconds: Math.max(0, (p.endMs - p.startMs) / 1000),
          setup,
          maxMonitorCount: p.maxMonitorCount,
          signature: `${p.monitor}:${p.signature}:${p.startMs}`
        };
      })
      .sort(
        (a, b) =>
          b.end.localeCompare(a.end) || a.monitor.localeCompare(b.monitor, undefined, { sensitivity: "base" })
      )
      .slice(0, 80);

    return {
      setupSlices,
      totalSeconds,
      countSeries,
      avgCount,
      peakCount,
      heatmapRows,
      heatmapLabels: labels,
      heatmapMaxCellSeconds,
      heatmapBinSize: workspaceBinSizeLabel(stepMs),
      setupRows,
      monitorPeriods
    };
  }, [workspaceEventsFiltered, windowRange, range]);

  const tabsCountSeries = useMemo<LinePoint[]>(() => {
    if (!windowRange) return [];
    const fromMs = Date.parse(windowRange.from);
    const toMs = Date.parse(windowRange.to);
    if (Number.isNaN(fromMs) || Number.isNaN(toMs) || toMs <= fromMs) return [];

    const changes = new Map<number, number>();
    for (const e of tabsEvents) {
      const start = Date.parse(e.start_ts);
      const end = Date.parse(e.end_ts);
      if (Number.isNaN(start) || Number.isNaN(end) || end <= start) continue;
      if (end <= fromMs || start >= toMs) continue;

      let count = asNumber(e?.data?.count);
      if (count <= 0 && Array.isArray(e?.data?.tabs)) count = e.data.tabs.length;
      if (count <= 0) continue;

      const s = Math.max(fromMs, start);
      const t = Math.min(toMs, end);
      changes.set(s, (changes.get(s) || 0) + count);
      changes.set(t, (changes.get(t) || 0) - count);
    }

    const stamps = Array.from(changes.keys()).sort((a, b) => a - b);
    let cur = 0;
    const points: LinePoint[] = [{ t: fromMs, value: 0 }];

    for (const ts of stamps) {
      cur += changes.get(ts) || 0;
      points.push({ t: ts, value: Math.max(0, cur) });
    }

    points.push({ t: toMs, value: Math.max(0, cur) });
    points.sort((a, b) => a.t - b.t);

    const dedup: LinePoint[] = [];
    for (const p of points) {
      const prev = dedup[dedup.length - 1];
      if (prev && prev.t === p.t) {
        prev.value = p.value;
      } else {
        dedup.push({ ...p });
      }
    }

    return dedup;
  }, [tabsEvents, windowRange]);

  const tabDomainSlices = useMemo<SliceRow[]>(() => {
    const fromMs = Date.parse(windowRange?.from || "");
    const toMs = Date.parse(windowRange?.to || "");
    if (Number.isNaN(fromMs) || Number.isNaN(toMs) || toMs <= fromMs) return [];

    const totals = new Map<string, number>();
    const titlesByDomain = new Map<string, Map<string, number>>();
    const browsersByDomain = new Map<string, Map<string, number>>();

    for (const e of tabsEvents) {
      const tabsRaw = e?.data?.tabs;
      if (!Array.isArray(tabsRaw) || !tabsRaw.length) continue;
      const start = Date.parse(e.start_ts);
      const end = Date.parse(e.end_ts);
      if (Number.isNaN(start) || Number.isNaN(end) || end <= start) continue;
      if (end <= fromMs || start >= toMs) continue;
      const clippedStart = Math.max(fromMs, start);
      const clippedEnd = Math.min(toMs, end);
      if (clippedEnd <= clippedStart) continue;
      const dur = (clippedEnd - clippedStart) / 1000;
      const browser = asString(e?.data?.browser) || asString(e?.source) || "browser";
      const tabs = tabsRaw.filter((tab) => tab && typeof tab === "object") as Record<string, unknown>[];
      if (!tabs.length) continue;
      const weightedDur = dur / tabs.length;

      for (const tabObj of tabs) {
        const d = tabDomainFromTab(tabObj);
        totals.set(d, (totals.get(d) || 0) + weightedDur);

        const title = trimLabel(asString(tabObj.title) || asString(tabObj.url) || asString(tabObj.pending_url) || "untitled tab");
        const byTitle = titlesByDomain.get(d) || new Map<string, number>();
        byTitle.set(title, (byTitle.get(title) || 0) + weightedDur);
        titlesByDomain.set(d, byTitle);

        const byBrowser = browsersByDomain.get(d) || new Map<string, number>();
        byBrowser.set(browser, (byBrowser.get(browser) || 0) + weightedDur);
        browsersByDomain.set(d, byBrowser);
      }
    }

    const palette = ["#2dd4bf", "#60a5fa", "#a78bfa", "#f472b6", "#f59e0b", "#22c55e", "#fb7185", "#38bdf8"];
    return Array.from(totals.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)
      .map(([domain, seconds], idx) => ({
        id: domain,
        label: domain,
        seconds,
        color: palette[idx % palette.length],
        details: [
          {
            title: "Top tabs",
            items: buildTopDetailItems(titlesByDomain.get(domain) || new Map<string, number>(), 8),
            emptyText: "No tab titles available."
          },
          {
            title: "Browsers",
            items: buildTopDetailItems(browsersByDomain.get(domain) || new Map<string, number>(), 6),
            emptyText: "No browser data available."
          }
        ]
      }));
  }, [tabsEvents, windowRange]);

  const visibleRows = useMemo<VisibleRow[]>(() => {
    const rows: VisibleRow[] = [];
    for (const e of visibleEvents) {
      rows.push({
        start: e.start_ts,
        end: e.end_ts,
        app: asString(e?.data?.app),
        title: asString(e?.data?.title),
        workspace: asString(e?.data?.workspace),
        monitor: asString(e?.data?.monitor)
      });
    }
    rows.sort((a, b) => b.end.localeCompare(a.end));
    return rows.slice(0, 40);
  }, [visibleEvents]);

  const showTopic = (id: TopicId): boolean => {
    if (page === "dashboard") {
      return id === "overview" || id === "apps" || id === "categories";
    }
    return topic === "all" || topic === id;
  };

  const categoriesAppsSlices = (categories?.apps || []).map((r) => {
    const detail = categories?.app_details?.[r.category];
    const appItems = (detail?.top_apps || []).map((it) => ({
      label: trimLabel(it.name, 84),
      value: fmtSeconds(it.seconds)
    }));
    const titleItems = (detail?.top_titles || []).map((it) => ({
      label: trimLabel(it.name, 84),
      value: fmtSeconds(it.seconds)
    }));
    return {
      id: r.category,
      label: r.label,
      seconds: r.seconds,
      color: r.color,
      percent: r.percent,
      details: [
        { title: "Top apps", items: appItems, emptyText: "No apps for this category in current range." },
        { title: "Top windows", items: titleItems, emptyText: "No window titles for this category." }
      ]
    };
  });
  const categoriesTabsSlices = (categories?.tabs || []).map((r) => {
    const detail = categories?.tab_details?.[r.category];
    const domainItems = (detail?.top_domains || []).map((it) => ({
      label: trimLabel(it.name, 84),
      value: fmtSeconds(it.seconds)
    }));
    const titleItems = (detail?.top_titles || []).map((it) => ({
      label: trimLabel(it.name, 84),
      value: fmtSeconds(it.seconds)
    }));
    const browserItems = (detail?.top_browsers || []).map((it) => ({
      label: trimLabel(it.name, 84),
      value: fmtSeconds(it.seconds)
    }));
    return {
      id: r.category,
      label: r.label,
      seconds: r.seconds,
      color: r.color,
      percent: r.percent,
      details: [
        { title: "Top domains", items: domainItems, emptyText: "No tab domains for this category." },
        { title: "Top tabs", items: titleItems, emptyText: "No tab titles for this category." },
        { title: "Browsers", items: browserItems, emptyText: "No browser data for this category." }
      ]
    };
  });

  const appsCard = (
    <section className="card">
      <div className="cardHd">
        <h2>Top Apps ({summary?.top_apps_mode || "-"})</h2>
      </div>
      <div className="cardBd">
        <table>
          <thead>
            <tr>
              <th>App</th>
              <th>Time</th>
              <th>Share</th>
            </tr>
          </thead>
          <tbody>
            {topApps.map((a) => {
              const pct = a.percent_active ?? a.percent_window ?? 0;
              return (
                <tr key={a.app}>
                  <td>{a.app}</td>
                  <td>{fmtSeconds(a.seconds || 0)}</td>
                  <td>
                    <div className="shareCell">
                      <div className="inlineBarTrack">
                        <div className="inlineBarFill" style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} />
                      </div>
                      <span className="inlineBarPct">{fmtPct(pct)}</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );

  const categoriesCard = (
    <section className="card">
      <div className="cardHd">
        <h2>Categories</h2>
      </div>
      <div className="cardBd split2">
        <div>
          <h3>Apps ({categories?.mode || "auto"})</h3>
          <DonutChart rows={categoriesAppsSlices} total={categories?.apps_total_seconds || 0} title="apps categories" />
        </div>
        <div>
          <h3>Tabs</h3>
          <DonutChart rows={categoriesTabsSlices} total={categories?.tabs_total_seconds || 0} title="tabs categories" />
        </div>
      </div>
    </section>
  );

  const statusTone = error ? "isError" : loading ? "isLoading" : "isOk";
  const statusBadge = loading ? "syncing" : error ? "degraded" : "healthy";

  return (
    <main className={`page page-${page}`}>
      <header className="header">
        <div>
          <div className="brandLine">
            <h1>Activewatcher</h1>
            <div className="navLinks">
              <a href={hrefFor("dashboard")} className={page === "dashboard" ? "pill active" : "pill"}>
                dashboard
              </a>
              <a href={hrefFor("stats")} className={page === "stats" ? "pill active" : "pill"}>
                stats
              </a>
            </div>
          </div>
          <div className="sub">
            {windowRange ? `range: ${range} · ${fmtTs(windowRange.from)} → ${fmtTs(windowRange.to)}` : `range: ${range}`}
          </div>
        </div>

        <div className="controls">
          {RANGES.map((r) => (
            <button key={r.key} className={r.key === range ? "pill active" : "pill"} onClick={() => onRangeChange(r.key)}>
              {r.label}
            </button>
          ))}
          <button className="pill" onClick={() => setReloadKey((v) => v + 1)}>
            refresh
          </button>
        </div>
      </header>

      {page === "stats" ? (
        <div className="subnav">
          {TOPICS.map((t) => (
            <button
              key={t.id}
              className={topic === t.id ? "pill active" : "pill"}
              onClick={() => onTopicChange(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>
      ) : null}

      <section className={`card statusCard ${statusTone}`}>
        <div className="sub statusLine">
          <span className="statusBadge">{statusBadge}</span>
          <span>{updatedAt ? `updated ${updatedAt}` : loading ? "fetching data..." : "waiting for first refresh"}</span>
          <span className={error ? "statusIssue" : "statusHealthy"}>
            {error ? `partial errors: ${error}` : "all data sources reachable"}
          </span>
        </div>
      </section>

      {showTopic("overview") ? (
        <section className="card">
          <div className="cardHd">
            <h2>Overview</h2>
          </div>
          <div className="cardBd">
            <div className="kpiGrid">
              <div className="kpi">
                <span>Active</span>
                <strong>{fmtSecondsShort(summary?.active_seconds || 0)}</strong>
              </div>
              <div className="kpi">
                <span>AFK</span>
                <strong>{fmtSecondsShort(summary?.afk_seconds || 0)}</strong>
              </div>
              <div className="kpi">
                <span>Off</span>
                <strong>{fmtSecondsShort(summary?.unknown_seconds || 0)}</strong>
              </div>
              <div className="kpi">
                <span>Total</span>
                <strong>{fmtSecondsShort(summary?.total_seconds || 0)}</strong>
              </div>
            </div>

            <div className="split2" style={{ marginTop: 12 }}>
              <div>
                <h3>Activity Share</h3>
                <DonutChart rows={activitySlices} total={summary?.total_seconds || 0} title="activity share" />
              </div>
              <div>
                <h3>Timeline</h3>
                <LegacyTimeline
                  chunks={summary?.timeline_chunks || []}
                  range={range}
                  fromTs={summary?.from_ts || windowRange?.from || ""}
                  toTs={summary?.to_ts || windowRange?.to || ""}
                />
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {page === "dashboard" && showTopic("apps") && showTopic("categories") ? (
        <div className="dashboardTopRow">
          {appsCard}
          {categoriesCard}
        </div>
      ) : (
        <>
          {showTopic("apps") ? appsCard : null}
          {showTopic("categories") ? categoriesCard : null}
        </>
      )}

      {page === "stats" && showTopic("websites") ? (
        <section className="card">
          <div className="cardHd">
            <h2>Websites</h2>
          </div>
          <div className="cardBd split2">
            <div>
              <h3>Top by Time</h3>
              <HorizontalBars
                rows={websites.slice(0, 15).map((r) => ({
                  id: r.site,
                  label: r.site,
                  value: r.seconds,
                  sub: `${r.visits} visits`
                }))}
                valueFormatter={(v) => fmtSeconds(v)}
              />
            </div>
            <div>
              <h3>Details</h3>
              <table>
                <thead>
                  <tr>
                    <th>Site</th>
                    <th>Time</th>
                    <th>Visits</th>
                    <th>Last</th>
                  </tr>
                </thead>
                <tbody>
                  {websites.slice(0, 20).map((r) => (
                    <tr key={r.site}>
                      <td>{r.site}</td>
                      <td>{fmtSeconds(r.seconds)}</td>
                      <td>{r.visits}</td>
                      <td>{fmtTs(r.lastTs)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      ) : null}

      {page === "stats" && showTopic("workspaces") ? (
        <section className="card">
          <div className="cardHd">
            <h2>Workspaces</h2>
          </div>
          <div className="cardBd workspaceStack">
            <div className="wsFilterRow">
              <span className="wsFilterLabel">monitor setup</span>
              <div className="wsFilterGroup">
                {MONITOR_SETUP_FILTERS.map((f) => (
                  <button
                    key={f.key}
                    type="button"
                    className={monitorSetupFilter === f.key ? "pill active" : "pill"}
                    onClick={() => setMonitorSetupFilter(f.key)}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
              <span className="sub wsFilterMeta">
                switches:{" "}
                {monitorSetupFilter === "all"
                  ? workspaceSwitchEvents.length
                  : `${workspaceSwitchEventsFiltered.length}/${workspaceSwitchEvents.length}`}
              </span>
            </div>
            <div>
              <h3>Workspace Heatmap</h3>
              <WorkspaceHeatmap
                labels={workspaceInsights.heatmapLabels}
                rows={workspaceInsights.heatmapRows}
                maxCellSeconds={workspaceInsights.heatmapMaxCellSeconds}
              />
              <div className="sub">bin size: {workspaceInsights.heatmapBinSize || "-"} · top 12 workspaces by time</div>
            </div>
            <div className="split2">
              <div>
                <h3>Workspace Share</h3>
                <DonutChart rows={workspaceInsights.shareSlices} total={workspaceInsights.totalSeconds} title="workspace share" />
              </div>
              <div>
                <h3>Switches Over Time</h3>
                <MiniLineChart points={workspaceInsights.switchSeries} />
                <div className="sub" style={{ marginTop: 7 }}>
                  total switches: {workspaceInsights.switchCount}
                </div>
              </div>
            </div>
            <div className="split2">
              <div>
                <h3>Workspace Time</h3>
                <HorizontalBars rows={workspaceInsights.timeRows} valueFormatter={(v) => fmtSeconds(v)} />
              </div>
              <div>
                <h3>Workspace Transitions</h3>
                <WorkspaceTransitionMatrixView matrix={workspaceTransitionMatrix} />
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {page === "stats" && showTopic("monitors") ? (
        <section className="card">
          <div className="cardHd">
            <h2>Monitor Stats</h2>
          </div>
          <div className="cardBd workspaceStack">
            <div className="wsFilterRow">
              <span className="wsFilterLabel">monitor setup</span>
              <div className="wsFilterGroup">
                {MONITOR_SETUP_FILTERS.map((f) => (
                  <button
                    key={`monitor-stats-${f.key}`}
                    type="button"
                    className={monitorSetupFilter === f.key ? "pill active" : "pill"}
                    onClick={() => setMonitorSetupFilter(f.key)}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
              <span className="sub wsFilterMeta">
                samples:{" "}
                {monitorSetupFilter === "all"
                  ? workspaceEvents.length
                  : `${workspaceEventsFiltered.length}/${workspaceEvents.length}`}
              </span>
            </div>

            <div className="split2">
              <div>
                <h3>Single vs Multi</h3>
                <DonutChart rows={monitorInsights.setupSlices} total={monitorInsights.totalSeconds} title="monitor setup share" />
              </div>
              <div>
                <h3>Monitor Count Over Time</h3>
                <MiniLineChart points={monitorInsights.countSeries} />
                <div className="sub" style={{ marginTop: 7 }}>
                  avg monitors: {Math.round(monitorInsights.avgCount * 100) / 100} · peak:{" "}
                  {Math.round(monitorInsights.peakCount * 100) / 100}
                </div>
              </div>
            </div>

            <div>
              <h3>Connected Monitors Heatmap</h3>
              <WorkspaceHeatmap
                labels={monitorInsights.heatmapLabels}
                rows={monitorInsights.heatmapRows}
                maxCellSeconds={monitorInsights.heatmapMaxCellSeconds}
              />
              <div className="sub">bin size: {monitorInsights.heatmapBinSize || "-"} · rows show connected monitor names</div>
            </div>

            <div className="split2">
              <div>
                <h3>Top Monitor Setups</h3>
                <HorizontalBars rows={monitorInsights.setupRows} valueFormatter={(v) => fmtSeconds(v)} />
              </div>
              <div>
                <h3>Connected When</h3>
                {monitorInsights.monitorPeriods.length ? (
                  <table className="monitorPeriodsTable">
                    <thead>
                      <tr>
                        <th>Monitor</th>
                        <th>Start</th>
                        <th>End</th>
                        <th>Duration</th>
                        <th>Setup</th>
                        <th>Max Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {monitorInsights.monitorPeriods.map((p, idx) => (
                        <tr key={`${p.monitor}-${p.start}-${p.signature}-${idx}`}>
                          <td className="monitorPeriodMonitors">{p.monitor}</td>
                          <td>{fmtTs(p.start)}</td>
                          <td>{fmtTs(p.end)}</td>
                          <td>{fmtSeconds(p.durationSeconds)}</td>
                          <td>
                            <span className={`monitorSetupBadge ${p.setup}`}>{monitorSetupLabel(p.setup)}</span>
                          </td>
                          <td>
                            <span className="monitorCountValue">{p.maxMonitorCount > 0 ? p.maxMonitorCount : "-"}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="empty">No monitor setup periods.</div>
                )}
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {page === "stats" && showTopic("tabs") ? (
        <section className="card">
          <div className="cardHd">
            <h2>Browser Tabs</h2>
          </div>
          <div className="cardBd split2">
            <div>
              <h3>Open Tabs Over Time</h3>
              <MiniLineChart points={tabsCountSeries} />
            </div>
            <div>
              <h3>Tab Domains</h3>
              <DonutChart
                rows={tabDomainSlices}
                total={tabDomainSlices.reduce((sum, r) => sum + r.seconds, 0)}
                title="tab domains"
              />
            </div>
          </div>
        </section>
      ) : null}

      {page === "stats" && showTopic("logs") ? (
        <section className="card">
          <div className="cardHd">
            <h2>Latest Visible Windows</h2>
          </div>
          <div className="cardBd">
            <table>
              <thead>
                <tr>
                  <th>Start</th>
                  <th>End</th>
                  <th>App</th>
                  <th>Title</th>
                  <th>WS</th>
                  <th>Mon</th>
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((r, idx) => (
                  <tr key={`${r.end}-${idx}`}>
                    <td>{fmtTs(r.start)}</td>
                    <td>{fmtTs(r.end)}</td>
                    <td>{r.app}</td>
                    <td>{r.title}</td>
                    <td>{r.workspace}</td>
                    <td>{r.monitor}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </main>
  );
}
