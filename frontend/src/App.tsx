import { Fragment, type MouseEvent, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

type RangeKey = "24h" | "1w" | "1m" | "all";
type TopicId =
  | "all"
  | "overview"
  | "apps"
  | "categories"
  | "mixed"
  | "websites"
  | "workspaces"
  | "monitors"
  | "system"
  | "tabs"
  | "logs";
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

type AppCoOccurrenceMatrix = {
  activeApps: string[];
  visibleApps: string[];
  seconds: number[][];
  rowTotals: number[];
  colTotals: number[];
  maxCellSeconds: number;
  totalSeconds: number;
  topPairs: Array<{ activeApp: string; visibleApp: string; seconds: number; sharePct: number }>;
};

type DailyMonitorSplitRow = {
  id: string;
  label: string;
  singleSeconds: number;
  multiSeconds: number;
  unknownSeconds: number;
  visibleWindowSeconds: number;
  openAppSeconds: number;
  totalSeconds: number;
};

type AppFlowEdge = {
  id: string;
  from: string;
  to: string;
  count: number;
  sharePct: number;
  topWorkspacePath: string;
};

type MixedCategory = "work" | "communication" | "research" | "entertainment" | "other";

type CategoryTransitionMatrix = {
  labels: MixedCategory[];
  counts: number[][];
  rowTotals: number[];
  colTotals: number[];
  maxCell: number;
  total: number;
  topTransitions: Array<{ from: MixedCategory; to: MixedCategory; count: number; rowProbPct: number; sharePct: number }>;
};

type WorkspaceUsageOverlayRow = {
  id: string;
  label: string;
  seconds: number;
  switches: number;
  switchesPerHour: number;
};

type ProductivityPulseBin = {
  id: string;
  label: string;
  startMs: number;
  endMs: number;
  workSeconds: number;
  communicationSeconds: number;
  distractionSeconds: number;
  otherSeconds: number;
  afkSeconds: number;
};

type HexbinDensityPoint = {
  id: string;
  tabsCount: number;
  visibleWindows: number;
  cpuPercent: number;
  ramPercent: number;
  category: MixedCategory;
};

type HexbinDensityCell = {
  id: string;
  tabsBin: number;
  windowsBin: number;
  samples: number;
  medianCpu: number;
  medianRam: number;
};

type HexbinDensityMatrix = {
  cells: HexbinDensityCell[];
  xBins: number[];
  yBins: number[];
  maxSamples: number;
};

type TriGraphNodeType = "app" | "domain" | "workspace";
type TriGraphEdgeKind = "app-domain" | "domain-workspace" | "app-workspace";

type TriGraphNode = {
  id: string;
  type: TriGraphNodeType;
  raw: string;
  label: string;
  weight: number;
};

type TriGraphEdge = {
  id: string;
  kind: TriGraphEdgeKind;
  from: string;
  to: string;
  weight: number;
};

type TriGraphData = {
  appNodes: TriGraphNode[];
  domainNodes: TriGraphNode[];
  workspaceNodes: TriGraphNode[];
  edges: TriGraphEdge[];
  maxEdgeWeight: number;
};

type WorkspaceEntropyRow = {
  id: string;
  label: string;
  totalSeconds: number;
  appCount: number;
  entropyBits: number;
  normalizedEntropy: number;
  switches: number;
  switchesPerHour: number;
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
  { id: "mixed", label: "gemischt" },
  { id: "websites", label: "websites" },
  { id: "workspaces", label: "workspaces" },
  { id: "monitors", label: "monitors" },
  { id: "system", label: "system" },
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
    s === "mixed" ||
    s === "websites" ||
    s === "workspaces" ||
    s === "monitors" ||
    s === "system" ||
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

function fmtBytes(bytes: number): string {
  const v = Math.max(0, Number(bytes) || 0);
  if (v >= 1024 ** 4) return `${Math.round((v / 1024 ** 4) * 100) / 100} TiB`;
  if (v >= 1024 ** 3) return `${Math.round((v / 1024 ** 3) * 100) / 100} GiB`;
  if (v >= 1024 ** 2) return `${Math.round((v / 1024 ** 2) * 100) / 100} MiB`;
  if (v >= 1024) return `${Math.round((v / 1024) * 100) / 100} KiB`;
  return `${Math.round(v)} B`;
}

function bpsToMbps(bps: number): number {
  const v = Math.max(0, Number(bps) || 0);
  return (v * 8) / 1_000_000;
}

function fmtMbps(mbps: number): string {
  const v = Math.max(0, Number(mbps) || 0);
  if (v >= 1000) return `${Math.round((v / 1000) * 100) / 100} Gbps`;
  return `${Math.round(v * 100) / 100} Mbps`;
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

const MIXED_CATEGORY_ORDER: MixedCategory[] = ["work", "communication", "research", "entertainment", "other"];

function mixedCategoryLabel(category: MixedCategory): string {
  if (category === "work") return "Work";
  if (category === "communication") return "Communication";
  if (category === "research") return "Research";
  if (category === "entertainment") return "Entertainment";
  return "Other";
}

function mixedCategoryColor(category: MixedCategory): string {
  if (category === "work") return "rgba(45, 212, 191, 0.9)";
  if (category === "communication") return "rgba(96, 165, 250, 0.9)";
  if (category === "research") return "rgba(168, 85, 247, 0.88)";
  if (category === "entertainment") return "rgba(250, 204, 21, 0.92)";
  return "rgba(148, 163, 184, 0.82)";
}

function pulseColor(kind: "work" | "communication" | "distraction" | "other" | "afk"): string {
  if (kind === "work") return "rgba(45, 212, 191, 0.88)";
  if (kind === "communication") return "rgba(96, 165, 250, 0.9)";
  if (kind === "distraction") return "rgba(250, 204, 21, 0.9)";
  if (kind === "afk") return "rgba(148, 163, 184, 0.78)";
  return "rgba(167, 139, 250, 0.84)";
}

const COMM_HINTS = [
  "slack",
  "discord",
  "teams",
  "zoom",
  "telegram",
  "whatsapp",
  "signal",
  "thunderbird",
  "outlook",
  "mail",
  "meet",
  "calendar"
];
const WORK_HINTS = [
  "code",
  "codium",
  "jetbrains",
  "idea",
  "pycharm",
  "webstorm",
  "goland",
  "terminal",
  "alacritty",
  "kitty",
  "wezterm",
  "zsh",
  "bash",
  "fish",
  "nvim",
  "neovim",
  "vim",
  "emacs",
  "notion",
  "obsidian",
  "overleaf",
  "figma",
  "jira",
  "confluence"
];
const RESEARCH_HINTS = ["arxiv", "scholar", "wikipedia", "paper", "docs", "readthedocs", "stack", "pubmed", "ilias"];
const ENTERTAINMENT_HINTS = [
  "youtube",
  "netflix",
  "twitch",
  "reddit",
  "x.com",
  "twitter",
  "instagram",
  "tiktok",
  "spotify",
  "steam",
  "prime video",
  "disney+",
  "music"
];

function includesAny(haystack: string, needles: string[]): boolean {
  const h = String(haystack || "").toLowerCase();
  return needles.some((needle) => h.includes(needle));
}

function classifyDomainCategory(domain: string): MixedCategory {
  const d = normalizeHost(domain);
  if (!d) return "other";
  if (includesAny(d, ["slack", "discord", "teams", "zoom", "meet.google", "mail.google", "outlook", "calendar.google", "whatsapp"])) {
    return "communication";
  }
  if (includesAny(d, ["youtube", "youtu", "netflix", "twitch", "reddit", "x.com", "twitter", "instagram", "tiktok", "spotify"])) {
    return "entertainment";
  }
  if (includesAny(d, ["arxiv", "wikipedia", "readthedocs", "docs", "stackoverflow", "scholar", "ilias", ".edu"])) {
    return "research";
  }
  if (includesAny(d, ["github", "gitlab", "atlassian", "notion", "figma", "linear", "vercel", "npmjs"])) {
    return "work";
  }
  return "other";
}

function classifyActiveCategory(
  app: string,
  title: string,
  browserDomainHint?: string | null
): MixedCategory {
  const a = String(app || "").toLowerCase();
  const t = String(title || "").toLowerCase();
  const combo = `${a} ${t}`;

  if (includesAny(combo, COMM_HINTS)) return "communication";
  if (includesAny(combo, WORK_HINTS)) return "work";
  if (includesAny(combo, RESEARCH_HINTS)) return "research";
  if (includesAny(combo, ENTERTAINMENT_HINTS)) return "entertainment";

  if (isBrowserApp(app)) {
    const domainFromTitle = extractHostFromTitle(title);
    const chosenDomain = browserDomainHint || domainFromTitle || "";
    const dc = classifyDomainCategory(chosenDomain);
    if (dc !== "other") return dc;
  }

  return "other";
}

function mixedToPulseCategory(category: MixedCategory): "work" | "communication" | "distraction" | "other" {
  if (category === "communication") return "communication";
  if (category === "entertainment") return "distraction";
  if (category === "research" || category === "work") return "work";
  return "other";
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

function overlapSeconds(startA: number, endA: number, startB: number, endB: number): number {
  const s = Math.max(startA, startB);
  const e = Math.min(endA, endB);
  return e > s ? (e - s) / 1000 : 0;
}

function median(values: number[]): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) {
    return (sorted[mid - 1] + sorted[mid]) / 2;
  }
  return sorted[mid];
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

function DonutChart({
  rows,
  total,
  title,
  showCenterValue = true
}: {
  rows: SliceRow[];
  total: number;
  title: string;
  showCenterValue?: boolean;
}) {
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
        {showCenterValue ? (
          <text x="21" y="21" textAnchor="middle" dominantBaseline="middle" className="donutText">
            {total > 0 ? fmtSecondsShort(total) : "-"}
          </text>
        ) : null}
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

function AppCoOccurrenceMatrixView({ matrix }: { matrix: AppCoOccurrenceMatrix }) {
  const [hovered, setHovered] = useState<HoverTooltip | null>(null);
  const { activeApps, visibleApps, seconds, rowTotals, colTotals, maxCellSeconds, totalSeconds } = matrix;

  const updateHover = (e: MouseEvent<HTMLDivElement>, label: string, meta?: string) => {
    const p = tooltipPoint(e);
    setHovered({ x: p.x, y: p.y, label, meta });
  };

  if (!activeApps.length || !visibleApps.length || totalSeconds <= 0) {
    return <div className="empty">No co-occurrence data in this range.</div>;
  }

  const cols = `minmax(130px,auto) repeat(${visibleApps.length}, minmax(28px,1fr)) minmax(66px,auto)`;
  return (
    <div className="wsMatrixWrap">
      <div className="wsMatrixNote sub">rows: active app · columns: visible app · overlap total: {fmtSeconds(totalSeconds)}</div>
      <div className="wsMatrixScroll">
        <div className="wsMatrixGrid" style={{ gridTemplateColumns: cols }}>
          <div className="wsMatrixCorner">active \ visible</div>
          {visibleApps.map((app) => (
            <div key={`co-head-${app}`} className="wsMatrixHead">
              {trimLabel(app, 14)}
            </div>
          ))}
          <div className="wsMatrixHead wsMatrixHeadTotal">row</div>

          {activeApps.map((activeApp, i) => (
            <Fragment key={`co-row-${activeApp}`}>
              <div
                className="wsMatrixRowLabel"
                onMouseEnter={(e) => updateHover(e, activeApp, `visible overlap: ${fmtSeconds(rowTotals[i] || 0)}`)}
                onMouseMove={(e) => updateHover(e, activeApp, `visible overlap: ${fmtSeconds(rowTotals[i] || 0)}`)}
                onMouseLeave={() => setHovered(null)}
              >
                <span className="wsTransitionTag">{trimLabel(activeApp, 26)}</span>
              </div>
              {visibleApps.map((visibleApp, j) => {
                const v = seconds[i]?.[j] || 0;
                const ratio = maxCellSeconds > 0 ? Math.max(0, Math.min(1, v / maxCellSeconds)) : 0;
                return (
                  <div
                    key={`co-cell-${activeApp}-${visibleApp}`}
                    className={`wsMatrixCell ${v > 0 ? "active" : ""}`}
                    style={{ background: workspaceHeatColor(ratio) }}
                    onMouseEnter={(e) =>
                      updateHover(
                        e,
                        `${trimLabel(activeApp, 32)} + ${trimLabel(visibleApp, 32)}`,
                        `${fmtSeconds(v)}${rowTotals[i] > 0 ? ` · ${fmtPct((v / rowTotals[i]) * 100)} of row` : ""}`
                      )
                    }
                    onMouseMove={(e) =>
                      updateHover(
                        e,
                        `${trimLabel(activeApp, 32)} + ${trimLabel(visibleApp, 32)}`,
                        `${fmtSeconds(v)}${rowTotals[i] > 0 ? ` · ${fmtPct((v / rowTotals[i]) * 100)} of row` : ""}`
                      )
                    }
                    onMouseLeave={() => setHovered(null)}
                  >
                    {v > 0 ? <span className="wsMatrixCellText">{fmtSecondsShort(v)}</span> : <span className="wsMatrixCellDot" />}
                  </div>
                );
              })}
              <div className="wsMatrixRowTotal">{fmtSecondsShort(rowTotals[i] || 0)}</div>
            </Fragment>
          ))}

          <div className="wsMatrixFooterLabel">col</div>
          {colTotals.map((v, idx) => (
            <div key={`co-col-total-${visibleApps[idx]}`} className="wsMatrixColTotal">
              {fmtSecondsShort(v || 0)}
            </div>
          ))}
          <div className="wsMatrixFooterTotal">{fmtSecondsShort(totalSeconds)}</div>
        </div>
      </div>
      <TooltipPortal tooltip={hovered} />
    </div>
  );
}

function DailyMonitorSplitView({ rows }: { rows: DailyMonitorSplitRow[] }) {
  const [hovered, setHovered] = useState<HoverTooltip | null>(null);
  if (!rows.length) return <div className="empty">No monitor split data.</div>;
  const maxTotal = rows.reduce((m, r) => Math.max(m, r.totalSeconds), 0);

  const updateHover = (e: MouseEvent<HTMLDivElement>, label: string, meta?: string) => {
    const p = tooltipPoint(e);
    setHovered({ x: p.x, y: p.y, label, meta });
  };

  return (
    <div className="mixedStackWrap">
      {rows.map((row) => {
        const total = Math.max(1, row.totalSeconds);
        const singlePct = (row.singleSeconds / total) * 100;
        const multiPct = (row.multiSeconds / total) * 100;
        const unknownPct = Math.max(0, 100 - singlePct - multiPct);
        const scalePct = maxTotal > 0 ? (row.totalSeconds / maxTotal) * 100 : 0;
        const avgVisible = row.totalSeconds > 0 ? row.visibleWindowSeconds / row.totalSeconds : 0;
        const avgOpen = row.totalSeconds > 0 ? row.openAppSeconds / row.totalSeconds : 0;

        return (
          <div key={row.id} className="mixedStackRow">
            <div className="mixedStackLabel">{row.label}</div>
            <div className="mixedStackTrack">
              <div className="mixedStackScale" style={{ width: `${Math.max(3, scalePct)}%` }}>
                <div
                  className="mixedStackSeg single"
                  style={{ width: `${singlePct}%` }}
                  onMouseEnter={(e) => updateHover(e, `${row.label} · single`, fmtSeconds(row.singleSeconds))}
                  onMouseMove={(e) => updateHover(e, `${row.label} · single`, fmtSeconds(row.singleSeconds))}
                  onMouseLeave={() => setHovered(null)}
                />
                <div
                  className="mixedStackSeg multi"
                  style={{ width: `${multiPct}%` }}
                  onMouseEnter={(e) => updateHover(e, `${row.label} · multi`, fmtSeconds(row.multiSeconds))}
                  onMouseMove={(e) => updateHover(e, `${row.label} · multi`, fmtSeconds(row.multiSeconds))}
                  onMouseLeave={() => setHovered(null)}
                />
                <div
                  className="mixedStackSeg unknown"
                  style={{ width: `${unknownPct}%` }}
                  onMouseEnter={(e) => updateHover(e, `${row.label} · unknown`, fmtSeconds(row.unknownSeconds))}
                  onMouseMove={(e) => updateHover(e, `${row.label} · unknown`, fmtSeconds(row.unknownSeconds))}
                  onMouseLeave={() => setHovered(null)}
                />
              </div>
            </div>
            <div className="mixedStackMeta">
              {fmtSecondsShort(row.totalSeconds)} · vis {Math.round(avgVisible * 100) / 100} · apps {Math.round(avgOpen * 100) / 100}
            </div>
          </div>
        );
      })}
      <div className="sub">bar width = total tracked time per day · colors = single/multi/unknown monitor share</div>
      <TooltipPortal tooltip={hovered} />
    </div>
  );
}

function AppFlowTopView({ edges }: { edges: AppFlowEdge[] }) {
  if (!edges.length) return <div className="empty">No app-to-app transitions in this range.</div>;
  const maxCount = edges.reduce((m, e) => Math.max(m, e.count), 0);
  return (
    <div className="barList">
      {edges.map((edge) => {
        const w = maxCount > 0 ? (edge.count / maxCount) * 100 : 0;
        return (
          <div key={edge.id} className="barRow">
            <div className="barLabel">
              {trimLabel(edge.from, 16)} <span className="barSub">→ {trimLabel(edge.to, 16)}</span>
            </div>
            <div className="barTrack">
              <div className="barFill" style={{ width: `${w}%`, background: "linear-gradient(90deg,#60a5fa,#22d3ee)" }} />
            </div>
            <div className="barValue">
              {edge.count} · {fmtPct(edge.sharePct)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function CategoryTransitionMatrixView({ matrix }: { matrix: CategoryTransitionMatrix }) {
  const [hovered, setHovered] = useState<HoverTooltip | null>(null);
  const { labels, counts, rowTotals, colTotals, maxCell, total } = matrix;
  const updateHover = (e: MouseEvent<HTMLDivElement>, label: string, meta?: string) => {
    const p = tooltipPoint(e);
    setHovered({ x: p.x, y: p.y, label, meta });
  };
  if (!labels.length || total <= 0) return <div className="empty">No category transition data.</div>;

  const cols = `minmax(116px,auto) repeat(${labels.length}, minmax(32px,1fr)) minmax(72px,auto)`;
  return (
    <div className="wsMatrixWrap">
      <div className="wsMatrixNote sub">rows: from category · columns: to category · transitions: {total}</div>
      <div className="wsMatrixScroll">
        <div className="wsMatrixGrid" style={{ gridTemplateColumns: cols }}>
          <div className="wsMatrixCorner">from \ to</div>
          {labels.map((c) => (
            <div key={`markov-h-${c}`} className="wsMatrixHead">
              {mixedCategoryLabel(c)}
            </div>
          ))}
          <div className="wsMatrixHead wsMatrixHeadTotal">out</div>

          {labels.map((from, i) => (
            <Fragment key={`markov-row-${from}`}>
              <div
                className="wsMatrixRowLabel"
                onMouseEnter={(e) => updateHover(e, mixedCategoryLabel(from), `${rowTotals[i] || 0} outgoing transitions`)}
                onMouseMove={(e) => updateHover(e, mixedCategoryLabel(from), `${rowTotals[i] || 0} outgoing transitions`)}
                onMouseLeave={() => setHovered(null)}
              >
                <span
                  className="wsTransitionTag"
                  style={{
                    background: `${mixedCategoryColor(from).replace("0.9", "0.18").replace("0.88", "0.18").replace("0.92", "0.2")}`,
                    borderColor: mixedCategoryColor(from),
                    color: "var(--ink)"
                  }}
                >
                  {mixedCategoryLabel(from)}
                </span>
              </div>
              {labels.map((to, j) => {
                const count = counts[i]?.[j] || 0;
                const ratio = maxCell > 0 ? Math.max(0, Math.min(1, count / maxCell)) : 0;
                const rowProb = rowTotals[i] > 0 ? (count / rowTotals[i]) * 100 : 0;
                return (
                  <div
                    key={`markov-cell-${from}-${to}`}
                    className={`wsMatrixCell ${count > 0 ? "active" : ""}`}
                    style={{ background: workspaceHeatColor(ratio) }}
                    onMouseEnter={(e) =>
                      updateHover(
                        e,
                        `${mixedCategoryLabel(from)} → ${mixedCategoryLabel(to)}`,
                        `${count} transitions · ${fmtPct(rowProb)} row-prob`
                      )
                    }
                    onMouseMove={(e) =>
                      updateHover(
                        e,
                        `${mixedCategoryLabel(from)} → ${mixedCategoryLabel(to)}`,
                        `${count} transitions · ${fmtPct(rowProb)} row-prob`
                      )
                    }
                    onMouseLeave={() => setHovered(null)}
                  >
                    {count > 0 ? <span className="wsMatrixCellText">{count}</span> : <span className="wsMatrixCellDot" />}
                  </div>
                );
              })}
              <div className="wsMatrixRowTotal">{rowTotals[i] || 0}</div>
            </Fragment>
          ))}

          <div className="wsMatrixFooterLabel">in</div>
          {colTotals.map((v, idx) => (
            <div key={`markov-col-total-${labels[idx]}`} className="wsMatrixColTotal">
              {v}
            </div>
          ))}
          <div className="wsMatrixFooterTotal">{total}</div>
        </div>
      </div>
      <TooltipPortal tooltip={hovered} />
    </div>
  );
}

function WorkspaceUsageOverlayView({ rows }: { rows: WorkspaceUsageOverlayRow[] }) {
  if (!rows.length) return <div className="empty">No workspace usage rows.</div>;
  const maxTime = rows.reduce((m, r) => Math.max(m, r.seconds), 0);
  const maxSwitches = rows.reduce((m, r) => Math.max(m, r.switches), 0);
  return (
    <div className="barList">
      {rows.map((row) => {
        const timeW = maxTime > 0 ? (row.seconds / maxTime) * 100 : 0;
        const switchW = maxSwitches > 0 ? (row.switches / maxSwitches) * 100 : 0;
        return (
          <div key={row.id} className="barRow">
            <div className="barLabel">
              {row.label}
              <span className="barSub">{row.switches} switches · {Math.round(row.switchesPerHour * 100) / 100}/h</span>
            </div>
            <div className="mixedUsageTrack">
              <div className="mixedUsageTime" style={{ width: `${timeW}%` }} />
              <div className="mixedUsageSwitch" style={{ width: `${switchW}%` }} />
            </div>
            <div className="barValue">{fmtSeconds(row.seconds)}</div>
          </div>
        );
      })}
      <div className="sub">cyan = time share · yellow overlay = switch intensity</div>
    </div>
  );
}

function ProductivityPulseView({ bins }: { bins: ProductivityPulseBin[] }) {
  const [hovered, setHovered] = useState<HoverTooltip | null>(null);
  if (!bins.length) return <div className="empty">No productivity pulse data.</div>;
  const showEvery = Math.max(1, Math.floor(bins.length / 12));

  const updateHover = (e: MouseEvent<HTMLDivElement>, bin: ProductivityPulseBin) => {
    const p = tooltipPoint(e);
    const duration = Math.max(1, (bin.endMs - bin.startMs) / 1000);
    setHovered({
      x: p.x,
      y: p.y,
      label: `${fmtTs(new Date(bin.startMs).toISOString())} → ${fmtTs(new Date(bin.endMs).toISOString())}`,
      meta: `work ${fmtPct((bin.workSeconds / duration) * 100)} · comm ${fmtPct((bin.communicationSeconds / duration) * 100)} · distract ${fmtPct((bin.distractionSeconds / duration) * 100)} · afk ${fmtPct((bin.afkSeconds / duration) * 100)}`
    });
  };

  return (
    <div className="pulseWrap">
      <div className="pulseLegend">
        <span><span className="legendDotLegacy" style={{ background: pulseColor("work") }} />Work</span>
        <span><span className="legendDotLegacy" style={{ background: pulseColor("communication") }} />Communication</span>
        <span><span className="legendDotLegacy" style={{ background: pulseColor("distraction") }} />Distraction</span>
        <span><span className="legendDotLegacy" style={{ background: pulseColor("other") }} />Other</span>
        <span><span className="legendDotLegacy" style={{ background: pulseColor("afk") }} />AFK</span>
      </div>
      <div className="pulseBars">
        {bins.map((bin) => {
          const duration = Math.max(1, (bin.endMs - bin.startMs) / 1000);
          const workPct = Math.max(0, Math.min(100, (bin.workSeconds / duration) * 100));
          const commPct = Math.max(0, Math.min(100, (bin.communicationSeconds / duration) * 100));
          const distractPct = Math.max(0, Math.min(100, (bin.distractionSeconds / duration) * 100));
          const otherPct = Math.max(0, Math.min(100, (bin.otherSeconds / duration) * 100));
          const afkPct = Math.max(0, Math.min(100, (bin.afkSeconds / duration) * 100));
          return (
            <div
              key={bin.id}
              className="pulseBarCol"
              onMouseEnter={(e) => updateHover(e, bin)}
              onMouseMove={(e) => updateHover(e, bin)}
              onMouseLeave={() => setHovered(null)}
            >
              <div className="pulseSeg work" style={{ height: `${workPct}%` }} />
              <div className="pulseSeg communication" style={{ height: `${commPct}%` }} />
              <div className="pulseSeg distraction" style={{ height: `${distractPct}%` }} />
              <div className="pulseSeg other" style={{ height: `${otherPct}%` }} />
              <div className="pulseSeg afk" style={{ height: `${afkPct}%` }} />
            </div>
          );
        })}
      </div>
      <div className="pulseLabels">
        {bins.map((bin, idx) => (
          <span key={`pulse-l-${bin.id}`}>{idx % showEvery === 0 || idx === bins.length - 1 ? bin.label : ""}</span>
        ))}
      </div>
      <TooltipPortal tooltip={hovered} />
    </div>
  );
}

function HexbinDensityView({
  matrix,
  metric
}: {
  matrix: HexbinDensityMatrix;
  metric: "cpu" | "ram";
}) {
  const [hovered, setHovered] = useState<HoverTooltip | null>(null);
  const { cells, xBins, yBins, maxSamples } = matrix;
  if (!cells.length || !xBins.length || !yBins.length) {
    return <div className="empty">No 2D density samples for the current filter.</div>;
  }

  const rows = [...yBins].sort((a, b) => b - a);
  const cellMap = new Map(cells.map((c) => [`${c.tabsBin}|${c.windowsBin}`, c]));
  const maxMetric = cells.reduce((m, c) => Math.max(m, metric === "cpu" ? c.medianCpu : c.medianRam), 0);
  const cols = `minmax(98px,auto) repeat(${xBins.length}, minmax(30px,1fr))`;

  const updateHover = (e: MouseEvent<HTMLDivElement>, cell: HexbinDensityCell) => {
    const p = tooltipPoint(e);
    const tabsLabel = `${cell.tabsBin}-${cell.tabsBin + 4}`;
    setHovered({
      x: p.x,
      y: p.y,
      label: `${tabsLabel} tabs · ${cell.windowsBin} visible windows`,
      meta: `${cell.samples} samples · CPU ${fmtPct(cell.medianCpu)} · RAM ${fmtPct(cell.medianRam)}`
    });
  };

  return (
    <div className="wsMatrixWrap">
      <div className="wsMatrixNote sub">x = tab count (5-tab bins) · y = visible window count · color = median {metric.toUpperCase()}</div>
      <div className="wsMatrixScroll">
        <div className="wsMatrixGrid hexbinGrid" style={{ gridTemplateColumns: cols }}>
          <div className="wsMatrixCorner">visible \ tabs</div>
          {xBins.map((x) => (
            <div key={`hex-x-${x}`} className="wsMatrixHead">
              {x}-{x + 4}
            </div>
          ))}
          {rows.map((y) => (
            <Fragment key={`hex-row-${y}`}>
              <div className="wsMatrixRowLabel">
                <span className="wsTransitionTag hexbinAxisTag">{y}</span>
              </div>
              {xBins.map((x) => {
                const cell = cellMap.get(`${x}|${y}`);
                if (!cell) return <div key={`hex-cell-empty-${x}-${y}`} className="wsMatrixCell hexbinCell empty" />;

                const metricValue = metric === "cpu" ? cell.medianCpu : cell.medianRam;
                const metricRatio = maxMetric > 0 ? Math.max(0, Math.min(1, metricValue / maxMetric)) : 0;
                const sampleRatio = maxSamples > 0 ? Math.max(0, Math.min(1, cell.samples / maxSamples)) : 0;
                return (
                  <div
                    key={`hex-cell-${x}-${y}`}
                    className="wsMatrixCell hexbinCell active"
                    style={{
                      background: workspaceHeatColor(metricRatio),
                      boxShadow: `inset 0 0 0 1px rgba(255,255,255,${0.08 + sampleRatio * 0.36})`,
                      opacity: 0.42 + sampleRatio * 0.58
                    }}
                    onMouseEnter={(e) => updateHover(e, cell)}
                    onMouseMove={(e) => updateHover(e, cell)}
                    onMouseLeave={() => setHovered(null)}
                  >
                    <span className="wsMatrixCellText">{cell.samples}</span>
                  </div>
                );
              })}
            </Fragment>
          ))}
        </div>
      </div>
      <TooltipPortal tooltip={hovered} />
    </div>
  );
}

function TriGraphView({ graph }: { graph: TriGraphData }) {
  const [hovered, setHovered] = useState<HoverTooltip | null>(null);
  const { appNodes, domainNodes, workspaceNodes, edges, maxEdgeWeight } = graph;
  if (!edges.length || (!appNodes.length && !domainNodes.length && !workspaceNodes.length)) {
    return <div className="empty">No tri-graph edges in this range.</div>;
  }

  const width = 920;
  const laneMax = Math.max(appNodes.length, domainNodes.length, workspaceNodes.length, 1);
  const height = Math.max(300, 96 + laneMax * 34);
  const laneX: Record<TriGraphNodeType, number> = {
    app: 110,
    domain: 460,
    workspace: 810
  };

  const yFor = (idx: number, total: number): number => {
    const inner = height - 94;
    if (total <= 1) return 48 + inner / 2;
    return 48 + ((idx + 1) * inner) / (total + 1);
  };

  const pos = new Map<string, { x: number; y: number; node: TriGraphNode }>();
  appNodes.forEach((node, idx) => pos.set(node.id, { x: laneX.app, y: yFor(idx, appNodes.length), node }));
  domainNodes.forEach((node, idx) => pos.set(node.id, { x: laneX.domain, y: yFor(idx, domainNodes.length), node }));
  workspaceNodes.forEach((node, idx) => pos.set(node.id, { x: laneX.workspace, y: yFor(idx, workspaceNodes.length), node }));

  const edgeColor = (kind: TriGraphEdgeKind): string => {
    if (kind === "app-domain") return "rgba(96,165,250,0.82)";
    if (kind === "domain-workspace") return "rgba(167,139,250,0.82)";
    return "rgba(250,204,21,0.78)";
  };

  const updateEdgeHover = (e: MouseEvent<SVGPathElement>, edge: TriGraphEdge) => {
    const p = tooltipPoint(e as unknown as MouseEvent<Element>);
    const fromNode = pos.get(edge.from)?.node;
    const toNode = pos.get(edge.to)?.node;
    setHovered({
      x: p.x,
      y: p.y,
      label: `${fromNode?.label || edge.from} -> ${toNode?.label || edge.to}`,
      meta: `${edge.kind} · ${fmtSeconds(edge.weight)}`
    });
  };

  const updateNodeHover = (e: MouseEvent<SVGGElement>, node: TriGraphNode) => {
    const p = tooltipPoint(e as unknown as MouseEvent<Element>);
    setHovered({
      x: p.x,
      y: p.y,
      label: node.label,
      meta: `${node.type} · ${fmtSeconds(node.weight)}`
    });
  };

  const laneLabel = (type: TriGraphNodeType): string => {
    if (type === "app") return "Apps";
    if (type === "domain") return "Domains";
    return "Workspaces";
  };

  return (
    <div className="triGraphWrap">
      <svg className="triGraphSvg" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMinYMin meet">
        {(["app", "domain", "workspace"] as TriGraphNodeType[]).map((type) => (
          <g key={`lane-${type}`}>
            <line
              x1={laneX[type]}
              y1={38}
              x2={laneX[type]}
              y2={height - 20}
              stroke="rgba(166,213,255,.2)"
              strokeDasharray="4 6"
              strokeWidth="1"
            />
            <text x={laneX[type]} y={20} textAnchor="middle" className="triLaneLabel">
              {laneLabel(type)}
            </text>
          </g>
        ))}

        {[...edges]
          .sort((a, b) => a.weight - b.weight)
          .map((edge) => {
            const from = pos.get(edge.from);
            const to = pos.get(edge.to);
            if (!from || !to) return null;
            const dx = to.x - from.x;
            const c1x = from.x + dx * 0.34;
            const c2x = from.x + dx * 0.66;
            const d = `M ${from.x} ${from.y} C ${c1x} ${from.y}, ${c2x} ${to.y}, ${to.x} ${to.y}`;
            const w = maxEdgeWeight > 0 ? 1 + (edge.weight / maxEdgeWeight) * 5 : 1;
            return (
              <path
                key={edge.id}
                d={d}
                fill="none"
                stroke={edgeColor(edge.kind)}
                strokeWidth={w}
                strokeLinecap="round"
                className="triEdge"
                onMouseEnter={(e) => updateEdgeHover(e, edge)}
                onMouseMove={(e) => updateEdgeHover(e, edge)}
                onMouseLeave={() => setHovered(null)}
              />
            );
          })}

        {[...appNodes, ...domainNodes, ...workspaceNodes].map((node) => {
          const p = pos.get(node.id);
          if (!p) return null;
          const fill =
            node.type === "app"
              ? "rgba(45,212,191,.95)"
              : node.type === "domain"
                ? "rgba(96,165,250,.95)"
                : "rgba(250,204,21,.92)";
          const anchor = node.type === "app" ? "start" : node.type === "workspace" ? "end" : "middle";
          const textX = node.type === "app" ? p.x + 10 : node.type === "workspace" ? p.x - 10 : p.x;
          return (
            <g
              key={`tri-node-${node.id}`}
              className="triNode"
              onMouseEnter={(e) => updateNodeHover(e, node)}
              onMouseMove={(e) => updateNodeHover(e, node)}
              onMouseLeave={() => setHovered(null)}
            >
              <circle cx={p.x} cy={p.y} r={5.8} fill={fill} stroke="rgba(5,10,18,.9)" strokeWidth="1.1" />
              <text x={textX} y={p.y + 3.5} textAnchor={anchor} className="triNodeLabel">
                {trimLabel(node.label, 18)}
              </text>
            </g>
          );
        })}
      </svg>
      <TooltipPortal tooltip={hovered} />
    </div>
  );
}

function WorkspaceEntropyView({ rows }: { rows: WorkspaceEntropyRow[] }) {
  const [hovered, setHovered] = useState<HoverTooltip | null>(null);
  if (!rows.length) return <div className="empty">No workspace entropy rows.</div>;
  const maxSwitches = rows.reduce((m, r) => Math.max(m, r.switches), 0);

  const updateHover = (e: MouseEvent<HTMLDivElement>, row: WorkspaceEntropyRow) => {
    const p = tooltipPoint(e);
    setHovered({
      x: p.x,
      y: p.y,
      label: row.label,
      meta: `${Math.round(row.entropyBits * 100) / 100} bits · ${fmtPct(row.normalizedEntropy * 100)} normalized · ${row.switches} switches (${Math.round(row.switchesPerHour * 100) / 100}/h) · ${row.appCount} apps`
    });
  };

  return (
    <div className="barList">
      {rows.map((row) => {
        const entropyW = Math.max(0, Math.min(100, row.normalizedEntropy * 100));
        const switchW = maxSwitches > 0 ? (row.switches / maxSwitches) * 100 : 0;
        return (
          <div key={row.id} className="barRow">
            <div className="barLabel">
              {row.label}
              <span className="barSub">
                {row.appCount} apps · {row.switches} switches
              </span>
            </div>
            <div
              className="entropyTrack"
              onMouseEnter={(e) => updateHover(e, row)}
              onMouseMove={(e) => updateHover(e, row)}
              onMouseLeave={() => setHovered(null)}
            >
              <div className="entropyFill" style={{ width: `${entropyW}%` }} />
              <div className="entropySwitch" style={{ width: `${switchW}%` }} />
            </div>
            <div className="barValue">{Math.round(row.entropyBits * 100) / 100} bits</div>
          </div>
        );
      })}
      <div className="sub">cyan = normalized entropy (topic spread) · yellow overlay = switch frequency</div>
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
    const fPctC = Math.max(0, Math.min(100, fPct));
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
                <div className="barSegLegacy afk" style={{ height: `${e.afkPct}%` }} />
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
  const [mixedCategoryFilter, setMixedCategoryFilter] = useState<"all" | MixedCategory>("all");
  const [mixedHexMetric, setMixedHexMetric] = useState<"cpu" | "ram">("cpu");
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
  const [systemEvents, setSystemEvents] = useState<ApiEvent[]>([]);
  const [tabsEvents, setTabsEvents] = useState<ApiEvent[]>([]);
  const [appOpenEvents, setAppOpenEvents] = useState<ApiEvent[]>([]);
  const [idleEvents, setIdleEvents] = useState<ApiEvent[]>([]);
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
        systemData,
        tabsData,
        appOpenData,
        idleData,
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
        safe("system", () => fetchJson<EventsResponse>(`/v1/events?bucket=system&${query}`), { events: [] }),
        safe("browser_tabs", () => fetchJson<EventsResponse>(`/v1/events?bucket=browser_tabs&${query}`), { events: [] }),
        safe("app_open", () => fetchJson<EventsResponse>(`/v1/events?bucket=app_open&${query}`), { events: [] }),
        safe("idle", () => fetchJson<EventsResponse>(`/v1/events?bucket=idle&${query}`), { events: [] }),
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
      setSystemEvents(Array.isArray(systemData.events) ? systemData.events : []);
      setTabsEvents(Array.isArray(tabsData.events) ? tabsData.events : []);
      setAppOpenEvents(Array.isArray(appOpenData.events) ? appOpenData.events : []);
      setIdleEvents(Array.isArray(idleData.events) ? idleData.events : []);
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

  const systemInsights = useMemo(() => {
    const empty = {
      cpuSeries: [] as LinePoint[],
      memSeries: [] as LinePoint[],
      netRxSeries: [] as LinePoint[],
      netTxSeries: [] as LinePoint[],
      netTotalSeries: [] as LinePoint[],
      avgCpu: 0,
      peakCpu: 0,
      avgMem: 0,
      peakMem: 0,
      avgNetTotalMbps: 0,
      peakNetTotalMbps: 0,
      ifaceRows: [] as BarRow[],
      latest:
        null as
          | {
              ts: string;
              cpuPercent: number;
              memPercent: number;
              memUsedBytes: number;
              memTotalBytes: number;
              netRxMbps: number;
              netTxMbps: number;
              netTotalMbps: number;
              interfaces: string[];
            }
          | null
    };

    if (!windowRange) return empty;
    const fromMs = Date.parse(windowRange.from);
    const toMs = Date.parse(windowRange.to);
    if (Number.isNaN(fromMs) || Number.isNaN(toMs) || toMs <= fromMs) return empty;

    const cpuSeries: LinePoint[] = [];
    const memSeries: LinePoint[] = [];
    const netRxSeries: LinePoint[] = [];
    const netTxSeries: LinePoint[] = [];
    const netTotalSeries: LinePoint[] = [];
    const ifaceSeconds = new Map<string, number>();

    let latestMs = -1;
    let latest: (typeof empty)["latest"] = null;

    const addIfaceSeconds = (iface: string, sec: number): void => {
      const key = String(iface || "").trim();
      if (!key) return;
      ifaceSeconds.set(key, (ifaceSeconds.get(key) || 0) + Math.max(0, sec));
    };

    for (const e of systemEvents) {
      const data = (e?.data && typeof e.data === "object" ? e.data : undefined) as Record<string, unknown> | undefined;
      if (!data) continue;

      const startMs = Date.parse(e.start_ts);
      const endMs = Date.parse(e.end_ts);
      const tsMs = !Number.isNaN(endMs) ? endMs : startMs;
      if (Number.isNaN(tsMs) || tsMs < fromMs || tsMs > toMs) continue;

      const cpuPercent = Math.max(0, Math.min(100, asNumber(data.cpu_percent)));
      const memTotalBytes = Math.max(0, asNumber(data.mem_total_bytes));
      const memUsedBytes = Math.max(0, asNumber(data.mem_used_bytes));
      let memPercent = asNumber(data.mem_percent);
      if ((!Number.isFinite(memPercent) || memPercent <= 0) && memTotalBytes > 0) {
        memPercent = (memUsedBytes / memTotalBytes) * 100;
      }
      memPercent = Math.max(0, Math.min(100, Number.isFinite(memPercent) ? memPercent : 0));

      const netRxBps = Math.max(0, asNumber(data.net_rx_bps));
      const netTxBps = Math.max(0, asNumber(data.net_tx_bps));
      const netTotalBps = Math.max(netRxBps + netTxBps, Math.max(0, asNumber(data.net_total_bps)));
      const netRxMbps = bpsToMbps(netRxBps);
      const netTxMbps = bpsToMbps(netTxBps);
      const netTotalMbps = bpsToMbps(netTotalBps);

      cpuSeries.push({ t: tsMs, value: cpuPercent });
      memSeries.push({ t: tsMs, value: memPercent });
      netRxSeries.push({ t: tsMs, value: netRxMbps });
      netTxSeries.push({ t: tsMs, value: netTxMbps });
      netTotalSeries.push({ t: tsMs, value: netTotalMbps });

      if (!Number.isNaN(startMs) && !Number.isNaN(endMs)) {
        const clipStart = Math.max(fromMs, startMs);
        const clipEnd = Math.min(toMs, endMs);
        const durationSeconds = clipEnd > clipStart ? (clipEnd - clipStart) / 1000 : 0;
        if (durationSeconds > 0 && Array.isArray(data.net_interfaces)) {
          for (const raw of data.net_interfaces) {
            addIfaceSeconds(String(raw || ""), durationSeconds);
          }
        }
      }

      if (tsMs >= latestMs) {
        latestMs = tsMs;
        const interfaces = Array.isArray(data.net_interfaces)
          ? Array.from(
              new Set(
                data.net_interfaces
                  .map((v) => String(v || "").trim())
                  .filter((v) => v && v !== "null" && v !== "undefined")
              )
            )
          : [];
        latest = {
          ts: new Date(tsMs).toISOString(),
          cpuPercent,
          memPercent,
          memUsedBytes,
          memTotalBytes,
          netRxMbps,
          netTxMbps,
          netTotalMbps,
          interfaces
        };
      }
    }

    const dedupPoints = (points: LinePoint[]): LinePoint[] => {
      const sorted = [...points].sort((a, b) => a.t - b.t);
      const out: LinePoint[] = [];
      for (const p of sorted) {
        const prev = out[out.length - 1];
        if (prev && prev.t === p.t) prev.value = p.value;
        else out.push({ ...p });
      }
      return out;
    };

    const cpuSeriesD = dedupPoints(cpuSeries);
    const memSeriesD = dedupPoints(memSeries);
    const netRxSeriesD = dedupPoints(netRxSeries);
    const netTxSeriesD = dedupPoints(netTxSeries);
    const netTotalSeriesD = dedupPoints(netTotalSeries);

    const avg = (points: LinePoint[]): number =>
      points.length > 0 ? points.reduce((sum, p) => sum + p.value, 0) / points.length : 0;
    const peak = (points: LinePoint[]): number => points.reduce((m, p) => Math.max(m, p.value), 0);

    const ifaceRows: BarRow[] = Array.from(ifaceSeconds.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)
      .map(([iface, seconds]) => ({
        id: iface,
        label: iface,
        value: seconds,
        sub: "interface active"
      }));

    return {
      cpuSeries: cpuSeriesD,
      memSeries: memSeriesD,
      netRxSeries: netRxSeriesD,
      netTxSeries: netTxSeriesD,
      netTotalSeries: netTotalSeriesD,
      avgCpu: avg(cpuSeriesD),
      peakCpu: peak(cpuSeriesD),
      avgMem: avg(memSeriesD),
      peakMem: peak(memSeriesD),
      avgNetTotalMbps: avg(netTotalSeriesD),
      peakNetTotalMbps: peak(netTotalSeriesD),
      ifaceRows,
      latest
    };
  }, [systemEvents, windowRange]);

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

  const mixedInsights = useMemo(() => {
    const empty = {
      coOccurrenceMatrix: {
        activeApps: [],
        visibleApps: [],
        seconds: [],
        rowTotals: [],
        colTotals: [],
        maxCellSeconds: 0,
        totalSeconds: 0,
        topPairs: []
      } as AppCoOccurrenceMatrix,
      dailyMonitorSplitRows: [] as DailyMonitorSplitRow[],
      appFlowEdges: [] as AppFlowEdge[],
      categoryTransitionMatrix: {
        labels: [],
        counts: [],
        rowTotals: [],
        colTotals: [],
        maxCell: 0,
        total: 0,
        topTransitions: []
      } as CategoryTransitionMatrix,
      workspaceUsageRows: [] as WorkspaceUsageOverlayRow[],
      productivityPulseBins: [] as ProductivityPulseBin[],
      switchingCostRows: [] as BarRow[],
      hexbinPoints: [] as HexbinDensityPoint[],
      triGraph: {
        appNodes: [],
        domainNodes: [],
        workspaceNodes: [],
        edges: [],
        maxEdgeWeight: 0
      } as TriGraphData,
      workspaceEntropyRows: [] as WorkspaceEntropyRow[]
    };

    if (!windowRange) return empty;
    const fromMs = Date.parse(windowRange.from);
    const toMs = Date.parse(windowRange.to);
    if (Number.isNaN(fromMs) || Number.isNaN(toMs) || toMs <= fromMs) return empty;

    type ActiveInterval = {
      start: number;
      end: number;
      app: string;
      title: string;
      workspace: string;
      category: MixedCategory;
    };
    type VisibleInterval = {
      start: number;
      end: number;
      app: string;
      title: string;
      workspace: string;
    };
    type WorkspaceInterval = {
      start: number;
      end: number;
      workspace: string;
      setup: "single" | "multi" | "unknown";
    };
    type AfkInterval = { start: number; end: number };

    const parseSpan = (startTs: string, endTs: string): { start: number; end: number } | null => {
      const start = Date.parse(startTs);
      const end = Date.parse(endTs);
      if (Number.isNaN(start) || Number.isNaN(end) || end <= start) return null;
      if (end <= fromMs || start >= toMs) return null;
      const clippedStart = Math.max(fromMs, start);
      const clippedEnd = Math.min(toMs, end);
      if (clippedEnd <= clippedStart) return null;
      return { start: clippedStart, end: clippedEnd };
    };

    const activeIntervals: ActiveInterval[] = [];
    for (const e of windowEvents) {
      const span = parseSpan(e.start_ts, e.end_ts);
      if (!span) continue;
      const app = asString(e?.data?.app) || asString(e?.source) || "unknown";
      const title = asString(e?.data?.title);
      const workspace = asString(e?.data?.workspace) || asString(e?.data?.workspace_id) || "?";
      const category = classifyActiveCategory(app, title);
      activeIntervals.push({ ...span, app, title, workspace, category });
    }
    activeIntervals.sort((a, b) => a.start - b.start || a.end - b.end);

    const visibleIntervals: VisibleInterval[] = [];
    for (const e of visibleEvents) {
      const span = parseSpan(e.start_ts, e.end_ts);
      if (!span) continue;
      const app = asString(e?.data?.app) || asString(e?.source) || "unknown";
      const title = asString(e?.data?.title);
      const workspace = asString(e?.data?.workspace) || asString(e?.data?.workspace_id) || "?";
      visibleIntervals.push({ ...span, app, title, workspace });
    }
    visibleIntervals.sort((a, b) => a.start - b.start || a.end - b.end);

    const workspaceIntervals: WorkspaceInterval[] = [];
    for (const e of workspaceEvents) {
      const span = parseSpan(e.start_ts, e.end_ts);
      if (!span) continue;
      const ws = asString(e?.data?.workspace) || asString(e?.data?.workspace_id) || "?";
      const setup = monitorSetupFromData(
        (e?.data && typeof e.data === "object" ? e.data : undefined) as Record<string, unknown> | undefined
      );
      workspaceIntervals.push({ ...span, workspace: ws, setup: setup || "unknown" });
    }
    workspaceIntervals.sort((a, b) => a.start - b.start || a.end - b.end);

    const afkIntervals: AfkInterval[] = [];
    for (const e of idleEvents) {
      const span = parseSpan(e.start_ts, e.end_ts);
      if (!span) continue;
      const afkRaw = e?.data?.afk;
      const afk =
        typeof afkRaw === "boolean"
          ? afkRaw
          : ["1", "true", "yes"].includes(String(afkRaw || "").trim().toLowerCase());
      if (!afk) continue;
      afkIntervals.push(span);
    }
    afkIntervals.sort((a, b) => a.start - b.start || a.end - b.end);

    const afkOverlapSecondsInRange = (startMs: number, endMs: number): number => {
      if (endMs <= startMs || !afkIntervals.length) return 0;
      let total = 0;
      for (const a of afkIntervals) {
        if (a.end <= startMs) continue;
        if (a.start >= endMs) break;
        total += overlapSeconds(startMs, endMs, a.start, a.end);
      }
      return total;
    };

    const rowTotalsMap = new Map<string, number>();
    const colTotalsMap = new Map<string, number>();
    const pairMap = new Map<string, Map<string, number>>();
    let pairTotal = 0;
    let visStartIdx = 0;
    for (const active of activeIntervals) {
      while (visStartIdx < visibleIntervals.length && visibleIntervals[visStartIdx].end <= active.start) {
        visStartIdx += 1;
      }
      for (let j = visStartIdx; j < visibleIntervals.length && visibleIntervals[j].start < active.end; j += 1) {
        const visible = visibleIntervals[j];
        const overlap = overlapSeconds(active.start, active.end, visible.start, visible.end);
        if (overlap <= 0) continue;
        const activeApp = active.app || "unknown";
        const visibleApp = visible.app || "unknown";
        const row = pairMap.get(activeApp) || new Map<string, number>();
        row.set(visibleApp, (row.get(visibleApp) || 0) + overlap);
        pairMap.set(activeApp, row);
        rowTotalsMap.set(activeApp, (rowTotalsMap.get(activeApp) || 0) + overlap);
        colTotalsMap.set(visibleApp, (colTotalsMap.get(visibleApp) || 0) + overlap);
        pairTotal += overlap;
      }
    }

    const coActiveApps = Array.from(rowTotalsMap.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 14)
      .map(([app]) => app);
    const coVisibleApps = Array.from(colTotalsMap.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 14)
      .map(([app]) => app);
    const coSeconds = coActiveApps.map((activeApp) => coVisibleApps.map((visibleApp) => pairMap.get(activeApp)?.get(visibleApp) || 0));
    const coRowTotals = coActiveApps.map((activeApp) => rowTotalsMap.get(activeApp) || 0);
    const coColTotals = coVisibleApps.map((visibleApp) => colTotalsMap.get(visibleApp) || 0);
    const coMaxCell = coSeconds.reduce((m, row) => Math.max(m, ...row, 0), 0);
    const coTotal = coSeconds.reduce((sum, row) => sum + row.reduce((s, v) => s + v, 0), 0);
    const coPairsFlat: Array<{ activeApp: string; visibleApp: string; seconds: number; sharePct: number }> = [];
    for (const [activeApp, row] of pairMap.entries()) {
      for (const [visibleApp, seconds] of row.entries()) {
        if (seconds <= 0) continue;
        coPairsFlat.push({
          activeApp,
          visibleApp,
          seconds,
          sharePct: pairTotal > 0 ? (seconds / pairTotal) * 100 : 0
        });
      }
    }
    coPairsFlat.sort((a, b) => b.seconds - a.seconds);
    const coOccurrenceMatrix: AppCoOccurrenceMatrix = {
      activeApps: coActiveApps,
      visibleApps: coVisibleApps,
      seconds: coSeconds,
      rowTotals: coRowTotals,
      colTotals: coColTotals,
      maxCellSeconds: coMaxCell,
      totalSeconds: coTotal,
      topPairs: coPairsFlat.slice(0, 24)
    };

    type DailyAgg = {
      startMs: number;
      label: string;
      singleSeconds: number;
      multiSeconds: number;
      unknownSeconds: number;
      visibleWindowSeconds: number;
      openAppSeconds: number;
      totalSeconds: number;
    };
    const dayMap = new Map<number, DailyAgg>();
    const dayStart = (ms: number): number => {
      const d = new Date(ms);
      d.setHours(0, 0, 0, 0);
      return d.getTime();
    };
    const ensureDay = (startMs: number): DailyAgg => {
      let row = dayMap.get(startMs);
      if (!row) {
        row = {
          startMs,
          label: new Date(startMs).toLocaleDateString(undefined, { month: "2-digit", day: "2-digit" }),
          singleSeconds: 0,
          multiSeconds: 0,
          unknownSeconds: 0,
          visibleWindowSeconds: 0,
          openAppSeconds: 0,
          totalSeconds: 0
        };
        dayMap.set(startMs, row);
      }
      return row;
    };
    const addDaily = (startMs: number, endMs: number, apply: (row: DailyAgg, sec: number) => void): void => {
      let cur = startMs;
      while (cur < endMs) {
        const dStart = dayStart(cur);
        const dEnd = dStart + 86_400_000;
        const segEnd = Math.min(endMs, dEnd);
        const sec = (segEnd - cur) / 1000;
        if (sec > 0) apply(ensureDay(dStart), sec);
        if (segEnd <= cur) break;
        cur = segEnd;
      }
    };
    for (const ws of workspaceIntervals) {
      addDaily(ws.start, ws.end, (row, sec) => {
        row.totalSeconds += sec;
        if (ws.setup === "single") row.singleSeconds += sec;
        else if (ws.setup === "multi") row.multiSeconds += sec;
        else row.unknownSeconds += sec;
      });
    }
    for (const v of visibleIntervals) {
      addDaily(v.start, v.end, (row, sec) => {
        row.visibleWindowSeconds += sec;
      });
    }
    for (const e of appOpenEvents) {
      const span = parseSpan(e.start_ts, e.end_ts);
      if (!span) continue;
      let count = asNumber(e?.data?.count);
      if (count <= 0 && Array.isArray(e?.data?.apps)) count = e.data.apps.length;
      if (count <= 0) count = 1;
      addDaily(span.start, span.end, (row, sec) => {
        row.openAppSeconds += sec * count;
      });
    }
    const dailyMonitorSplitRows: DailyMonitorSplitRow[] = Array.from(dayMap.values())
      .sort((a, b) => a.startMs - b.startMs)
      .map((row) => ({
        id: String(row.startMs),
        label: row.label,
        singleSeconds: row.singleSeconds,
        multiSeconds: row.multiSeconds,
        unknownSeconds: row.unknownSeconds,
        visibleWindowSeconds: row.visibleWindowSeconds,
        openAppSeconds: row.openAppSeconds,
        totalSeconds: row.totalSeconds
      }));

    const flowMap = new Map<string, { from: string; to: string; count: number; workspacePathCounts: Map<string, number> }>();
    const flowGapMs = 20 * 60_000;
    let totalFlows = 0;
    for (let i = 1; i < activeIntervals.length; i += 1) {
      const prev = activeIntervals[i - 1];
      const cur = activeIntervals[i];
      if (cur.start - prev.end > flowGapMs) continue;
      if (!prev.app || !cur.app || prev.app === cur.app) continue;
      const id = `${prev.app}=>${cur.app}`;
      const item = flowMap.get(id) || {
        from: prev.app,
        to: cur.app,
        count: 0,
        workspacePathCounts: new Map<string, number>()
      };
      item.count += 1;
      const path = `${workspaceLabel(prev.workspace)} -> ${workspaceLabel(cur.workspace)}`;
      item.workspacePathCounts.set(path, (item.workspacePathCounts.get(path) || 0) + 1);
      flowMap.set(id, item);
      totalFlows += 1;
    }
    const appFlowEdges: AppFlowEdge[] = Array.from(flowMap.entries())
      .map(([id, edge]) => {
        let topWorkspacePath = "n/a";
        let topCount = 0;
        for (const [path, count] of edge.workspacePathCounts.entries()) {
          if (count > topCount) {
            topCount = count;
            topWorkspacePath = path;
          }
        }
        return {
          id,
          from: edge.from,
          to: edge.to,
          count: edge.count,
          sharePct: totalFlows > 0 ? (edge.count / totalFlows) * 100 : 0,
          topWorkspacePath
        };
      })
      .sort((a, b) => b.count - a.count)
      .slice(0, 20);

    const labels = [...MIXED_CATEGORY_ORDER];
    const idxByCategory = new Map<MixedCategory, number>();
    labels.forEach((c, idx) => idxByCategory.set(c, idx));
    const markovCounts = Array.from({ length: labels.length }, () => new Array<number>(labels.length).fill(0));
    for (let i = 1; i < activeIntervals.length; i += 1) {
      const prev = activeIntervals[i - 1];
      const cur = activeIntervals[i];
      if (cur.start - prev.end > flowGapMs) continue;
      const from = prev.category;
      const to = cur.category;
      const fi = idxByCategory.get(from);
      const ti = idxByCategory.get(to);
      if (fi == null || ti == null) continue;
      markovCounts[fi][ti] += 1;
    }
    const markovRowTotals = markovCounts.map((row) => row.reduce((sum, v) => sum + v, 0));
    const markovColTotals = labels.map((_, col) => markovCounts.reduce((sum, row) => sum + (row[col] || 0), 0));
    const markovMax = markovCounts.reduce((m, row) => Math.max(m, ...row, 0), 0);
    const markovTotal = markovRowTotals.reduce((sum, v) => sum + v, 0);
    const topTransitions: Array<{ from: MixedCategory; to: MixedCategory; count: number; rowProbPct: number; sharePct: number }> = [];
    for (let i = 0; i < labels.length; i += 1) {
      for (let j = 0; j < labels.length; j += 1) {
        const count = markovCounts[i][j];
        if (count <= 0) continue;
        topTransitions.push({
          from: labels[i],
          to: labels[j],
          count,
          rowProbPct: markovRowTotals[i] > 0 ? (count / markovRowTotals[i]) * 100 : 0,
          sharePct: markovTotal > 0 ? (count / markovTotal) * 100 : 0
        });
      }
    }
    topTransitions.sort((a, b) => b.count - a.count);
    const categoryTransitionMatrix: CategoryTransitionMatrix = {
      labels: markovTotal > 0 ? labels : [],
      counts: markovTotal > 0 ? markovCounts : [],
      rowTotals: markovTotal > 0 ? markovRowTotals : [],
      colTotals: markovTotal > 0 ? markovColTotals : [],
      maxCell: markovMax,
      total: markovTotal,
      topTransitions: topTransitions.slice(0, 16)
    };

    const usageSecondsByWorkspace = new Map<string, number>();
    for (const ws of workspaceIntervals) {
      const sec = Math.max(0, (ws.end - ws.start) / 1000);
      if (sec <= 0) continue;
      usageSecondsByWorkspace.set(ws.workspace, (usageSecondsByWorkspace.get(ws.workspace) || 0) + sec);
    }
    const switchesByWorkspace = new Map<string, number>();
    const switchEventsInRange: Array<{ tsMs: number; to: string }> = [];
    for (const e of workspaceSwitchEvents) {
      const tsMs = Date.parse(e.start_ts || e.end_ts);
      if (Number.isNaN(tsMs) || tsMs < fromMs || tsMs > toMs) continue;
      const fromWs =
        asString(e?.data?.from_workspace) || asString(e?.data?.prev_workspace) || asString(e?.data?.workspace) || "?";
      const toWs = asString(e?.data?.to_workspace) || asString(e?.data?.workspace) || "?";
      switchesByWorkspace.set(fromWs, (switchesByWorkspace.get(fromWs) || 0) + 1);
      switchesByWorkspace.set(toWs, (switchesByWorkspace.get(toWs) || 0) + 1);
      switchEventsInRange.push({ tsMs, to: toWs });
    }
    switchEventsInRange.sort((a, b) => a.tsMs - b.tsMs);

    const workspaceKeys = Array.from(new Set([...usageSecondsByWorkspace.keys(), ...switchesByWorkspace.keys()])).sort(
      compareWorkspaceIds
    );
    const workspaceUsageRows: WorkspaceUsageOverlayRow[] = workspaceKeys
      .map((ws) => {
        const seconds = usageSecondsByWorkspace.get(ws) || 0;
        const switches = switchesByWorkspace.get(ws) || 0;
        const switchesPerHour = seconds > 0 ? switches / (seconds / 3600) : 0;
        return {
          id: ws,
          label: workspaceLabel(ws),
          seconds,
          switches,
          switchesPerHour
        };
      })
      .filter((row) => row.seconds > 0 || row.switches > 0);

    const switchingCostAgg = new Map<string, { costs: number[]; churnTotal: number }>();
    const stableThresholdSec = 180;
    const horizonSec = 15 * 60;
    let activeIdx = 0;
    for (const sw of switchEventsInRange) {
      const horizonEndMs = Math.min(toMs, sw.tsMs + horizonSec * 1000);
      while (activeIdx < activeIntervals.length && activeIntervals[activeIdx].end <= sw.tsMs) {
        activeIdx += 1;
      }

      let currentApp = "";
      let runSec = 0;
      let churn = 0;
      let lastSegEndMs = sw.tsMs;
      let stableAtSec: number | null = null;

      for (let j = activeIdx; j < activeIntervals.length && activeIntervals[j].start < horizonEndMs; j += 1) {
        const segStart = Math.max(sw.tsMs, activeIntervals[j].start);
        const segEnd = Math.min(horizonEndMs, activeIntervals[j].end);
        if (segEnd <= segStart) continue;
        const afkSec = afkOverlapSecondsInRange(segStart, segEnd);
        const segSec = Math.max(0, (segEnd - segStart) / 1000 - afkSec);
        if (segSec <= 0) continue;

        const app = activeIntervals[j].app || "unknown";
        if (app === currentApp && segStart <= lastSegEndMs + 20_000) {
          runSec += segSec;
        } else {
          if (currentApp && app !== currentApp) churn += 1;
          currentApp = app;
          runSec = segSec;
        }
        lastSegEndMs = segEnd;

        if (runSec >= stableThresholdSec) {
          const overSec = runSec - stableThresholdSec;
          const stableAtMs = segEnd - overSec * 1000;
          stableAtSec = Math.max(0, (stableAtMs - sw.tsMs) / 1000);
          break;
        }
      }

      const costSec = stableAtSec != null ? stableAtSec : horizonSec;
      const rec = switchingCostAgg.get(sw.to) || { costs: [], churnTotal: 0 };
      rec.costs.push(costSec);
      rec.churnTotal += churn;
      switchingCostAgg.set(sw.to, rec);
    }

    const switchingCostRows: BarRow[] = Array.from(switchingCostAgg.entries())
      .map(([workspace, rec]) => {
        const avg = rec.costs.length ? rec.costs.reduce((sum, v) => sum + v, 0) / rec.costs.length : 0;
        const med = median(rec.costs);
        const churnAvg = rec.costs.length ? rec.churnTotal / rec.costs.length : 0;
        return {
          id: `switch-cost-${workspace}`,
          label: workspaceLabel(workspace),
          value: avg,
          sub: `${rec.costs.length} switches · median ${fmtSecondsShort(med)} · churn ${Math.round(churnAvg * 100) / 100}`,
          color: "linear-gradient(90deg, rgba(250,204,21,.8), rgba(234,88,12,.9))"
        };
      })
      .sort((a, b) => b.value - a.value)
      .slice(0, 16);

    let pulseStepMs = 3600_000;
    if (range === "1w") pulseStepMs = 4 * 3600_000;
    else if (range === "1m") pulseStepMs = 12 * 3600_000;
    else if (range === "all") {
      const raw = Math.max(3600_000, Math.ceil((toMs - fromMs) / 36));
      const choices = [3600_000, 7200_000, 14_400_000, 21_600_000, 43_200_000, 86_400_000, 172_800_000, 604_800_000];
      pulseStepMs = choices.find((v) => raw <= v) || raw;
    }
    const pulseBins: ProductivityPulseBin[] = [];
    for (let s = fromMs; s < toMs; s += pulseStepMs) {
      const e = Math.min(toMs, s + pulseStepMs);
      pulseBins.push({
        id: `${s}`,
        label: workspaceBinLabel(range, s, pulseStepMs),
        startMs: s,
        endMs: e,
        workSeconds: 0,
        communicationSeconds: 0,
        distractionSeconds: 0,
        otherSeconds: 0,
        afkSeconds: 0
      });
    }
    const addToPulseBins = (startMs: number, endMs: number, add: (bin: ProductivityPulseBin, sec: number) => void): void => {
      let cur = startMs;
      while (cur < endMs) {
        const idx = Math.max(0, Math.min(pulseBins.length - 1, Math.floor((cur - fromMs) / pulseStepMs)));
        const bin = pulseBins[idx];
        const segEnd = Math.min(endMs, bin.endMs);
        const sec = (segEnd - cur) / 1000;
        if (sec > 0) add(bin, sec);
        if (segEnd <= cur) break;
        cur = segEnd;
      }
    };
    for (const a of activeIntervals) {
      addToPulseBins(a.start, a.end, (bin, sec) => {
        const pulseCat = mixedToPulseCategory(a.category);
        if (pulseCat === "work") bin.workSeconds += sec;
        else if (pulseCat === "communication") bin.communicationSeconds += sec;
        else if (pulseCat === "distraction") bin.distractionSeconds += sec;
        else bin.otherSeconds += sec;
      });
    }
    for (const afk of afkIntervals) {
      addToPulseBins(afk.start, afk.end, (bin, sec) => {
        bin.afkSeconds += sec;
      });
    }
    for (const bin of pulseBins) {
      const duration = Math.max(1, (bin.endMs - bin.startMs) / 1000);
      bin.afkSeconds = Math.max(0, Math.min(duration, bin.afkSeconds));
      const activeTotal = bin.workSeconds + bin.communicationSeconds + bin.distractionSeconds + bin.otherSeconds;
      const activeCap = Math.max(0, duration - bin.afkSeconds);
      if (activeTotal > activeCap && activeTotal > 0) {
        const scale = activeCap / activeTotal;
        bin.workSeconds *= scale;
        bin.communicationSeconds *= scale;
        bin.distractionSeconds *= scale;
        bin.otherSeconds *= scale;
      }
    }
    const productivityPulseBins = pulseBins;

    let densityStepMs = 10 * 60_000;
    if (range === "1w") densityStepMs = 30 * 60_000;
    else if (range === "1m") densityStepMs = 2 * 3600_000;
    else if (range === "all") {
      const raw = Math.max(30 * 60_000, Math.ceil((toMs - fromMs) / 120));
      const choices = [10 * 60_000, 15 * 60_000, 30 * 60_000, 3600_000, 2 * 3600_000, 4 * 3600_000, 12 * 3600_000, 86_400_000];
      densityStepMs = choices.find((v) => raw <= v) || raw;
    }
    const densityBinCount = Math.max(1, Math.ceil((toMs - fromMs) / densityStepMs));
    const densityStarts = Array.from({ length: densityBinCount }, (_, idx) => fromMs + idx * densityStepMs);
    const densityEnds = densityStarts.map((s) => Math.min(toMs, s + densityStepMs));
    const tabWeighted = new Array(densityBinCount).fill(0);
    const visibleWeighted = new Array(densityBinCount).fill(0);
    const categoryWeighted = Array.from({ length: densityBinCount }, () => new Map<MixedCategory, number>());
    const cpuSamples = Array.from({ length: densityBinCount }, () => [] as number[]);
    const ramSamples = Array.from({ length: densityBinCount }, () => [] as number[]);

    const addToDensityBins = (startMs: number, endMs: number, add: (idx: number, sec: number) => void): void => {
      let cur = startMs;
      while (cur < endMs) {
        const idx = Math.max(0, Math.min(densityBinCount - 1, Math.floor((cur - fromMs) / densityStepMs)));
        const segEnd = Math.min(endMs, densityEnds[idx]);
        const sec = (segEnd - cur) / 1000;
        if (sec > 0) add(idx, sec);
        if (segEnd <= cur) break;
        cur = segEnd;
      }
    };

    for (const e of tabsEvents) {
      const span = parseSpan(e.start_ts, e.end_ts);
      if (!span) continue;
      let count = asNumber(e?.data?.count);
      if (count <= 0 && Array.isArray(e?.data?.tabs)) count = e.data.tabs.length;
      if (count <= 0) continue;
      addToDensityBins(span.start, span.end, (idx, sec) => {
        tabWeighted[idx] += count * sec;
      });
    }
    for (const v of visibleIntervals) {
      addToDensityBins(v.start, v.end, (idx, sec) => {
        visibleWeighted[idx] += sec;
      });
    }
    for (const a of activeIntervals) {
      addToDensityBins(a.start, a.end, (idx, sec) => {
        const row = categoryWeighted[idx];
        row.set(a.category, (row.get(a.category) || 0) + sec);
      });
    }
    for (const e of systemEvents) {
      const data = (e?.data && typeof e.data === "object" ? e.data : undefined) as Record<string, unknown> | undefined;
      if (!data) continue;
      const start = Date.parse(e.start_ts);
      const end = Date.parse(e.end_ts);
      const ts = !Number.isNaN(end) ? end : start;
      if (Number.isNaN(ts) || ts < fromMs || ts > toMs) continue;
      const idx = Math.max(0, Math.min(densityBinCount - 1, Math.floor((ts - fromMs) / densityStepMs)));
      const cpu = Math.max(0, Math.min(100, asNumber(data.cpu_percent)));
      let ram = asNumber(data.mem_percent);
      if ((!Number.isFinite(ram) || ram <= 0) && asNumber(data.mem_total_bytes) > 0) {
        ram = (asNumber(data.mem_used_bytes) / asNumber(data.mem_total_bytes)) * 100;
      }
      ram = Math.max(0, Math.min(100, Number.isFinite(ram) ? ram : 0));
      cpuSamples[idx].push(cpu);
      ramSamples[idx].push(ram);
    }

    const hexbinPoints: HexbinDensityPoint[] = [];
    for (let idx = 0; idx < densityBinCount; idx += 1) {
      const start = densityStarts[idx];
      const end = densityEnds[idx];
      const duration = Math.max(1, (end - start) / 1000);
      const hasSignal =
        tabWeighted[idx] > 0 || visibleWeighted[idx] > 0 || cpuSamples[idx].length > 0 || ramSamples[idx].length > 0;
      if (!hasSignal) continue;
      const avgTabs = tabWeighted[idx] / duration;
      const avgVisible = visibleWeighted[idx] / duration;
      const categoryMap = categoryWeighted[idx];
      let dominantCategory: MixedCategory = "other";
      let dominantSec = 0;
      for (const [cat, sec] of categoryMap.entries()) {
        if (sec > dominantSec) {
          dominantSec = sec;
          dominantCategory = cat;
        }
      }
      hexbinPoints.push({
        id: `${start}`,
        tabsCount: avgTabs,
        visibleWindows: avgVisible,
        cpuPercent: cpuSamples[idx].length ? median(cpuSamples[idx]) : 0,
        ramPercent: ramSamples[idx].length ? median(ramSamples[idx]) : 0,
        category: dominantCategory
      });
    }

    const triNodeWeights = new Map<string, number>();
    const triNodeMeta = new Map<string, { type: TriGraphNodeType; raw: string; label: string }>();
    const triEdgeWeights = new Map<string, TriGraphEdge>();

    const triNodeId = (type: TriGraphNodeType, raw: string): string => `${type}:${String(raw || "").toLowerCase()}`;
    const addTriNode = (type: TriGraphNodeType, raw: string, label: string, weight: number): string => {
      const cleanRaw = String(raw || "").trim() || "unknown";
      const id = triNodeId(type, cleanRaw);
      triNodeWeights.set(id, (triNodeWeights.get(id) || 0) + Math.max(0, weight));
      if (!triNodeMeta.has(id)) triNodeMeta.set(id, { type, raw: cleanRaw, label: trimLabel(label || cleanRaw, 42) });
      return id;
    };
    const addTriEdge = (
      kind: TriGraphEdgeKind,
      fromType: TriGraphNodeType,
      fromRaw: string,
      fromLabel: string,
      toType: TriGraphNodeType,
      toRaw: string,
      toLabel: string,
      weight: number
    ): void => {
      const w = Math.max(0, weight);
      if (w <= 0) return;
      const fromId = addTriNode(fromType, fromRaw, fromLabel, w);
      const toId = addTriNode(toType, toRaw, toLabel, w);
      const edgeId = `${kind}:${fromId}->${toId}`;
      const prev = triEdgeWeights.get(edgeId);
      if (prev) prev.weight += w;
      else triEdgeWeights.set(edgeId, { id: edgeId, kind, from: fromId, to: toId, weight: w });
    };

    for (const a of activeIntervals) {
      const sec = Math.max(0, (a.end - a.start) / 1000);
      if (sec <= 0) continue;
      addTriEdge("app-workspace", "app", a.app, a.app, "workspace", a.workspace, workspaceLabel(a.workspace), sec);
      if (isBrowserApp(a.app)) {
        const host = extractHostFromTitle(a.title);
        const domain = host ? baseDomainFromHost(host) : "";
        if (domain) {
          addTriEdge("app-domain", "app", a.app, a.app, "domain", domain, domain, sec);
          addTriEdge("domain-workspace", "domain", domain, domain, "workspace", a.workspace, workspaceLabel(a.workspace), sec);
        }
      }
    }
    for (const v of visibleIntervals) {
      const sec = Math.max(0, (v.end - v.start) / 1000) * 0.35;
      if (sec <= 0) continue;
      addTriEdge("app-workspace", "app", v.app, v.app, "workspace", v.workspace, workspaceLabel(v.workspace), sec);
      if (isBrowserApp(v.app)) {
        const host = extractHostFromTitle(v.title);
        const domain = host ? baseDomainFromHost(host) : "";
        if (domain) {
          addTriEdge("app-domain", "app", v.app, v.app, "domain", domain, domain, sec);
          addTriEdge("domain-workspace", "domain", domain, domain, "workspace", v.workspace, workspaceLabel(v.workspace), sec);
        }
      }
    }
    for (const e of tabsEvents) {
      const span = parseSpan(e.start_ts, e.end_ts);
      if (!span) continue;
      const durationSec = (span.end - span.start) / 1000;
      const tabsRaw = Array.isArray(e?.data?.tabs) ? e.data.tabs : [];
      const tabs = tabsRaw.filter((tab) => tab && typeof tab === "object").slice(0, 120) as Record<string, unknown>[];
      if (!tabs.length || durationSec <= 0) continue;
      const app = asString(e?.data?.browser) || asString(e?.source) || "browser";
      const workspace = asString(e?.data?.workspace) || asString(e?.data?.workspace_id) || "?";
      const perTabSec = durationSec / tabs.length;
      for (const tab of tabs) {
        const domain = tabDomainFromTab(tab);
        addTriEdge("app-domain", "app", app, app, "domain", domain, domain, perTabSec);
        addTriEdge("domain-workspace", "domain", domain, domain, "workspace", workspace, workspaceLabel(workspace), perTabSec * 0.8);
        addTriEdge("app-workspace", "app", app, app, "workspace", workspace, workspaceLabel(workspace), perTabSec * 0.25);
      }
    }

    const nodesByType = (type: TriGraphNodeType): TriGraphNode[] =>
      Array.from(triNodeMeta.entries())
        .filter(([, meta]) => meta.type === type)
        .map(([id, meta]) => ({
          id,
          type: meta.type,
          raw: meta.raw,
          label: meta.label,
          weight: triNodeWeights.get(id) || 0
        }))
        .sort((a, b) => b.weight - a.weight);

    const appNodesTop = nodesByType("app").slice(0, 12);
    const domainNodesTop = nodesByType("domain").slice(0, 16);
    const workspaceNodesTop = nodesByType("workspace")
      .slice(0, 12)
      .sort((a, b) => compareWorkspaceIds(a.raw, b.raw));

    const allowedNodeIds = new Set<string>([
      ...appNodesTop.map((n) => n.id),
      ...domainNodesTop.map((n) => n.id),
      ...workspaceNodesTop.map((n) => n.id)
    ]);
    const triEdges = Array.from(triEdgeWeights.values())
      .filter((edge) => allowedNodeIds.has(edge.from) && allowedNodeIds.has(edge.to))
      .sort((a, b) => b.weight - a.weight)
      .slice(0, 80);
    const maxTriEdgeWeight = triEdges.reduce((m, e) => Math.max(m, e.weight), 0);
    const triGraph: TriGraphData = {
      appNodes: appNodesTop,
      domainNodes: domainNodesTop,
      workspaceNodes: workspaceNodesTop,
      edges: triEdges,
      maxEdgeWeight: maxTriEdgeWeight
    };

    const entropyAppMap = new Map<string, Map<string, number>>();
    const ensureEntropyRow = (workspace: string): Map<string, number> => {
      let row = entropyAppMap.get(workspace);
      if (!row) {
        row = new Map<string, number>();
        entropyAppMap.set(workspace, row);
      }
      return row;
    };
    for (const a of activeIntervals) {
      const sec = Math.max(0, (a.end - a.start) / 1000);
      if (sec <= 0) continue;
      const row = ensureEntropyRow(a.workspace);
      row.set(a.app, (row.get(a.app) || 0) + sec);
    }
    for (const v of visibleIntervals) {
      const sec = Math.max(0, (v.end - v.start) / 1000) * 0.35;
      if (sec <= 0) continue;
      const row = ensureEntropyRow(v.workspace);
      row.set(v.app, (row.get(v.app) || 0) + sec);
    }

    const switchCountForEntropy = new Map<string, number>();
    for (const e of workspaceSwitchEvents) {
      const tsMs = Date.parse(e.start_ts || e.end_ts);
      if (Number.isNaN(tsMs) || tsMs < fromMs || tsMs > toMs) continue;
      const fromWs =
        asString(e?.data?.from_workspace) || asString(e?.data?.prev_workspace) || asString(e?.data?.workspace) || "?";
      const toWs = asString(e?.data?.to_workspace) || asString(e?.data?.workspace) || "?";
      switchCountForEntropy.set(fromWs, (switchCountForEntropy.get(fromWs) || 0) + 1);
      switchCountForEntropy.set(toWs, (switchCountForEntropy.get(toWs) || 0) + 1);
    }

    const workspaceEntropyRows: WorkspaceEntropyRow[] = Array.from(entropyAppMap.entries())
      .map(([workspace, appWeights]) => {
        const values = Array.from(appWeights.values()).filter((v) => v > 0);
        const totalSeconds = values.reduce((sum, v) => sum + v, 0);
        const appCount = values.length;
        let entropyBits = 0;
        if (totalSeconds > 0) {
          for (const v of values) {
            const p = v / totalSeconds;
            if (p > 0) entropyBits += -p * Math.log2(p);
          }
        }
        const maxEntropy = appCount > 1 ? Math.log2(appCount) : 1;
        const normalizedEntropy = appCount > 1 ? Math.max(0, Math.min(1, entropyBits / maxEntropy)) : 0;
        const switches = switchCountForEntropy.get(workspace) || 0;
        const switchesPerHour = totalSeconds > 0 ? switches / (totalSeconds / 3600) : 0;
        return {
          id: workspace,
          label: workspaceLabel(workspace),
          totalSeconds,
          appCount,
          entropyBits,
          normalizedEntropy,
          switches,
          switchesPerHour
        };
      })
      .filter((row) => row.totalSeconds > 0)
      .sort((a, b) => compareWorkspaceIds(a.id, b.id))
      .slice(0, 18);

    return {
      coOccurrenceMatrix,
      dailyMonitorSplitRows,
      appFlowEdges,
      categoryTransitionMatrix,
      workspaceUsageRows,
      productivityPulseBins,
      switchingCostRows,
      hexbinPoints,
      triGraph,
      workspaceEntropyRows
    };
  }, [
    windowRange,
    range,
    windowEvents,
    visibleEvents,
    workspaceEvents,
    workspaceSwitchEvents,
    tabsEvents,
    appOpenEvents,
    idleEvents,
    systemEvents
  ]);

  const mixedHexDensity = useMemo<HexbinDensityMatrix>(() => {
    const points = mixedInsights.hexbinPoints.filter((p) => mixedCategoryFilter === "all" || p.category === mixedCategoryFilter);
    if (!points.length) return { cells: [], xBins: [], yBins: [], maxSamples: 0 };

    const cellMap = new Map<string, { tabsBin: number; windowsBin: number; samples: number; cpu: number[]; ram: number[] }>();
    for (const point of points) {
      const tabsBin = Math.max(0, Math.floor(point.tabsCount / 5) * 5);
      const windowsBin = Math.max(0, Math.floor(point.visibleWindows));
      const key = `${tabsBin}|${windowsBin}`;
      const cell = cellMap.get(key) || { tabsBin, windowsBin, samples: 0, cpu: [], ram: [] };
      cell.samples += 1;
      if (point.cpuPercent > 0) cell.cpu.push(point.cpuPercent);
      if (point.ramPercent > 0) cell.ram.push(point.ramPercent);
      cellMap.set(key, cell);
    }

    const cells: HexbinDensityCell[] = Array.from(cellMap.values())
      .map((cell) => ({
        id: `${cell.tabsBin}|${cell.windowsBin}`,
        tabsBin: cell.tabsBin,
        windowsBin: cell.windowsBin,
        samples: cell.samples,
        medianCpu: cell.cpu.length ? median(cell.cpu) : 0,
        medianRam: cell.ram.length ? median(cell.ram) : 0
      }))
      .sort((a, b) => a.windowsBin - b.windowsBin || a.tabsBin - b.tabsBin);

    const xBins = Array.from(new Set(cells.map((c) => c.tabsBin))).sort((a, b) => a - b);
    const yBins = Array.from(new Set(cells.map((c) => c.windowsBin))).sort((a, b) => a - b);
    const maxSamples = cells.reduce((m, c) => Math.max(m, c.samples), 0);
    return { cells, xBins, yBins, maxSamples };
  }, [mixedInsights.hexbinPoints, mixedCategoryFilter]);

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
          <DonutChart
            rows={categoriesTabsSlices}
            total={categories?.tabs_total_seconds || 0}
            title="tabs categories"
            showCenterValue={false}
          />
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

      {page === "stats" && showTopic("mixed") ? (
        <section className="card">
          <div className="cardHd">
            <h2>Gemischt</h2>
          </div>
          <div className="cardBd workspaceStack">
            <div className="split2">
              <div>
                <h3>Active + Visible Co-Occurrence</h3>
                <AppCoOccurrenceMatrixView matrix={mixedInsights.coOccurrenceMatrix} />
              </div>
              <div>
                <h3>Single vs Multi pro Tag</h3>
                <DailyMonitorSplitView rows={mixedInsights.dailyMonitorSplitRows} />
              </div>
            </div>

            <div className="split2">
              <div>
                <h3>App-Flows (Top 20)</h3>
                <AppFlowTopView edges={mixedInsights.appFlowEdges} />
              </div>
              <div>
                <h3>Category Transition Matrix</h3>
                <CategoryTransitionMatrixView matrix={mixedInsights.categoryTransitionMatrix} />
              </div>
            </div>

            <div className="split2">
              <div>
                <h3>Workspace Usage + Wechsel-Overlay</h3>
                <WorkspaceUsageOverlayView rows={mixedInsights.workspaceUsageRows} />
              </div>
              <div>
                <h3>Wechselkosten nach Workspace-Switch</h3>
                <HorizontalBars rows={mixedInsights.switchingCostRows} valueFormatter={(v) => fmtSeconds(v)} />
                <div className="sub">Stabiler Fokus = mindestens 3 Minuten in derselben App</div>
              </div>
            </div>

            <div>
              <h3>Produktivitaetspuls</h3>
              <ProductivityPulseView bins={mixedInsights.productivityPulseBins} />
            </div>

            <div className="split2">
              <div>
                <div className="mixedControlRow">
                  <h3>2D-Dichte: Tabs vs sichtbare Fenster</h3>
                  <div className="mixedControlButtons">
                    <div className="wsFilterGroup">
                      <button
                        type="button"
                        className={mixedHexMetric === "cpu" ? "pill active" : "pill"}
                        onClick={() => setMixedHexMetric("cpu")}
                      >
                        CPU
                      </button>
                      <button
                        type="button"
                        className={mixedHexMetric === "ram" ? "pill active" : "pill"}
                        onClick={() => setMixedHexMetric("ram")}
                      >
                        RAM
                      </button>
                    </div>
                    <div className="wsFilterGroup">
                      <button
                        type="button"
                        className={mixedCategoryFilter === "all" ? "pill active" : "pill"}
                        onClick={() => setMixedCategoryFilter("all")}
                      >
                        all categories
                      </button>
                      {MIXED_CATEGORY_ORDER.map((cat) => (
                        <button
                          key={`mixed-cat-${cat}`}
                          type="button"
                          className={mixedCategoryFilter === cat ? "pill active" : "pill"}
                          onClick={() => setMixedCategoryFilter(cat)}
                        >
                          {mixedCategoryLabel(cat)}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
                <HexbinDensityView matrix={mixedHexDensity} metric={mixedHexMetric} />
              </div>
              <div>
                <h3>App-Domain-Workspace Tri-Graph</h3>
                <TriGraphView graph={mixedInsights.triGraph} />
              </div>
            </div>

            <div>
              <h3>Workspace Entropy</h3>
              <WorkspaceEntropyView rows={mixedInsights.workspaceEntropyRows} />
              <div className="sub">niedrig = thematisch sauber · hoch = gemischt/chaotischer</div>
            </div>
          </div>
        </section>
      ) : null}

      {page === "stats" && showTopic("websites") ? (
        <section className="card">
          <div className="cardHd">
            <h2>Websites</h2>
          </div>
          <div className="cardBd split2">
            <div>
              <h3>Top by Time</h3>
              <div className="listScrollWrap">
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
            </div>
            <div>
              <h3>Details</h3>
              <div className="tableScrollWrap">
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
                  <div className="monitorPeriodsWrap">
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
                  </div>
                ) : (
                  <div className="empty">No monitor setup periods.</div>
                )}
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {page === "stats" && showTopic("system") ? (
        <section className="card">
          <div className="cardHd">
            <h2>System Stats</h2>
          </div>
          <div className="cardBd workspaceStack">
            <div className="split2">
              <div>
                <h3>CPU Load (%)</h3>
                <MiniLineChart points={systemInsights.cpuSeries} />
                <div className="sub" style={{ marginTop: 7 }}>
                  avg: {fmtPct(systemInsights.avgCpu)} · peak: {fmtPct(systemInsights.peakCpu)}
                </div>
              </div>
              <div>
                <h3>RAM Usage (%)</h3>
                <MiniLineChart points={systemInsights.memSeries} />
                <div className="sub" style={{ marginTop: 7 }}>
                  avg: {fmtPct(systemInsights.avgMem)} · peak: {fmtPct(systemInsights.peakMem)}
                </div>
              </div>
            </div>

            <div className="split2">
              <div>
                <h3>Network Download</h3>
                <MiniLineChart points={systemInsights.netRxSeries} />
              </div>
              <div>
                <h3>Network Upload</h3>
                <MiniLineChart points={systemInsights.netTxSeries} />
              </div>
            </div>

            <div className="split2">
              <div>
                <h3>Total Throughput</h3>
                <MiniLineChart points={systemInsights.netTotalSeries} />
                <div className="sub" style={{ marginTop: 7 }}>
                  avg: {fmtMbps(systemInsights.avgNetTotalMbps)} · peak: {fmtMbps(systemInsights.peakNetTotalMbps)}
                </div>
              </div>
              <div>
                <h3>Active Network Interfaces</h3>
                <HorizontalBars rows={systemInsights.ifaceRows} valueFormatter={(v) => fmtSeconds(v)} />
              </div>
            </div>

            <div>
              <h3>Latest Sample</h3>
              {systemInsights.latest ? (
                <table>
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>CPU</th>
                      <th>RAM</th>
                      <th>Memory</th>
                      <th>Net RX</th>
                      <th>Net TX</th>
                      <th>Net Total</th>
                      <th>Interfaces</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{fmtTs(systemInsights.latest.ts)}</td>
                      <td>{fmtPct(systemInsights.latest.cpuPercent)}</td>
                      <td>{fmtPct(systemInsights.latest.memPercent)}</td>
                      <td>
                        {fmtBytes(systemInsights.latest.memUsedBytes)} / {fmtBytes(systemInsights.latest.memTotalBytes)}
                      </td>
                      <td>{fmtMbps(systemInsights.latest.netRxMbps)}</td>
                      <td>{fmtMbps(systemInsights.latest.netTxMbps)}</td>
                      <td>{fmtMbps(systemInsights.latest.netTotalMbps)}</td>
                      <td>{systemInsights.latest.interfaces.length ? systemInsights.latest.interfaces.join(", ") : "-"}</td>
                    </tr>
                  </tbody>
                </table>
              ) : (
                <div className="empty">No system metrics in this range.</div>
              )}
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
                showCenterValue={false}
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
