const api = globalThis.browser ?? globalThis.chrome;

const DEFAULTS = {
  serverUrl: "http://127.0.0.1:8712",
  browserLabel: "auto",
};

let sendTimer = null;
let lastPayload = "";

function callApi(fn, ...args) {
  return new Promise((resolve, reject) => {
    try {
      fn(...args, (...res) => {
        const err = api?.runtime?.lastError;
        if (err) return reject(err);
        resolve(res.length > 1 ? res : res[0]);
      });
    } catch (e) {
      reject(e);
    }
  });
}

async function getSettings() {
  try {
    const data = await callApi(api.storage.local.get, DEFAULTS);
    return { ...DEFAULTS, ...data };
  } catch {
    return { ...DEFAULTS };
  }
}

function detectBrowserLabel() {
  const ua = String(navigator.userAgent || "").toLowerCase();
  if (ua.includes("firefox")) return "firefox";
  if (ua.includes("brave")) return "brave";
  if (ua.includes("chrome")) return "chrome";
  return "browser";
}

async function collectTabsSnapshot() {
  const tabs = await callApi(api.tabs.query, {});
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
  const serverUrl = String(settings.serverUrl || DEFAULTS.serverUrl).replace(/\/+$/, "");
  const browserLabel =
    settings.browserLabel && settings.browserLabel !== "auto"
      ? String(settings.browserLabel)
      : detectBrowserLabel();

  let snapshot;
  try {
    snapshot = await collectTabsSnapshot();
  } catch {
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
  if (body === lastPayload) return;
  lastPayload = body;

  try {
    await fetch(`${serverUrl}/v1/state`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
  } catch {
    // ignore network errors
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
