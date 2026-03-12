const api = globalThis.browser ?? globalThis.chrome;
const USE_PROMISE_API = Boolean(globalThis.browser);

const DEFAULTS = {
  serverUrl: "http://127.0.0.1:8712",
  browserLabel: "auto",
  writeToken: "",
};

let sendTimer = null;
let lastPayloadKey = "";

const ALLOWED_SERVER_HOSTS = new Set(["127.0.0.1", "localhost", "[::1]", "::1"]);
const ALLOWED_SERVER_PORT = "8712";

function normalizeServerUrl(rawValue) {
  const raw = String(rawValue || "").trim();
  if (!raw) return null;
  let parsed;
  try {
    parsed = new URL(raw);
  } catch {
    return null;
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return null;
  const host = String(parsed.hostname || "").trim().toLowerCase();
  if (!ALLOWED_SERVER_HOSTS.has(host)) return null;
  const port = parsed.port || (parsed.protocol === "https:" ? "443" : "80");
  if (port !== ALLOWED_SERVER_PORT) return null;
  return parsed.origin;
}

function callApi(target, method, ...args) {
  const fn = target?.[method];
  if (typeof fn !== "function") {
    return Promise.reject(new Error(`Missing browser API method: ${method}`));
  }

  if (USE_PROMISE_API) {
    try {
      return Promise.resolve(fn.call(target, ...args));
    } catch (e) {
      return Promise.reject(e);
    }
  }

  return new Promise((resolve, reject) => {
    try {
      fn.call(target, ...args, (...res) => {
        const err = api?.runtime?.lastError;
        if (err) {
          reject(new Error(String(err.message || err)));
          return;
        }
        resolve(res.length > 1 ? res : res[0]);
      });
    } catch (e) {
      reject(e);
    }
  });
}

async function getSettings() {
  try {
    const data = await callApi(api.storage.local, "get", DEFAULTS);
    return { ...DEFAULTS, ...data };
  } catch {
    return { ...DEFAULTS };
  }
}

function detectBrowserLabel() {
  const brands = navigator.userAgentData?.brands;
  if (Array.isArray(brands)) {
    const normalized = brands.map((row) => String(row?.brand || "").toLowerCase());
    if (normalized.some((b) => b.includes("firefox"))) return "firefox";
    if (normalized.some((b) => b.includes("brave"))) return "brave";
    if (normalized.some((b) => b.includes("chrome") || b.includes("chromium"))) return "chrome";
  }

  const ua = String(navigator.userAgent || "").toLowerCase();
  if (ua.includes("firefox")) return "firefox";
  if (ua.includes("brave")) return "brave";
  if (ua.includes("chrome")) return "chrome";
  return "browser";
}

function dedupeKey(payload, nowMs) {
  const minuteBucket = Math.floor((Number(nowMs) || Date.now()) / 60000);
  return JSON.stringify({
    bucket: payload?.bucket || "",
    source: payload?.source || "",
    data: payload?.data || {},
    minute: minuteBucket
  });
}

async function collectTabsSnapshot() {
  const tabs = await callApi(api.tabs, "query", {});
  const windowIds = new Set();
  let incognito = 0;
  let pinned = 0;
  let audible = 0;
  let muted = 0;
  const tabItems = [];
  for (const t of tabs || []) {
    if (t.windowId != null) windowIds.add(t.windowId);
    if (t.incognito) incognito += 1;
    if (t.pinned) pinned += 1;
    if (t.audible) audible += 1;
    if (t.mutedInfo && t.mutedInfo.muted) muted += 1;
    tabItems.push({
      id: t.id ?? null,
      window_id: t.windowId ?? null,
      index: t.index ?? null,
      url: t.url || t.pendingUrl || "",
      pending_url: t.pendingUrl || "",
      title: t.title || "",
      fav_icon_url: t.favIconUrl || "",
      status: t.status || "",
      last_accessed: t.lastAccessed ?? null,
      discarded: !!t.discarded,
      auto_discardable: !!t.autoDiscardable,
      group_id: t.groupId ?? null,
      opener_tab_id: t.openerTabId ?? null,
      active: !!t.active,
      pinned: !!t.pinned,
      highlighted: !!t.highlighted,
      incognito: !!t.incognito,
      audible: !!t.audible,
      muted: !!(t.mutedInfo && t.mutedInfo.muted),
    });
  }
  return {
    count: (tabs || []).length,
    window_count: windowIds.size,
    incognito_tabs: incognito,
    pinned_tabs: pinned,
    audible_tabs: audible,
    muted_tabs: muted,
    tabs: tabItems,
  };
}

async function postState() {
  const settings = await getSettings();
  const serverUrl = normalizeServerUrl(settings.serverUrl) || DEFAULTS.serverUrl;
  const browserLabel =
    settings.browserLabel && settings.browserLabel !== "auto"
      ? String(settings.browserLabel)
      : detectBrowserLabel();

  let snapshot;
  try {
    snapshot = await collectTabsSnapshot();
  } catch (e) {
    console.warn("[ActiveWatcher Tabs] Failed to collect tab snapshot", e);
    return;
  }

  const payload = {
    bucket: "browser_tabs",
    source: `tabs:${browserLabel}`,
    ts: new Date().toISOString(),
    data: {
      browser: browserLabel,
      ...snapshot,
    },
  };

  const body = JSON.stringify(payload);
  const key = dedupeKey(payload, Date.now());
  if (key === lastPayloadKey) return;

  try {
    const headers = { "Content-Type": "application/json" };
    const writeToken = String(settings.writeToken || "").trim();
    if (writeToken) {
      headers["X-ActiveWatcher-Token"] = writeToken;
    }
    const response = await fetch(`${serverUrl}/v1/state`, {
      method: "POST",
      headers,
      body,
    });
    if (response.ok) {
      lastPayloadKey = key;
    } else {
      console.warn("[ActiveWatcher Tabs] Server rejected state payload", response.status);
    }
  } catch (e) {
    console.warn("[ActiveWatcher Tabs] Failed to send state payload", e);
  }
}

function scheduleSend(delayMs = 400) {
  if (sendTimer) clearTimeout(sendTimer);
  sendTimer = setTimeout(() => {
    sendTimer = null;
    postState();
  }, delayMs);
}

function bindEvents() {
  const on = (obj, evt) => obj && obj[evt] && obj[evt].addListener(() => scheduleSend());
  on(api.tabs, "onCreated");
  on(api.tabs, "onRemoved");
  on(api.tabs, "onUpdated");
  on(api.tabs, "onActivated");
  on(api.tabs, "onMoved");
  on(api.tabs, "onAttached");
  on(api.tabs, "onDetached");
  on(api.windows, "onCreated");
  on(api.windows, "onRemoved");
  on(api.windows, "onFocusChanged");
  if (api.runtime && api.runtime.onStartup) {
    api.runtime.onStartup.addListener(() => scheduleSend(0));
  }
  if (api.runtime && api.runtime.onInstalled) {
    api.runtime.onInstalled.addListener(() => scheduleSend(0));
  }
  if (api.alarms) {
    try {
      api.alarms.create("aw_tabs_ping", { periodInMinutes: 1 });
      api.alarms.onAlarm.addListener((a) => {
        if (a && a.name === "aw_tabs_ping") scheduleSend(0);
      });
    } catch {
      // ignore
    }
  }
}

bindEvents();
scheduleSend(0);
