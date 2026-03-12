import { useRef, useState, type ChangeEvent } from "react";

import { type UiSettingsSnapshot } from "./uiSettings";

type RangeResponse = {
  empty?: boolean;
  from_ts?: string | null;
  to_ts?: string | null;
};

type EventsResponse = {
  from_ts?: string;
  to_ts?: string;
  events?: unknown[];
  next_cursor?: number | null;
};

type TimersResponse = {
  server_ts?: string;
  timers?: unknown[];
};

function fileStamp(): string {
  return new Date().toISOString().replace(/[:.]/g, "-");
}

function downloadJson(fileName: string, payload: unknown): void {
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json;charset=utf-8"
  });
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(href);
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`${url} -> HTTP ${res.status}`);
  return (await res.json()) as T;
}

export function SettingsPage({
  apiBase,
  settings,
  onChange,
  onImportSettings,
  onResetSettings
}: {
  apiBase: string;
  settings: UiSettingsSnapshot;
  onChange: (patch: Partial<UiSettingsSnapshot>) => void;
  onImportSettings: (payload: unknown) => void;
  onResetSettings: () => void;
}) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  function clearStatus(): void {
    setNote("");
    setError("");
  }

  function onExportSettings(): void {
    clearStatus();
    downloadJson(`activewatcher-settings-${fileStamp()}.json`, {
      schema: "activewatcher-ui-settings/v1",
      exported_at: new Date().toISOString(),
      settings
    });
    setNote("settings exported");
  }

  async function onExportTimers(): Promise<void> {
    setBusy(true);
    clearStatus();
    try {
      const timers = await fetchJson<TimersResponse>(`${apiBase}/timers`);
      downloadJson(`activewatcher-timers-${fileStamp()}.json`, {
        schema: "activewatcher-timers-export/v1",
        exported_at: new Date().toISOString(),
        payload: timers
      });
      setNote("timers exported");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onExportData(): Promise<void> {
    setBusy(true);
    clearStatus();
    try {
      const buckets = ["window", "idle", "workspace", "workspace_switch", "system", "browser_tabs", "window_visible"];
      const dataByBucket: Record<string, unknown> = {};
      const bucketErrors: string[] = [];

      await Promise.all(
        buckets.map(async (bucket) => {
          try {
            const range = await fetchJson<RangeResponse>(
              `${apiBase}/range?bucket=${encodeURIComponent(bucket)}`
            );
            if (range.empty || !range.from_ts || !range.to_ts) {
              dataByBucket[bucket] = {
                bucket,
                empty: true,
                from_ts: null,
                to_ts: null,
                events: []
              };
              return;
            }

            const from = encodeURIComponent(range.from_ts);
            const to = encodeURIComponent(range.to_ts);
            const allEvents: unknown[] = [];
            let cursor = 0;
            let finalFromTs = range.from_ts;
            let finalToTs = range.to_ts;
            while (true) {
              const events = await fetchJson<EventsResponse>(
                `${apiBase}/events?bucket=${encodeURIComponent(bucket)}&from=${from}&to=${to}&limit=2000&cursor=${cursor}`
              );
              if (events.from_ts) finalFromTs = events.from_ts;
              if (events.to_ts) finalToTs = events.to_ts;
              if (Array.isArray(events.events) && events.events.length > 0) {
                allEvents.push(...events.events);
              }

              const nextCursor =
                typeof events.next_cursor === "number" && Number.isFinite(events.next_cursor) && events.next_cursor > cursor
                  ? Math.floor(events.next_cursor)
                  : null;
              if (nextCursor == null) break;
              cursor = nextCursor;
            }
            dataByBucket[bucket] = {
              bucket,
              empty: false,
              from_ts: finalFromTs,
              to_ts: finalToTs,
              event_count: allEvents.length,
              events: allEvents
            };
          } catch (e) {
            const message = String(e);
            bucketErrors.push(`${bucket}: ${message}`);
            dataByBucket[bucket] = {
              bucket,
              empty: true,
              from_ts: null,
              to_ts: null,
              events: [],
              error: message
            };
          }
        })
      );

      downloadJson(`activewatcher-data-${fileStamp()}.json`, {
        schema: "activewatcher-data-export/v1",
        exported_at: new Date().toISOString(),
        data: dataByBucket
      });
      if (bucketErrors.length > 0) {
        setNote("tracked data exported with partial errors");
        setError(bucketErrors.join(" | "));
      } else {
        setNote("tracked data exported");
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onImportFile(event: ChangeEvent<HTMLInputElement>): Promise<void> {
    const file = event.target.files?.[0];
    event.currentTarget.value = "";
    if (!file) return;

    setBusy(true);
    clearStatus();
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as unknown;
      onImportSettings(parsed);
      setNote("settings imported");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  function onReset(): void {
    clearStatus();
    onResetSettings();
    setNote("settings reset to defaults");
  }

  return (
    <section className="card">
      <div className="cardHd">
        <h2>Settings</h2>
      </div>
      <div className="cardBd settingsStack">
        <div className="settingsPanel">
          <div className="settingsSection">
            <div className="settingsSectionHd">
              <h3 className="settingsSectionTitle">Appearance</h3>
              <div className="sub settingsSectionDesc">visual style and readability</div>
            </div>
            <div className="settingsGrid">
              <div className="settingsField">
                <span>white mode</span>
                <div className="settingsToggleRow">
                  <button
                    type="button"
                    className={settings.themeMode === "light" ? "pill active" : "pill"}
                    onClick={() => onChange({ themeMode: "light" })}
                  >
                    on
                  </button>
                  <button
                    type="button"
                    className={settings.themeMode === "dark" ? "pill active" : "pill"}
                    onClick={() => onChange({ themeMode: "dark" })}
                  >
                    off
                  </button>
                </div>
              </div>

              <div className="settingsField">
                <span>high contrast</span>
                <div className="settingsToggleRow">
                  <button
                    type="button"
                    className={settings.contrastMode === "high" ? "pill active" : "pill"}
                    onClick={() => onChange({ contrastMode: "high" })}
                  >
                    on
                  </button>
                  <button
                    type="button"
                    className={settings.contrastMode === "normal" ? "pill active" : "pill"}
                    onClick={() => onChange({ contrastMode: "normal" })}
                  >
                    off
                  </button>
                </div>
              </div>

              <div className="settingsField">
                <span>design</span>
                <div className="settingsToggleRow">
                  <button
                    type="button"
                    className={settings.designVariant === "default" ? "pill active" : "pill"}
                    onClick={() => onChange({ designVariant: "default" })}
                  >
                    aurora
                  </button>
                  <button
                    type="button"
                    className={settings.designVariant === "terminal" ? "pill active" : "pill"}
                    onClick={() => onChange({ designVariant: "terminal" })}
                  >
                    terminal
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="settingsSection">
            <div className="settingsSectionHd">
              <h3 className="settingsSectionTitle">Notifications</h3>
              <div className="sub settingsSectionDesc">timer finish alerts</div>
            </div>
            <div className="settingsGrid">
              <div className="settingsField">
                <span>desktop notification</span>
                <div className="settingsToggleRow">
                  <button
                    type="button"
                    className={settings.timerNotifications ? "pill active" : "pill"}
                    onClick={() => onChange({ timerNotifications: true })}
                  >
                    on
                  </button>
                  <button
                    type="button"
                    className={!settings.timerNotifications ? "pill active" : "pill"}
                    onClick={() => onChange({ timerNotifications: false })}
                  >
                    off
                  </button>
                </div>
              </div>

              <div className="settingsField">
                <span>sound alert</span>
                <div className="settingsToggleRow">
                  <button
                    type="button"
                    className={settings.timerSound ? "pill active" : "pill"}
                    onClick={() => onChange({ timerSound: true })}
                  >
                    on
                  </button>
                  <button
                    type="button"
                    className={!settings.timerSound ? "pill active" : "pill"}
                    onClick={() => onChange({ timerSound: false })}
                  >
                    off
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="settingsSection">
            <div className="settingsSectionHd">
              <h3 className="settingsSectionTitle">API Security</h3>
              <div className="sub settingsSectionDesc">token for write actions</div>
            </div>
            <div className="settingsGrid">
              <label className="settingsField" htmlFor="aw-api-write-token">
                <span>write token (optional)</span>
                <input
                  id="aw-api-write-token"
                  type="password"
                  className="settingsInput"
                  autoComplete="off"
                  value={settings.apiWriteToken}
                  onChange={(e) => onChange({ apiWriteToken: e.currentTarget.value })}
                  placeholder="X-ActiveWatcher-Token"
                />
              </label>
            </div>
          </div>

          <div className="settingsSection">
            <div className="settingsSectionHd">
              <h3 className="settingsSectionTitle">Data & Timers</h3>
              <div className="sub settingsSectionDesc">export and import tools</div>
            </div>

            <div className="settingsActionGrid">
              <button type="button" className="pill" onClick={() => void onExportData()} disabled={busy}>
                export tracked data
              </button>
              <button type="button" className="pill" onClick={() => void onExportTimers()} disabled={busy}>
                export timers
              </button>
              <button type="button" className="pill" onClick={onExportSettings} disabled={busy}>
                export settings
              </button>
              <button type="button" className="pill" onClick={() => fileInputRef.current?.click()} disabled={busy}>
                import settings
              </button>
              <button type="button" className="pill danger" onClick={onReset} disabled={busy}>
                reset settings
              </button>
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept="application/json"
              className="settingsHiddenInput"
              onChange={(e) => void onImportFile(e)}
            />
          </div>

          {note ? <div className="sub settingsStatus ok">{note}</div> : null}
          {error ? <div className="sub settingsStatus err">{error}</div> : null}

          <div className="sub settingsHint">
            settings are saved locally in your browser and apply instantly.
          </div>
        </div>
      </div>
    </section>
  );
}
