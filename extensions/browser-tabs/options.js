const api = globalThis.browser ?? globalThis.chrome;
const USE_PROMISE_API = Boolean(globalThis.browser);

const DEFAULTS = {
  serverUrl: "http://127.0.0.1:8712",
  browserLabel: "auto",
};

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

async function load() {
  let data = {};
  try {
    data = await callApi(api.storage.local, "get", DEFAULTS);
  } catch {}
  const normalized = normalizeServerUrl(data.serverUrl);
  document.getElementById("serverUrl").value = normalized || DEFAULTS.serverUrl;
  document.getElementById("browserLabel").value = data.browserLabel || DEFAULTS.browserLabel;
}

async function save() {
  const status = document.getElementById("status");
  const rawServerUrl = String(document.getElementById("serverUrl").value || DEFAULTS.serverUrl).trim();
  const serverUrl = normalizeServerUrl(rawServerUrl);
  if (!serverUrl) {
    status.textContent = "Use http(s)://127.0.0.1:8712 or http(s)://localhost:8712.";
    return;
  }
  const browserLabel = String(document.getElementById("browserLabel").value || DEFAULTS.browserLabel).trim();
  try {
    await callApi(api.storage.local, "set", { serverUrl, browserLabel });
    status.textContent = "Saved.";
  } catch (e) {
    status.textContent = `Save failed: ${e}`;
  }
}

document.getElementById("save").addEventListener("click", save);
load();
