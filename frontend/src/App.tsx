import { Fragment, type MouseEvent, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { SettingsPage } from "./SettingsPage";
import { TimersPage } from "./TimersPage";
import {
  applyUiSettingsSnapshot,
  getContrastMode,
  getDesignVariant,
  getTimerNotificationsEnabled,
  getTimerSoundEnabled,
  resetUiSettings,
  setContrastMode,
  setDesignVariant,
  setTimerNotificationsEnabled,
  setTimerSoundEnabled,
  type ContrastMode,
  type DesignVariant,
  type UiSettingsSnapshot
} from "./uiSettings";
import { useThemeMode } from "./useThemeMode";

type RangeKey = "24h" | "1w" | "1m" | "all";
type DayWindowMode = "rolling" | "midnight";
type PageId = "dashboard" | "stats" | "timers" | "settings";
type TopicId =
  | "all"
  | "overview"
  | "apps"
  | "categories"
  | "autotag"
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

type AutotagRunRow = {
  run_id: string;
  created_at: string;
  from_ts: string;
  to_ts: string;
  decision_count: number;
  categories_generated_sha256: string;
  pass_a_failed_batches: number;
  pass_b_failed_batches: number;
  pass_b_apply_blocked: boolean;
  pass_b_apply_block_reason: string;
  recommend_apply: boolean;
  review_gate_approved?: boolean;
};

type AutotagRunsResponse = {
  runs: AutotagRunRow[];
  latest_run_id: string;
};

type AutotagDecisionRow = {
  created_at: string;
  decision_type: string;
  entity_id: string;
  entity_type: string;
  entity: string;
  state: string;
  target_category_id: string;
  confidence: number;
  reasons: string[];
  risk_flags: string[];
};

type AutotagDecisionsResponse = {
  run_id: string;
  from_ts: string;
  to_ts: string;
  decision_count: number;
  total_decision_count: number;
  summary: {
    by_type: Record<string, number>;
    by_state: Record<string, number>;
    by_target: Record<string, number>;
    avg_confidence: number;
  };
  decisions: AutotagDecisionRow[];
};

type GeneratedCategoriesPayload = Record<string, unknown> & {
  categories?: Array<Record<string, unknown>>;
};

type AutotagReviewGate = {
  source: string;
  run_id: string;
  approved: boolean;
  approved_by: string;
  approved_at: string;
  categories_generated_sha256: string;
  allowed_category_drop_ids: string[];
};

type AutotagGeneratedResponse = {
  run_id: string;
  from_ts: string;
  to_ts: string;
  categories_generated_sha256: string;
  generated: GeneratedCategoriesPayload;
  review_gate: AutotagReviewGate;
};

type AutotagApproveResponse = {
  run_id: string;
  review_gate: AutotagReviewGate;
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

type LoadKey =
  | "summary"
  | "categories"
  | "autotag"
  | "window"
  | "workspace"
  | "workspace_switch"
  | "system"
  | "browser_tabs"
  | "window_visible";

const DEFAULT_REFRESH_MS = 30_000;
const ALL_RANGE_REFRESH_MS = 120_000;
const EVENTS_CHUNK_MS = 7 * 24 * 3600 * 1000;
const EVENTS_MAX_CHUNKS = 48;

const RANGES: Array<{ key: RangeKey; label: string }> = [
  { key: "24h", label: "24h" },
  { key: "1w", label: "1w" },
  { key: "1m", label: "1m" },
  { key: "all", label: "all" }
];

const DAY_WINDOW_MODES: Array<{ key: DayWindowMode; label: string }> = [
  { key: "rolling", label: "-24h -> jetzt" },
  { key: "midnight", label: "00:00 -> jetzt" }
];

const TOPICS: Array<{ id: TopicId; label: string }> = [
  { id: "all", label: "all" },
  { id: "overview", label: "overview" },
  { id: "apps", label: "apps" },
  { id: "categories", label: "categories" },
  { id: "autotag", label: "autotag" },
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

function requestedLoadKeys(page: PageId, topic: TopicId): Set<LoadKey> {
  if (page === "timers" || page === "settings") {
    return new Set<LoadKey>();
  }

  if (page === "dashboard") {
    return new Set<LoadKey>(["summary", "categories"]);
  }

  if (topic === "all") {
    return new Set<LoadKey>([
      "summary",
      "categories",
      "autotag",
      "window",
      "workspace",
      "workspace_switch",
      "system",
      "browser_tabs",
      "window_visible"
    ]);
  }

  if (topic === "overview" || topic === "apps") return new Set<LoadKey>(["summary"]);
  if (topic === "categories") return new Set<LoadKey>(["categories"]);
  if (topic === "autotag") return new Set<LoadKey>(["autotag"]);
  if (topic === "websites") return new Set<LoadKey>(["window"]);
  if (topic === "workspaces") return new Set<LoadKey>(["workspace", "workspace_switch"]);
  if (topic === "monitors") return new Set<LoadKey>(["workspace"]);
  if (topic === "system") return new Set<LoadKey>(["system"]);
  if (topic === "tabs") return new Set<LoadKey>(["browser_tabs"]);
  if (topic === "logs") return new Set<LoadKey>(["window_visible"]);

  return new Set<LoadKey>();
}

const ALL_TOPIC_EAGER_KEYS = new Set<LoadKey>(["summary", "categories", "autotag"]);

function splitRequestedKeysForLoad(
  page: PageId,
  topic: TopicId,
  requested: Set<LoadKey>
): { eager: Set<LoadKey>; deferred: Set<LoadKey> } {
  if (page !== "stats" || topic !== "all") {
    return { eager: requested, deferred: new Set<LoadKey>() };
  }

  const eager = new Set<LoadKey>();
  const deferred = new Set<LoadKey>();
  for (const key of requested) {
    if (ALL_TOPIC_EAGER_KEYS.has(key)) eager.add(key);
    else deferred.add(key);
  }
  return { eager, deferred };
}

function parseRangeKey(v: string | null | undefined): RangeKey {
  const s = String(v || "");
  if (s === "24h" || s === "1w" || s === "1m" || s === "all") return s;
  return "24h";
}

function startOfLocalDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function startOfLocalWeek(date: Date): Date {
  const start = startOfLocalDay(date);
  const day = start.getDay();
  const offset = (day + 6) % 7;
  start.setDate(start.getDate() - offset);
  return start;
}

function formatLocalDateKey(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function parseLocalDateKey(v: string | null | undefined): Date | null {
  const s = String(v || "").trim();
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return null;

  const y = Number(m[1]);
  const mon = Number(m[2]);
  const day = Number(m[3]);
  if (!Number.isInteger(y) || !Number.isInteger(mon) || !Number.isInteger(day)) return null;

  const parsed = new Date(y, mon - 1, day);
  if (Number.isNaN(parsed.getTime())) return null;
  if (parsed.getFullYear() !== y || parsed.getMonth() !== mon - 1 || parsed.getDate() !== day) return null;
  return parsed;
}

function normalizeDayKey(v: string | null | undefined): string | null {
  const parsed = parseLocalDateKey(v);
  if (!parsed) return null;

  const day = startOfLocalDay(parsed);
  const today = startOfLocalDay(new Date());
  if (day.getTime() > today.getTime()) return formatLocalDateKey(today);
  return formatLocalDateKey(day);
}

function currentDayKey(): string {
  return formatLocalDateKey(new Date());
}

function normalizeWeekStartKey(v: string | null | undefined): string | null {
  const parsed = parseLocalDateKey(v);
  if (!parsed) return null;
  return formatLocalDateKey(startOfLocalWeek(parsed));
}

function currentWeekStartKey(): string {
  return formatLocalDateKey(startOfLocalWeek(new Date()));
}

function formatLocalWeekKey(date: Date): string {
  const weekStart = startOfLocalWeek(date);
  const weekThursday = new Date(weekStart.getFullYear(), weekStart.getMonth(), weekStart.getDate() + 3);
  const weekYear = weekThursday.getFullYear();
  const jan4 = new Date(weekYear, 0, 4);
  const jan4Offset = (jan4.getDay() + 6) % 7;
  const week1Start = new Date(weekYear, 0, 4 - jan4Offset);
  const diffDays = Math.round((startOfLocalDay(weekStart).getTime() - startOfLocalDay(week1Start).getTime()) / 86400_000);
  const week = Math.floor(diffDays / 7) + 1;
  return `${weekYear}-W${String(week).padStart(2, "0")}`;
}

function parseLocalWeekKey(v: string | null | undefined): Date | null {
  const s = String(v || "").trim();
  const m = s.match(/^(\d{4})-W(\d{2})$/i);
  if (!m) return null;

  const y = Number(m[1]);
  const week = Number(m[2]);
  if (!Number.isInteger(y) || !Number.isInteger(week) || week < 1 || week > 53) return null;

  const jan4 = new Date(y, 0, 4);
  const jan4Offset = (jan4.getDay() + 6) % 7;
  const week1Start = new Date(y, 0, 4 - jan4Offset);
  const parsed = new Date(week1Start.getTime());
  parsed.setDate(parsed.getDate() + (week - 1) * 7);
  if (Number.isNaN(parsed.getTime())) return null;

  const normalized = formatLocalWeekKey(parsed);
  if (normalized.toUpperCase() !== `${y}-W${String(week).padStart(2, "0")}`.toUpperCase()) return null;
  return startOfLocalWeek(parsed);
}

function normalizeWeekSelectionKey(v: string | null | undefined): string | null {
  const dateKey = normalizeWeekStartKey(v);
  if (dateKey) return dateKey;
  const parsedWeek = parseLocalWeekKey(v);
  if (!parsedWeek) return null;
  return formatLocalDateKey(startOfLocalWeek(parsedWeek));
}

function startOfLocalMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function formatLocalMonthKey(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

function parseLocalMonthKey(v: string | null | undefined): Date | null {
  const s = String(v || "").trim();
  const m = s.match(/^(\d{4})-(\d{2})$/);
  if (!m) return null;

  const y = Number(m[1]);
  const mon = Number(m[2]);
  if (!Number.isInteger(y) || !Number.isInteger(mon)) return null;

  const parsed = new Date(y, mon - 1, 1);
  if (Number.isNaN(parsed.getTime())) return null;
  if (parsed.getFullYear() !== y || parsed.getMonth() !== mon - 1) return null;
  return parsed;
}

function normalizeMonthKey(v: string | null | undefined): string | null {
  const parsed = parseLocalMonthKey(v);
  if (!parsed) return null;
  return formatLocalMonthKey(parsed);
}

function currentMonthKey(): string {
  return formatLocalMonthKey(new Date());
}

function weekRangeLabel(start: Date): string {
  const end = new Date(start.getTime());
  end.setDate(end.getDate() + 6);
  const fmt = (d: Date) => d.toLocaleDateString(undefined, { month: "2-digit", day: "2-digit" });
  return `${fmt(start)} -> ${fmt(end)}`;
}

function monthRangeLabel(start: Date): string {
  return start.toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

function parseDayWindowMode(v: string | null | undefined): DayWindowMode {
  const s = String(v || "").toLowerCase();
  if (s === "midnight") return "midnight";
  return "rolling";
}

function parseTopicId(v: string | null | undefined): TopicId {
  const s = String(v || "");
  if (
    s === "all" ||
    s === "overview" ||
    s === "apps" ||
    s === "categories" ||
    s === "autotag" ||
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

function parsePageId(pathname: string): PageId {
  const p = String(pathname || "").replace(/\/+$/, "");
  if (p.endsWith("/ui/stats")) return "stats";
  if (p.endsWith("/ui/timers")) return "timers";
  if (p.endsWith("/ui/settings")) return "settings";
  return "dashboard";
}

function pathPrefixBeforeUi(pathname: string): string {
  const p = String(pathname || "");
  const m = p.match(/^(.*)\/ui(?:\/.*)?$/);
  if (!m) return "";
  return m[1] || "";
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

function appDisplayName(raw: string): string {
  const value = String(raw || "").trim();
  if (!value || !value.includes(".")) return value;
  if (/\s/.test(value)) return value;
  const parts = value.split(".").filter(Boolean);
  if (parts.length < 2) return value;
  return parts[parts.length - 1] || value;
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

function parseTimeWindow(window: TimeWindow): { fromMs: number; toMs: number } | null {
  const fromMs = Date.parse(window.from);
  const toMs = Date.parse(window.to);
  if (Number.isNaN(fromMs) || Number.isNaN(toMs) || toMs <= fromMs) return null;
  return { fromMs, toMs };
}

function splitTimeWindow(window: TimeWindow, targetChunkMs: number): TimeWindow[] {
  const parsed = parseTimeWindow(window);
  if (!parsed) return [window];

  const chunkMs = Math.max(60_000, Math.round(targetChunkMs));
  const out: TimeWindow[] = [];
  for (let cursor = parsed.fromMs; cursor < parsed.toMs; cursor += chunkMs) {
    const end = Math.min(parsed.toMs, cursor + chunkMs);
    out.push({ from: new Date(cursor).toISOString(), to: new Date(end).toISOString() });
  }
  return out.length ? out : [window];
}

function eventDedupeKey(event: ApiEvent): string {
  if (typeof event.id === "number") return `id:${event.id}`;
  const dataJson = JSON.stringify(event.data || {});
  return `${event.source || ""}|${event.start_ts}|${event.end_ts}|${dataJson}`;
}

async function fetchEventsBucketChunked(apiBase: string, bucket: string, window: TimeWindow): Promise<ApiEvent[]> {
  const parsed = parseTimeWindow(window);
  if (!parsed) {
    const value = await fetchJson<EventsResponse>(`${apiBase}/events?bucket=${encodeURIComponent(bucket)}&${qs(window)}`);
    return Array.isArray(value.events) ? value.events : [];
  }

  const durationMs = parsed.toMs - parsed.fromMs;
  let chunkMs = EVENTS_CHUNK_MS;
  const minChunkMsByCount = Math.ceil(durationMs / EVENTS_MAX_CHUNKS);
  if (minChunkMsByCount > chunkMs) chunkMs = minChunkMsByCount;

  const chunks = splitTimeWindow(window, chunkMs);
  const rows: ApiEvent[] = [];
  const seen = new Set<string>();

  for (const chunk of chunks) {
    const value = await fetchJson<EventsResponse>(`${apiBase}/events?bucket=${encodeURIComponent(bucket)}&${qs(chunk)}`);
    const events = Array.isArray(value.events) ? value.events : [];
    for (const event of events) {
      const key = eventDedupeKey(event);
      if (seen.has(key)) continue;
      seen.add(key);
      rows.push(event);
    }
  }

  rows.sort((a, b) => {
    if (a.start_ts === b.start_ts) return String(a.end_ts || "").localeCompare(String(b.end_ts || ""));
    return String(a.start_ts || "").localeCompare(String(b.start_ts || ""));
  });
  return rows;
}

function parseIdList(raw: string): string[] {
  const parts = String(raw || "").split(/[\n,]/g);
  const out: string[] = [];
  const seen = new Set<string>();
  for (const part of parts) {
    const value = String(part || "").trim().toLowerCase();
    if (!value || seen.has(value)) continue;
    seen.add(value);
    out.push(value);
  }
  return out;
}

function nowIso(): string {
  return new Date().toISOString();
}

function addMs(iso: string, deltaMs: number): string {
  const d = new Date(iso);
  return new Date(d.getTime() + deltaMs).toISOString();
}

async function resolveWindow(
  range: RangeKey,
  dayWindowMode: DayWindowMode,
  page: PageId,
  topic: TopicId,
  apiBase: string,
  statsDayKey: string,
  statsWeekStart: string,
  statsMonthKey: string
): Promise<TimeWindow> {
  const to = nowIso();
  if (range === "24h") {
    if (page === "stats" && dayWindowMode === "midnight") {
      const now = new Date();
      const today = startOfLocalDay(now);
      const selectedDate = parseLocalDateKey(statsDayKey);
      let fromLocal = startOfLocalDay(selectedDate || now);
      if (fromLocal.getTime() > today.getTime()) {
        fromLocal = today;
      }

      const dayEnd = new Date(fromLocal.getTime());
      dayEnd.setDate(dayEnd.getDate() + 1);
      const toDate = now.getTime() < dayEnd.getTime() ? now : dayEnd;
      return { from: fromLocal.toISOString(), to: toDate.toISOString() };
    }

    if (dayWindowMode === "midnight") {
      const now = new Date();
      const fromLocal = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      return { from: fromLocal.toISOString(), to };
    }
    return { from: addMs(to, -24 * 3600 * 1000), to };
  }
  if (range === "1w") {
    if (page === "stats") {
      const now = new Date();
      const currentWeekStart = startOfLocalWeek(now);
      const selectedDate = parseLocalDateKey(statsWeekStart);
      let weekStart = startOfLocalWeek(selectedDate || now);
      if (weekStart.getTime() > currentWeekStart.getTime()) {
        weekStart = currentWeekStart;
      }

      const weekEnd = new Date(weekStart.getTime());
      weekEnd.setDate(weekEnd.getDate() + 7);
      const weekTo = now.getTime() < weekEnd.getTime() ? now : weekEnd;

      return {
        from: weekStart.toISOString(),
        to: weekTo.toISOString()
      };
    }
    return { from: addMs(to, -7 * 24 * 3600 * 1000), to };
  }
  if (range === "1m") {
    if (page === "stats") {
      const now = new Date();
      const currentMonthStart = startOfLocalMonth(now);
      const selectedMonth = parseLocalMonthKey(statsMonthKey);
      let monthStart = startOfLocalMonth(selectedMonth || now);
      if (monthStart.getTime() > currentMonthStart.getTime()) {
        monthStart = currentMonthStart;
      }

      const monthEnd = new Date(monthStart.getFullYear(), monthStart.getMonth() + 1, 1);
      const monthTo = now.getTime() < monthEnd.getTime() ? now : monthEnd;
      return {
        from: monthStart.toISOString(),
        to: monthTo.toISOString()
      };
    }

    return { from: addMs(to, -30 * 24 * 3600 * 1000), to };
  }

  let rangeBucket: string | null = null;
  if (page === "dashboard") {
    rangeBucket = "window";
  } else if (page === "stats") {
    if (topic === "overview" || topic === "apps" || topic === "categories" || topic === "websites") {
      rangeBucket = "window";
    } else if (topic === "workspaces" || topic === "monitors") {
      rangeBucket = "workspace";
    } else if (topic === "system") {
      rangeBucket = "system";
    } else if (topic === "tabs") {
      rangeBucket = "browser_tabs";
    } else if (topic === "logs") {
      rangeBucket = "window_visible";
    } else {
      rangeBucket = null;
    }
  }

  const rangeUrl = rangeBucket
    ? `${apiBase}/range?bucket=${encodeURIComponent(rangeBucket)}`
    : `${apiBase}/range`;
  const res = await fetch(rangeUrl, { cache: "no-store" });
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

async function postJson<T>(url: string, payload: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    let detail = "";
    try {
      const body = (await res.json()) as { detail?: unknown };
      detail = asString(body?.detail);
    } catch {
      detail = "";
    }
    if (detail) throw new Error(`${url} -> HTTP ${res.status}: ${detail}`);
    throw new Error(`${url} -> HTTP ${res.status}`);
  }
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

function LegacyTimeline({
  chunks,
  range,
  fromTs,
  toTs,
  showNowMarker
}: {
  chunks: TimelineChunk[];
  range: RangeKey;
  fromTs: string;
  toTs: string;
  showNowMarker: boolean;
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
        entry.top_app ? ` · top ${appDisplayName(entry.top_app)}` : ""
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

  let timelineEntries = entries;
  if (range === "24h" && entries.length > 0 && entries.length < 24) {
    const fromMs = Date.parse(fromTs);
    const fromDt = new Date(fromTs);
    const startsAtMidnightLocal =
      !Number.isNaN(fromMs) &&
      !Number.isNaN(fromDt.getTime()) &&
      fromDt.getHours() === 0 &&
      fromDt.getMinutes() === 0 &&
      fromDt.getSeconds() === 0;
    const isHourlyChunk = inferredChunkSeconds >= 3300 && inferredChunkSeconds <= 3900;
    if (startsAtMidnightLocal && isHourlyChunk) {
      const padded = [...entries];
      for (let i = entries.length; i < 24; i++) {
        const startMs = fromMs + i * 3600_000;
        const endMs = startMs + 3600_000;
        padded.push({
          idx: i,
          start_ts: new Date(startMs).toISOString(),
          end_ts: new Date(endMs).toISOString(),
          active_seconds: 0,
          afk_seconds: 0,
          unknown_seconds: 0,
          active: 0,
          afk: 0,
          off: 0,
          activePct: 0,
          afkPct: 0,
          top_app: null
        });
      }
      timelineEntries = padded;
    }
  }

  const avgActivePct =
    entries.length > 0 ? entries.reduce((sum, e) => sum + e.activePct, 0) / entries.length : 0;
  const avgActiveHours = entries.length > 0 ? entries.reduce((sum, e) => sum + e.active, 0) / entries.length / 3600 : 0;
  const peak = entries.reduce((best, e) => (best == null || e.active > best.active ? e : best), null as
    | (typeof entries)[number]
    | null);
  const peakActiveHours = peak ? peak.active / 3600 : 0;

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
  if (range === "24h") {
    const chunk = Math.max(1, Math.round(inferredChunkSeconds));
    infoBase = chunk >= 3600 ? `per ${Math.round(chunk / 3600)}h` : "per hour";
  }
  else if (range === "1w" || range === "1m") infoBase = "per day";
  else {
    const chunk = Math.max(1, Math.round(inferredChunkSeconds));
    if (chunk >= 86400) infoBase = `per ${Math.round(chunk / 86400)}d`;
    else if (chunk >= 3600) infoBase = `per ${Math.round(chunk / 3600)}h`;
    else infoBase = `per ${Math.max(1, Math.round(chunk / 60))}m`;
  }

  const peakLeftPct = peak && timelineEntries.length > 0 ? ((peak.idx + 0.5) / timelineEntries.length) * 100 : 0;
  let nowLeftPct: number | null = null;
  if (showNowMarker) {
    const axisFromMs = Date.parse(timelineEntries[0]?.start_ts || "");
    const axisToMs = Date.parse(timelineEntries[timelineEntries.length - 1]?.end_ts || "");
    const fallbackFromMs = Date.parse(fromTs);
    const fallbackToMs = Date.parse(toTs);
    const fromMs = !Number.isNaN(axisFromMs) ? axisFromMs : fallbackFromMs;
    const toMs = !Number.isNaN(axisToMs) ? axisToMs : fallbackToMs;
    const nowMs = Date.now();
    if (!Number.isNaN(fromMs) && !Number.isNaN(toMs) && toMs > fromMs) {
      const ratio = (nowMs - fromMs) / (toMs - fromMs);
      nowLeftPct = Math.max(0, Math.min(100, ratio * 100));
    }
  }

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
          {showNowMarker ? (
            <span className="legendItemLegacy">
              <span className="legendDotLegacy" style={{ background: "rgba(34,197,94,.92)" }} />
              Jetzt
            </span>
          ) : null}
        </div>
      </div>
      <div className="sub timelineInfoLegacy">
        {infoBase} · avg {fmtHours(avgActiveHours)} · peak {fmtHours(peakActiveHours)}
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
          {nowLeftPct != null ? <div className="timelineNowLegacy" style={{ left: `${nowLeftPct}%` }} /> : null}
          <div className="timelineLegacy">
            {timelineEntries.map((e) => (
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
        {timelineEntries.map((e, i) => (
          <span key={`${e.start_ts}-lbl`}>{showLabel(i, timelineEntries.length) ? labelText(e.start_ts) : ""}</span>
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
  const page: PageId = parsePageId(pathname);
  const searchParams = new URLSearchParams(String(window.location.search || ""));
  const uiPrefix = pathPrefixBeforeUi(pathname);
  const uiBase = `${uiPrefix}/ui`;
  const apiBase = `${uiPrefix}/v1`;
  const initialRange = parseRangeKey(searchParams.get("range"));
  const initialTopic = parseTopicId(searchParams.get("topic"));
  const initialDayWindowMode =
    page === "dashboard" ? "midnight" : parseDayWindowMode(searchParams.get("day_window"));
  const initialStatsDayKey = normalizeDayKey(searchParams.get("day")) || currentDayKey();
  const initialStatsWeekStart = normalizeWeekSelectionKey(searchParams.get("week_start")) || currentWeekStartKey();
  const initialStatsMonthKey = normalizeMonthKey(searchParams.get("month")) || currentMonthKey();

  const [range, setRange] = useState<RangeKey>(initialRange);
  const [topic, setTopic] = useState<TopicId>(initialTopic);
  const [dayWindowMode, setDayWindowMode] = useState<DayWindowMode>(initialDayWindowMode);
  const [statsDayKey, setStatsDayKey] = useState(initialStatsDayKey);
  const [statsWeekStart, setStatsWeekStart] = useState(initialStatsWeekStart);
  const [statsMonthKey, setStatsMonthKey] = useState(initialStatsMonthKey);
  const [monitorSetupFilter, setMonitorSetupFilter] = useState<MonitorSetupFilter>("all");
  const [reloadKey, setReloadKey] = useState(0);
  const [themeMode, onThemeModeChange] = useThemeMode();
  const [contrastMode, setContrastModeState] = useState<ContrastMode>(() => getContrastMode());
  const [designVariant, setDesignVariantState] = useState<DesignVariant>(() => getDesignVariant());
  const [timerNotifications, setTimerNotificationsState] = useState(() => getTimerNotificationsEnabled());
  const [timerSound, setTimerSoundState] = useState(() => getTimerSoundEnabled());

  useEffect(() => {
    if (typeof document === "undefined") return;
    document.body.classList.toggle("theme-high-contrast", contrastMode === "high");
  }, [contrastMode]);

  useLayoutEffect(() => {
    if (typeof document === "undefined") return;
    document.body.classList.toggle("design-terminal", designVariant === "terminal");
  }, [designVariant]);

  function onContrastModeChange(next: ContrastMode): void {
    setContrastModeState(next);
    setContrastMode(next);
  }

  function onDesignVariantChange(next: DesignVariant): void {
    setDesignVariantState(next);
    setDesignVariant(next);
  }

  function onTimerNotificationsChange(enabled: boolean): void {
    setTimerNotificationsState(enabled);
    setTimerNotificationsEnabled(enabled);
  }

  function onTimerSoundChange(enabled: boolean): void {
    setTimerSoundState(enabled);
    setTimerSoundEnabled(enabled);
  }

  function syncSettings(next: UiSettingsSnapshot): void {
    onThemeModeChange(next.themeMode);
    onContrastModeChange(next.contrastMode);
    onDesignVariantChange(next.designVariant);
    onTimerNotificationsChange(next.timerNotifications);
    onTimerSoundChange(next.timerSound);
  }

  function onSettingsChange(patch: Partial<UiSettingsSnapshot>): void {
    if (patch.themeMode) onThemeModeChange(patch.themeMode);
    if (patch.contrastMode) onContrastModeChange(patch.contrastMode);
    if (patch.designVariant) onDesignVariantChange(patch.designVariant);
    if (typeof patch.timerNotifications === "boolean") onTimerNotificationsChange(patch.timerNotifications);
    if (typeof patch.timerSound === "boolean") onTimerSoundChange(patch.timerSound);
  }

  function onSettingsImport(payload: unknown): void {
    const resolved =
      payload && typeof payload === "object" && !Array.isArray(payload) && "settings" in payload
        ? (payload as { settings: unknown }).settings
        : payload;
    const imported = applyUiSettingsSnapshot(resolved);
    syncSettings(imported);
  }

  function onSettingsReset(): void {
    const defaults = resetUiSettings();
    syncSettings(defaults);
  }

  const uiSettings = useMemo<UiSettingsSnapshot>(
    () => ({
      themeMode,
      contrastMode,
      designVariant,
      timerNotifications,
      timerSound
    }),
    [themeMode, contrastMode, designVariant, timerNotifications, timerSound]
  );

  const loadParamsRef = useRef<{
    page: PageId;
    topic: TopicId;
    range: RangeKey;
    dayWindowMode: DayWindowMode;
    statsDayKey: string;
    statsWeekStart: string;
    statsMonthKey: string;
    reloadKey: number;
    autotagRunId: string;
    apiBase: string;
  } | null>(null);

  function replaceQuery(
    nextRange: RangeKey,
    nextTopic: TopicId,
    nextDayWindowMode: DayWindowMode,
    nextStatsDayKey: string,
    nextStatsWeekStart: string,
    nextStatsMonthKey: string
  ): void {
    const params = new URLSearchParams(String(window.location.search || ""));
    params.set("range", nextRange);
    if (page === "stats") params.set("topic", nextTopic);
    else params.delete("topic");
    if (nextRange === "24h" && nextDayWindowMode === "midnight") params.set("day_window", "midnight");
    else params.delete("day_window");
    if (page === "stats" && nextRange === "24h" && nextDayWindowMode === "midnight") params.set("day", nextStatsDayKey);
    else params.delete("day");
    if (page === "stats" && nextRange === "1w") params.set("week_start", nextStatsWeekStart);
    else params.delete("week_start");
    if (page === "stats" && nextRange === "1m") params.set("month", nextStatsMonthKey);
    else params.delete("month");
    const query = params.toString();
    const nextUrl = `${window.location.pathname}${query ? `?${query}` : ""}`;
    window.history.replaceState(null, "", nextUrl);
  }

  function onRangeChange(next: RangeKey): void {
    setRange(next);
    replaceQuery(next, topic, dayWindowMode, statsDayKey, statsWeekStart, statsMonthKey);
  }

  function onTopicChange(next: TopicId): void {
    setTopic(next);
    replaceQuery(range, next, dayWindowMode, statsDayKey, statsWeekStart, statsMonthKey);
  }

  function onDayWindowModeChange(next: DayWindowMode): void {
    setDayWindowMode(next);
    replaceQuery(range, topic, next, statsDayKey, statsWeekStart, statsMonthKey);
  }

  function onStatsDayChange(next: string): void {
    const normalized = normalizeDayKey(next) || currentDayKey();
    setStatsDayKey(normalized);
    replaceQuery(range, topic, dayWindowMode, normalized, statsWeekStart, statsMonthKey);
  }

  function onStatsWeekChange(next: string): void {
    const normalized = normalizeWeekSelectionKey(next);
    if (!normalized) return;
    setStatsWeekStart(normalized);
    replaceQuery(range, topic, dayWindowMode, statsDayKey, normalized, statsMonthKey);
  }

  function onStatsMonthChange(next: string): void {
    const normalized = normalizeMonthKey(next) || currentMonthKey();
    setStatsMonthKey(normalized);
    replaceQuery(range, topic, dayWindowMode, statsDayKey, statsWeekStart, normalized);
  }

  function hrefFor(target: PageId): string {
    const params = new URLSearchParams();
    params.set("range", range);
    if (target === "stats") params.set("topic", topic);
    if (range === "24h" && dayWindowMode === "midnight") params.set("day_window", "midnight");
    if (target === "stats" && range === "24h" && dayWindowMode === "midnight") params.set("day", statsDayKey);
    if (target === "stats" && range === "1w") params.set("week_start", statsWeekStart);
    if (target === "stats" && range === "1m") params.set("month", statsMonthKey);
    const qs = params.toString();
    if (target === "dashboard") return `${uiBase}${qs ? `?${qs}` : ""}`;
    if (target === "stats") return `${uiBase}/stats${qs ? `?${qs}` : ""}`;
    if (target === "timers") return `${uiBase}/timers${qs ? `?${qs}` : ""}`;
    return `${uiBase}/settings${qs ? `?${qs}` : ""}`;
  }

  const [windowRange, setWindowRange] = useState<TimeWindow | null>(null);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [categories, setCategories] = useState<CategoriesResponse | null>(null);
  const [autotagRuns, setAutotagRuns] = useState<AutotagRunRow[]>([]);
  const [autotagDecisions, setAutotagDecisions] = useState<AutotagDecisionsResponse | null>(null);
  const [autotagGenerated, setAutotagGenerated] = useState<AutotagGeneratedResponse | null>(null);
  const [autotagRunId, setAutotagRunId] = useState("");
  const [autotagApprovedBy, setAutotagApprovedBy] = useState("");
  const [autotagAllowedDropIds, setAutotagAllowedDropIds] = useState("");
  const [autotagApprovePending, setAutotagApprovePending] = useState(false);
  const [autotagApproveError, setAutotagApproveError] = useState("");
  const [autotagApproveNote, setAutotagApproveNote] = useState("");
  const [windowEvents, setWindowEvents] = useState<ApiEvent[]>([]);
  const [workspaceEvents, setWorkspaceEvents] = useState<ApiEvent[]>([]);
  const [workspaceSwitchEvents, setWorkspaceSwitchEvents] = useState<ApiEvent[]>([]);
  const [systemEvents, setSystemEvents] = useState<ApiEvent[]>([]);
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
    if (page === "timers" || page === "settings") {
      setLoading(false);
      setError("");
      return;
    }

    let cancelled = false;
    let timer: number | null = null;
    let activeLoadId = 0;
    let loadInFlight = false;

    const refreshMs = range === "all" ? ALL_RANGE_REFRESH_MS : DEFAULT_REFRESH_MS;
    const previousLoad = loadParamsRef.current;
    const baseRequested = requestedLoadKeys(page, topic);
    const runSwitchOnly =
      previousLoad != null &&
      previousLoad.page === page &&
      previousLoad.topic === topic &&
      previousLoad.range === range &&
      previousLoad.dayWindowMode === dayWindowMode &&
      previousLoad.statsDayKey === statsDayKey &&
      previousLoad.statsWeekStart === statsWeekStart &&
      previousLoad.statsMonthKey === statsMonthKey &&
      previousLoad.reloadKey === reloadKey &&
      previousLoad.apiBase === apiBase &&
      previousLoad.autotagRunId !== autotagRunId;
    const requested =
      runSwitchOnly && baseRequested.has("autotag")
        ? new Set<LoadKey>(["autotag"])
        : baseRequested;
    const { eager: eagerRequested, deferred: deferredRequested } = splitRequestedKeysForLoad(page, topic, requested);

    loadParamsRef.current = {
      page,
      topic,
      range,
      dayWindowMode,
      statsDayKey,
      statsWeekStart,
      statsMonthKey,
      reloadKey,
      autotagRunId,
      apiBase
    };

    async function load() {
      if (loadInFlight) return;
      loadInFlight = true;
      const loadId = activeLoadId + 1;
      activeLoadId = loadId;

      if (!cancelled) setLoading(true);
      const errors: string[] = [];

      try {
        let query = "";
        let summaryQuery = "";
        let timeWindow: TimeWindow | null = null;
        if (!(requested.size === 1 && requested.has("autotag"))) {
          const effectiveDayWindowMode = page === "dashboard" ? "midnight" : dayWindowMode;
          timeWindow = await resolveWindow(
            range,
            effectiveDayWindowMode,
            page,
            topic,
            apiBase,
            statsDayKey,
            statsWeekStart,
            statsMonthKey
          );
          if (cancelled || loadId !== activeLoadId) return;
          setWindowRange(timeWindow);

          query = qs(timeWindow);
          const fromMs = Date.parse(timeWindow.from);
          const toMs = Date.parse(timeWindow.to);
          const durationSeconds =
            !Number.isNaN(fromMs) && !Number.isNaN(toMs) && toMs > fromMs ? (toMs - fromMs) / 1000 : 0;
          const chunkSeconds =
            page === "dashboard" && range === "24h" && effectiveDayWindowMode === "midnight"
              ? 3600
              : chunkSecondsForRange(range, durationSeconds);
          summaryQuery = `${query}&chunk_seconds=${chunkSeconds}`;
        }

        async function runBatch(keys: Set<LoadKey>): Promise<void> {
          if (!keys.size) return;

          const pending: Array<Promise<void>> = [];

          function queue<T>(label: string, url: string, apply: (value: T) => void): void {
            const p = fetchJson<T>(url)
              .then((value) => {
                if (cancelled || loadId !== activeLoadId) return;
                apply(value);
              })
              .catch((e) => {
                errors.push(`${label}: ${String(e)}`);
              });
            pending.push(p);
          }

          function queueEvents(
            label: string,
            bucket: string,
            apply: (events: ApiEvent[]) => void
          ): void {
            if (!timeWindow) {
              errors.push(`${label}: missing time window`);
              return;
            }
            const p = fetchEventsBucketChunked(apiBase, bucket, timeWindow)
              .then((events) => {
                if (cancelled || loadId !== activeLoadId) return;
                apply(events);
              })
              .catch((e) => {
                errors.push(`${label}: ${String(e)}`);
              });
            pending.push(p);
          }

          if (keys.has("summary")) {
            queue<SummaryResponse>(
              "summary",
              `${apiBase}/summary?${summaryQuery}&include_timeline=false`,
              (value) => setSummary(value)
            );
          }
          if (keys.has("categories")) {
            queue<CategoriesResponse>(
              "categories",
              `${apiBase}/categories?mode=auto&${query}`,
              (value) => setCategories(value)
            );
          }
          if (keys.has("autotag")) {
            const p = fetchJson<AutotagRunsResponse>(`${apiBase}/autotag/runs?limit=100`)
              .then(async (runsValue) => {
                if (cancelled || loadId !== activeLoadId) return;
                const runs = Array.isArray(runsValue?.runs) ? runsValue.runs : [];
                setAutotagRuns(runs);

                const selectedRunId = runs.some((row) => row.run_id === autotagRunId)
                  ? autotagRunId
                  : String(runsValue?.latest_run_id || runs[0]?.run_id || "");

                if (selectedRunId !== autotagRunId) {
                  setAutotagRunId(selectedRunId);
                }

                if (!selectedRunId) {
                  setAutotagDecisions(null);
                  setAutotagGenerated(null);
                  return;
                }

                const decisionsUrl = `${apiBase}/autotag/decisions?run_id=${encodeURIComponent(selectedRunId)}&limit=600`;
                try {
                  const decisionsValue = await fetchJson<AutotagDecisionsResponse>(decisionsUrl);
                  if (cancelled || loadId !== activeLoadId) return;
                  setAutotagDecisions(decisionsValue);
                } catch (e) {
                  errors.push(`autotag decisions: ${String(e)}`);
                }

                const generatedUrl = `${apiBase}/autotag/generated?run_id=${encodeURIComponent(selectedRunId)}`;
                try {
                  const generatedValue = await fetchJson<AutotagGeneratedResponse>(generatedUrl);
                  if (cancelled || loadId !== activeLoadId) return;
                  setAutotagGenerated(generatedValue);
                } catch (e) {
                  errors.push(`autotag generated: ${String(e)}`);
                }
              })
              .catch((e) => {
                errors.push(`autotag runs: ${String(e)}`);
              });
            pending.push(p);
          }
          if (keys.has("window")) {
            queueEvents(
              "window",
              "window",
              (events) => setWindowEvents(events)
            );
          }
          if (keys.has("workspace")) {
            queueEvents(
              "workspace",
              "workspace",
              (events) => setWorkspaceEvents(events)
            );
          }
          if (keys.has("workspace_switch")) {
            queueEvents(
              "workspace_switch",
              "workspace_switch",
              (events) => setWorkspaceSwitchEvents(events)
            );
          }
          if (keys.has("system")) {
            queueEvents(
              "system",
              "system",
              (events) => setSystemEvents(events)
            );
          }
          if (keys.has("browser_tabs")) {
            queueEvents(
              "browser_tabs",
              "browser_tabs",
              (events) => setTabsEvents(events)
            );
          }
          if (keys.has("window_visible")) {
            queueEvents(
              "window_visible",
              "window_visible",
              (events) => setVisibleEvents(events)
            );
          }

          await Promise.all(pending);
        }

        await runBatch(eagerRequested);
        if (cancelled || loadId !== activeLoadId) return;

        if (deferredRequested.size > 0) {
          setError(errors.join(" | "));
          setUpdatedAt(new Date().toLocaleTimeString());
          setLoading(false);

          await new Promise<void>((resolve) => {
            window.setTimeout(resolve, 0);
          });
          if (cancelled || loadId !== activeLoadId) return;

          const deferredStages: Array<LoadKey[]> = [
            ["window_visible", "workspace_switch"],
            ["window", "workspace"],
            ["system", "browser_tabs"]
          ];
          const handledKeys = new Set<LoadKey>();
          for (const stageKeys of deferredStages) {
            const stage = new Set<LoadKey>();
            for (const key of stageKeys) {
              if (!deferredRequested.has(key)) continue;
              stage.add(key);
              handledKeys.add(key);
            }
            if (!stage.size) continue;

            await runBatch(stage);
            if (cancelled || loadId !== activeLoadId) return;

            await new Promise<void>((resolve) => {
              window.setTimeout(resolve, 0);
            });
            if (cancelled || loadId !== activeLoadId) return;
          }

          const deferredRemaining = new Set<LoadKey>();
          for (const key of deferredRequested) {
            if (!handledKeys.has(key)) deferredRemaining.add(key);
          }
          if (deferredRemaining.size > 0) {
            await runBatch(deferredRemaining);
          }
          if (cancelled || loadId !== activeLoadId) return;
        }

        setError(errors.join(" | "));
        setUpdatedAt(new Date().toLocaleTimeString());
      } catch (e) {
        if (cancelled || loadId !== activeLoadId) return;
        setError(String(e));
      } finally {
        if (!cancelled && loadId === activeLoadId) {
          setLoading(false);
        }
        loadInFlight = false;
      }
    }

    void load();
    timer = window.setInterval(() => void load(), refreshMs);

    return () => {
      cancelled = true;
      if (timer != null) window.clearInterval(timer);
    };
  }, [page, topic, range, dayWindowMode, statsDayKey, statsWeekStart, statsMonthKey, reloadKey, autotagRunId, apiBase]);

  useEffect(() => {
    const runId = String(autotagGenerated?.run_id || "");
    if (!runId) {
      setAutotagApprovedBy("");
      setAutotagAllowedDropIds("");
      setAutotagApproveError("");
      setAutotagApproveNote("");
      return;
    }
    const gate = autotagGenerated?.review_gate;
    const allowedDropIds = Array.isArray(gate?.allowed_category_drop_ids)
      ? gate.allowed_category_drop_ids
      : [];
    setAutotagApprovedBy(String(gate?.approved_by || ""));
    setAutotagAllowedDropIds(allowedDropIds.join(", "));
    setAutotagApproveError("");
    setAutotagApproveNote("");
  }, [autotagGenerated?.run_id]);

  const topApps = useMemo(() => {
    if (!summary) return [] as SummaryApp[];
    return [...(summary.top_apps || [])].sort((a, b) => (b.seconds || 0) - (a.seconds || 0)).slice(0, 20);
  }, [summary]);

  const activitySlices = useMemo<SliceRow[]>(() => {
    if (!summary) return [];

    const activeAppItems = topApps.slice(0, 8).map((a) => ({
      label: appDisplayName(a.app),
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
        const app = trimLabel(appDisplayName(String(chunk.top_app || "unknown")), 84);
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
      if (!Number.isFinite(count)) continue;
      count = Math.max(0, count);

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
        app: appDisplayName(asString(e?.data?.app)),
        title: asString(e?.data?.title),
        workspace: asString(e?.data?.workspace),
        monitor: asString(e?.data?.monitor)
      });
    }
    rows.sort((a, b) => b.end.localeCompare(a.end));
    return rows.slice(0, 40);
  }, [visibleEvents]);

  const autotagCurrentRun = useMemo(() => {
    if (!autotagRuns.length) return null;
    return autotagRuns.find((row) => row.run_id === autotagRunId) || autotagRuns[0] || null;
  }, [autotagRuns, autotagRunId]);

  const autotagStateRows = useMemo<BarRow[]>(() => {
    const byState = autotagDecisions?.summary?.by_state || {};
    return Object.entries(byState)
      .map(([key, value]) => ({
        id: key,
        label: key || "unknown",
        value: Number(value) || 0,
        sub: "decisions"
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 12);
  }, [autotagDecisions]);

  const autotagTypeRows = useMemo<BarRow[]>(() => {
    const byType = autotagDecisions?.summary?.by_type || {};
    return Object.entries(byType)
      .map(([key, value]) => ({
        id: key,
        label: key || "unknown",
        value: Number(value) || 0,
        sub: "decisions"
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 12);
  }, [autotagDecisions]);

  const autotagTopTargets = useMemo(() => {
    const byTarget = autotagDecisions?.summary?.by_target || {};
    return Object.entries(byTarget)
      .map(([key, value]) => ({ id: key, label: key, value: Number(value) || 0 }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
  }, [autotagDecisions]);

  const autotagGeneratedJson = useMemo(() => {
    if (!autotagGenerated) return "";
    try {
      return JSON.stringify(autotagGenerated.generated || {}, null, 2);
    } catch {
      return "";
    }
  }, [autotagGenerated]);

  const autotagGeneratedCategoryCount = useMemo(() => {
    const categories = autotagGenerated?.generated?.categories;
    return Array.isArray(categories) ? categories.length : 0;
  }, [autotagGenerated]);

  const autotagReviewGate = autotagGenerated?.review_gate || null;

  const autotagReviewSummary = useMemo(() => {
    if (!autotagReviewGate) return "review gate: missing";
    if (autotagReviewGate.approved) {
      const by = String(autotagReviewGate.approved_by || "").trim() || "unknown";
      const at = String(autotagReviewGate.approved_at || "").trim();
      return at ? `review gate: approved by ${by} at ${fmtTs(at)}` : `review gate: approved by ${by}`;
    }
    return "review gate: pending approval";
  }, [autotagReviewGate]);

  async function approveAutotagRunFromUi(): Promise<void> {
    const runId = String(autotagCurrentRun?.run_id || "");
    if (!runId) {
      setAutotagApproveError("No run selected.");
      setAutotagApproveNote("");
      return;
    }
    const approvedBy = String(autotagApprovedBy || "").trim();
    if (!approvedBy) {
      setAutotagApproveError("Please fill \"approved by\".");
      setAutotagApproveNote("");
      return;
    }

    setAutotagApprovePending(true);
    setAutotagApproveError("");
    setAutotagApproveNote("");
    try {
      const allowedCategoryDropIds = parseIdList(autotagAllowedDropIds);
      const value = await postJson<AutotagApproveResponse>(`${apiBase}/autotag/review-gate/approve`, {
        run_id: runId,
        approved_by: approvedBy,
        allowed_category_drop_ids: allowedCategoryDropIds
      });
      const approvedAt = String(value?.review_gate?.approved_at || "");
      setAutotagApproveNote(
        approvedAt ? `Run approved: ${fmtTs(approvedAt)}.` : "Run approved."
      );

      const generatedUrl = `${apiBase}/autotag/generated?run_id=${encodeURIComponent(runId)}`;
      const generatedValue = await fetchJson<AutotagGeneratedResponse>(generatedUrl);
      setAutotagGenerated(generatedValue);
      setAutotagAllowedDropIds(
        Array.isArray(generatedValue.review_gate?.allowed_category_drop_ids)
          ? generatedValue.review_gate.allowed_category_drop_ids.join(", ")
          : ""
      );
    } catch (e) {
      setAutotagApproveError(String(e));
    } finally {
      setAutotagApprovePending(false);
    }
  }

  const showTopic = (id: TopicId): boolean => {
    if (page === "timers" || page === "settings") {
      return false;
    }
    if (page === "dashboard") {
      return id === "overview" || id === "apps" || id === "categories";
    }
    return topic === "all" || topic === id;
  };

  const categoriesAppsSlices = (categories?.apps || []).map((r) => {
    const detail = categories?.app_details?.[r.category];
    const appItems = (detail?.top_apps || []).map((it) => ({
      label: trimLabel(appDisplayName(it.name), 84),
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
                  <td>{appDisplayName(a.app)}</td>
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

  const statusTone = page === "settings" ? "isOk" : error ? "isError" : loading ? "isLoading" : "isOk";
  const statusBadge = page === "settings" ? "settings" : loading ? "syncing" : error ? "degraded" : "healthy";
  const effectiveDayWindowMode = page === "dashboard" ? "midnight" : dayWindowMode;
  const showTodayNowMarker = page === "dashboard" && range === "24h" && effectiveDayWindowMode === "midnight";
  const selectedStatsDayStart = startOfLocalDay(parseLocalDateKey(statsDayKey) || new Date());
  const selectedStatsWeekStart = startOfLocalWeek(parseLocalDateKey(statsWeekStart) || new Date());
  const selectedStatsMonthStart = startOfLocalMonth(parseLocalMonthKey(statsMonthKey) || new Date());
  const statsDayInputValue = formatLocalDateKey(selectedStatsDayStart);
  const statsDayInputMax = currentDayKey();
  const statsDayLabel = selectedStatsDayStart.toLocaleDateString(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  });
  const statsWeekInputValue = formatLocalWeekKey(selectedStatsWeekStart);
  const statsWeekInputMax = formatLocalWeekKey(new Date());
  const statsWeekLabel = weekRangeLabel(selectedStatsWeekStart);
  const statsMonthLabel = monthRangeLabel(selectedStatsMonthStart);
  const rangeLabel =
    range === "24h"
      ? page === "stats" && effectiveDayWindowMode === "midnight"
        ? `24h (${statsDayLabel})`
        : effectiveDayWindowMode === "midnight"
          ? "24h (00:00 -> jetzt)"
          : "24h (-24h -> jetzt)"
      : page === "stats" && range === "1w"
        ? `1w (${statsWeekLabel})`
      : page === "stats" && range === "1m"
        ? `1m (${statsMonthLabel})`
      : range;

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
              <a href={hrefFor("timers")} className={page === "timers" ? "pill active" : "pill"}>
                timers
              </a>
              <a href={hrefFor("settings")} className={page === "settings" ? "pill active" : "pill"}>
                settings
              </a>
            </div>
          </div>
          <div className="sub">
            {page === "timers"
              ? "named timers + counters with start/pause/stop"
              : page === "settings"
                ? "appearance, notifications + export tools"
              : windowRange
                ? `range: ${rangeLabel} · ${fmtTs(windowRange.from)} → ${fmtTs(windowRange.to)}`
                : `range: ${rangeLabel}`}
          </div>
        </div>

        <div>
          <div className="controls">
            {page === "dashboard" || page === "stats"
              ? RANGES.map((r) => (
                  <button key={r.key} className={r.key === range ? "pill active" : "pill"} onClick={() => onRangeChange(r.key)}>
                    {page === "dashboard" && r.key === "24h" ? "heute" : r.label}
                  </button>
                ))
              : null}
            <button className="pill" onClick={() => setReloadKey((v) => v + 1)}>
              refresh
            </button>
          </div>
          {page === "stats" && range === "24h" ? (
            <div className="controls" style={{ marginTop: 7 }}>
              {DAY_WINDOW_MODES.map((mode) => (
                <button
                  key={mode.key}
                  type="button"
                  className={dayWindowMode === mode.key ? "pill active" : "pill"}
                  onClick={() => onDayWindowModeChange(mode.key)}
                >
                  {mode.label}
                </button>
              ))}
            </div>
          ) : null}
          {page === "stats" && range === "24h" && dayWindowMode === "midnight" ? (
            <div className="controls" style={{ marginTop: 7 }}>
              <input
                type="date"
                className="timersSelect statsCalendarInput"
                value={statsDayInputValue}
                max={statsDayInputMax}
                onChange={(e) => onStatsDayChange(e.target.value)}
                aria-label="stats day"
              />
            </div>
          ) : null}
          {page === "stats" && range === "1w" ? (
            <div className="controls" style={{ marginTop: 7 }}>
              <input
                type="week"
                className="timersSelect statsCalendarInput"
                value={statsWeekInputValue}
                max={statsWeekInputMax}
                onChange={(e) => onStatsWeekChange(e.target.value)}
                aria-label="stats week"
              />
            </div>
          ) : null}
          {page === "stats" && range === "1m" ? (
            <div className="controls" style={{ marginTop: 7 }}>
              <input
                type="month"
                className="timersSelect statsCalendarInput"
                value={statsMonthKey}
                max={currentMonthKey()}
                onChange={(e) => onStatsMonthChange(e.target.value)}
                aria-label="stats month"
              />
            </div>
          ) : null}
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
          <span>
            {page === "timers"
              ? "timer controls are local + persisted in sqlite"
              : page === "settings"
                ? "settings are stored in your browser"
              : updatedAt
                ? `updated ${updatedAt}`
                : loading
                  ? "fetching data..."
                  : "waiting for first refresh"}
          </span>
          <span className={error ? "statusIssue" : "statusHealthy"}>
            {page === "timers"
              ? "timer controls available"
              : page === "settings"
                ? "ready to configure"
              : error
                ? `partial errors: ${error}`
                : "all requested data sources reachable"}
          </span>
        </div>
      </section>

      {page === "timers" ? (
        <TimersPage apiBase={apiBase} timerNotifications={timerNotifications} timerSound={timerSound} />
      ) : null}
      {page === "settings" ? (
        <SettingsPage
          apiBase={apiBase}
          settings={uiSettings}
          onChange={onSettingsChange}
          onImportSettings={onSettingsImport}
          onResetSettings={onSettingsReset}
        />
      ) : null}

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
                  showNowMarker={showTodayNowMarker}
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

      {page === "stats" && showTopic("autotag") ? (
        <section className="card">
          <div className="cardHd">
            <h2>Autotag Decisions</h2>
          </div>
          <div className="cardBd workspaceStack">
            <div className="wsFilterRow">
              <span className="wsFilterLabel">run</span>
              <div className="autotagRunControl">
                <div className="timersSelectWrap">
                  <select
                    className="autotagSelect timersSelect"
                    value={autotagCurrentRun?.run_id || ""}
                    onChange={(e) => setAutotagRunId(e.target.value)}
                    disabled={!autotagRuns.length}
                  >
                    {!autotagRuns.length ? <option value="">no runs</option> : null}
                    {autotagRuns.map((row) => (
                      <option key={row.run_id} value={row.run_id}>
                        {row.run_id}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              {autotagCurrentRun ? (
                <span className={`autotagApplyBadge ${autotagCurrentRun.recommend_apply ? "ok" : "warn"}`}>
                  {autotagCurrentRun.recommend_apply ? "recommend apply" : "review needed"}
                </span>
              ) : null}
              {autotagReviewGate ? (
                <span className={`autotagApplyBadge ${autotagReviewGate.approved ? "ok" : "warn"}`}>
                  {autotagReviewGate.approved ? "review approved" : "review pending"}
                </span>
              ) : null}
              <span className="sub wsFilterMeta">
                rows: {autotagDecisions?.decision_count || 0}
                {autotagDecisions ? `/${autotagDecisions.total_decision_count}` : ""}
              </span>
            </div>

            {autotagCurrentRun ? (
              <div className="sub">
                {fmtTs(autotagCurrentRun.from_ts)} {"->"} {fmtTs(autotagCurrentRun.to_ts)} · pass-a failed batches: {autotagCurrentRun.pass_a_failed_batches}
                {" · "}
                pass-b failed batches: {autotagCurrentRun.pass_b_failed_batches}
                {autotagCurrentRun.pass_b_apply_blocked
                  ? ` · apply blocked: ${autotagCurrentRun.pass_b_apply_block_reason || "yes"}`
                  : " · apply blocked: no"}
              </div>
            ) : (
              <div className="empty">No autotag runs found.</div>
            )}

            {autotagCurrentRun ? (
              <div className="autotagApprovePanel">
                <div className="autotagApproveGrid">
                  <label className="autotagApproveField">
                    <span>approved by</span>
                    <input
                      type="text"
                      value={autotagApprovedBy}
                      placeholder="your name"
                      onChange={(e) => setAutotagApprovedBy(e.target.value)}
                      disabled={autotagApprovePending}
                    />
                  </label>
                  <label className="autotagApproveField autotagApproveFieldWide">
                    <span>allowed drop ids</span>
                    <input
                      type="text"
                      value={autotagAllowedDropIds}
                      placeholder="optional, comma-separated"
                      onChange={(e) => setAutotagAllowedDropIds(e.target.value)}
                      disabled={autotagApprovePending}
                    />
                  </label>
                </div>
                <div className="autotagApproveActions">
                  <button
                    type="button"
                    className="pill"
                    onClick={() => void approveAutotagRunFromUi()}
                    disabled={autotagApprovePending || !autotagCurrentRun}
                  >
                    {autotagApprovePending ? "saving..." : "approve in ui"}
                  </button>
                  <span className="sub">{autotagReviewSummary}</span>
                </div>
                {autotagApproveNote ? (
                  <div className="sub autotagApproveMessage ok">{autotagApproveNote}</div>
                ) : null}
                {autotagApproveError ? (
                  <div className="sub autotagApproveMessage err">{autotagApproveError}</div>
                ) : null}
              </div>
            ) : null}

            <div className="split2">
              <div>
                <h3>Decision States</h3>
                {autotagStateRows.length ? (
                  <HorizontalBars rows={autotagStateRows} valueFormatter={(v) => String(Math.round(v))} />
                ) : (
                  <div className="empty">No decision states in this run.</div>
                )}
              </div>
              <div>
                <h3>Decision Types</h3>
                {autotagTypeRows.length ? (
                  <HorizontalBars rows={autotagTypeRows} valueFormatter={(v) => String(Math.round(v))} />
                ) : (
                  <div className="empty">No decision types in this run.</div>
                )}
              </div>
            </div>

            <div className="split2">
              <div>
                <h3>Top Targets</h3>
                {autotagTopTargets.length ? (
                  <HorizontalBars
                    rows={autotagTopTargets.map((row) => ({ id: row.id, label: row.label, value: row.value }))}
                    valueFormatter={(v) => String(Math.round(v))}
                  />
                ) : (
                  <div className="empty">No target categories in this run.</div>
                )}
              </div>
              <div>
                <h3>Run Metrics</h3>
                <div className="kpiGrid autotagKpiGrid">
                  <div className="kpi">
                    <span>Avg confidence</span>
                    <strong>{Math.round((autotagDecisions?.summary?.avg_confidence || 0) * 100)}%</strong>
                  </div>
                  <div className="kpi">
                    <span>Visible rows</span>
                    <strong>{autotagDecisions?.decision_count || 0}</strong>
                  </div>
                </div>
              </div>
            </div>

            <div>
              <h3>Generated Categories (JSON)</h3>
              {autotagCurrentRun ? (
                <>
                  <div className="sub autotagGeneratedMeta">
                    categories: {autotagGeneratedCategoryCount} · sha256: {autotagCurrentRun.categories_generated_sha256 || "-"}
                    {autotagReviewGate ? ` · gate source: ${autotagReviewGate.source || "missing"}` : ""}
                  </div>
                  {autotagReviewGate?.allowed_category_drop_ids?.length ? (
                    <div className="sub autotagGeneratedMeta">
                      allowlisted drop ids: {autotagReviewGate.allowed_category_drop_ids.join(", ")}
                    </div>
                  ) : null}
                  {autotagGeneratedJson ? (
                    <div className="autotagJsonWrap">
                      <pre className="autotagJsonPre">{autotagGeneratedJson}</pre>
                    </div>
                  ) : (
                    <div className="empty">No categories.generated.json found for this run.</div>
                  )}
                </>
              ) : (
                <div className="empty">No run selected.</div>
              )}
            </div>

            <div>
              <h3>Decision Rows</h3>
              {autotagDecisions?.decisions?.length ? (
                <div className="tableScrollWrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Type</th>
                        <th>Entity</th>
                        <th>State</th>
                        <th>Target</th>
                        <th>Conf</th>
                        <th>Reasons</th>
                        <th>Flags</th>
                      </tr>
                    </thead>
                    <tbody>
                      {autotagDecisions.decisions.map((row, idx) => (
                        <tr key={`${row.entity_id}-${row.decision_type}-${row.created_at}-${idx}`}>
                          <td>{fmtTs(row.created_at)}</td>
                          <td>{row.decision_type || "-"}</td>
                          <td>
                            <div className="autotagEntityCell">
                              <div>{trimLabel(row.entity || row.entity_id, 80)}</div>
                              <div className="sub">{row.entity_id}</div>
                            </div>
                          </td>
                          <td>{row.state || "-"}</td>
                          <td>{row.target_category_id || "unknown"}</td>
                          <td>{Math.round((row.confidence || 0) * 100)}%</td>
                          <td>{(row.reasons || []).slice(0, 2).join(" · ") || "-"}</td>
                          <td>{(row.risk_flags || []).slice(0, 2).join(", ") || "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="empty">No decision rows found for this run.</div>
              )}
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
