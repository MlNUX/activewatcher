const api = globalThis.browser ?? globalThis.chrome;

const DEFAULTS = {
  serverUrl: "http://127.0.0.1:8712",
  browserLabel: "auto",
};

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

async function load() {
  let data = {};
  try {
    data = await callApi(api.storage.local.get, DEFAULTS);
  } catch {}
  document.getElementById("serverUrl").value = data.serverUrl || DEFAULTS.serverUrl;
  document.getElementById("browserLabel").value = data.browserLabel || DEFAULTS.browserLabel;
}

async function save() {
  const serverUrl = String(document.getElementById("serverUrl").value || DEFAULTS.serverUrl).trim();
  const browserLabel = String(document.getElementById("browserLabel").value || DEFAULTS.browserLabel).trim();
  try {
    await callApi(api.storage.local.set, { serverUrl, browserLabel });
    document.getElementById("status").textContent = "Saved.";
  } catch (e) {
    document.getElementById("status").textContent = `Save failed: ${e}`;
  }
}

document.getElementById("save").addEventListener("click", save);
load();
