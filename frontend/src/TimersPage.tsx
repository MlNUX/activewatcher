import { useEffect, useMemo, useRef, useState } from "react";

type TimerKind = "timer" | "counter";
type TimerState = "idle" | "running" | "paused" | "finished";
type TimerListView = "active" | "history";

type TimerRow = {
  id: number;
  name: string;
  kind: TimerKind;
  state: TimerState;
  duration_seconds: number;
  elapsed_seconds: number;
  remaining_seconds: number | null;
  created_at: string;
  updated_at: string;
};

type TimersResponse = {
  server_ts: string;
  timers: TimerRow[];
};

type TimerAction = "start" | "pause" | "stop" | "reactivate" | "delete";

type TimerActionResponse = {
  status: string;
  timer: TimerRow;
};

function asNumber(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

const DIAL_RADIUS = 44;
const DIAL_CIRCUMFERENCE = 2 * Math.PI * DIAL_RADIUS;

function clamp01(raw: number): number {
  return Math.max(0, Math.min(1, asNumber(raw)));
}

function timerDialProgress(row: TimerRow, elapsedSeconds: number): number {
  if (row.kind !== "timer" || row.duration_seconds <= 0) return 0;
  return clamp01(elapsedSeconds / row.duration_seconds);
}

function fmtClock(rawSeconds: number): string {
  const total = Math.max(0, Math.floor(asNumber(rawSeconds)));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function isHistoryEntry(row: TimerRow): boolean {
  if (row.state === "finished") return true;
  if (row.state !== "idle") return false;
  return asNumber(row.elapsed_seconds) > 0;
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`${url} -> HTTP ${res.status}`);
  return (await res.json()) as T;
}

async function postJson<T>(url: string, payload: unknown, writeToken?: string): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json"
  };
  const token = String(writeToken || "").trim();
  if (token) {
    headers["X-ActiveWatcher-Token"] = token;
  }
  const res = await fetch(url, {
    method: "POST",
    cache: "no-store",
    headers,
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    let detail = "";
    try {
      const body = (await res.json()) as { detail?: unknown };
      detail = String(body?.detail || "").trim();
    } catch {
      detail = "";
    }
    if (detail) throw new Error(`${url} -> HTTP ${res.status}: ${detail}`);
    throw new Error(`${url} -> HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

async function notifyTimerFinished(name: string): Promise<void> {
  if (typeof window === "undefined" || !("Notification" in window)) return;
  let permission = Notification.permission;
  if (permission === "default") {
    try {
      permission = await Notification.requestPermission();
    } catch {
      return;
    }
  }
  if (permission !== "granted") return;
  new Notification("Timer finished", {
    body: `${name} is done.`,
    tag: `timer-finished-${name}`
  });
}

function playTimerFinishedSound(): void {
  if (typeof window === "undefined") return;
  const Ctx = window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctx) return;

  try {
    const ctx = new Ctx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = "sine";
    osc.frequency.setValueAtTime(880, ctx.currentTime);
    osc.frequency.setValueAtTime(660, ctx.currentTime + 0.18);

    gain.gain.setValueAtTime(0.0001, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.14, ctx.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.33);

    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.34);

    window.setTimeout(() => {
      void ctx.close();
    }, 420);
  } catch {
    // ignore audio failures (autoplay/browser policy)
  }
}

export function TimersPage({
  apiBase,
  timerNotifications,
  timerSound,
  apiWriteToken
}: {
  apiBase: string;
  timerNotifications: boolean;
  timerSound: boolean;
  apiWriteToken: string;
}) {
  const [timers, setTimers] = useState<TimerRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  const [name, setName] = useState("");
  const [kind, setKind] = useState<TimerKind>("timer");
  const [minutes, setMinutes] = useState("25");

  const [refreshKey, setRefreshKey] = useState(0);
  const [createPending, setCreatePending] = useState(false);
  const [activeTimerId, setActiveTimerId] = useState<number | null>(null);
  const [listView, setListView] = useState<TimerListView>("active");
  const prevStatesRef = useRef<Map<number, TimerState>>(new Map());

  const runningCount = useMemo(
    () => timers.reduce((count, row) => (row.state === "running" ? count + 1 : count), 0),
    [timers]
  );

  const pausedCount = useMemo(
    () => timers.reduce((count, row) => (row.state === "paused" ? count + 1 : count), 0),
    [timers]
  );

  const [activeTimers, historyTimers] = useMemo(() => {
    const active: TimerRow[] = [];
    const history: TimerRow[] = [];
    for (const row of timers) {
      if (isHistoryEntry(row)) {
        history.push(row);
      } else {
        active.push(row);
      }
    }
    return [active, history] as const;
  }, [timers]);
  const visibleTimers = listView === "history" ? historyTimers : activeTimers;

  useEffect(() => {
    let cancelled = false;
    let inFlight = false;
    let loopHandle: number | null = null;

    async function load(quiet: boolean): Promise<void> {
      if (inFlight) return;
      inFlight = true;
      if (!quiet && !cancelled) setLoading(true);

      let nextDelay = 4_000;
      try {
        const value = await fetchJson<TimersResponse>(`${apiBase}/timers`);
        if (cancelled) return;
        const rows = Array.isArray(value?.timers) ? value.timers : [];
        setTimers(rows);
        setError("");
        nextDelay = rows.some((row) => row.state === "running") ? 1_000 : 4_000;
      } catch (e) {
        if (cancelled) return;
        setError(String(e));
      } finally {
        inFlight = false;
        if (!quiet && !cancelled) setLoading(false);
      }

      if (!cancelled) {
        loopHandle = window.setTimeout(() => {
          void load(true);
        }, nextDelay);
      }
    }

    void load(false);
    return () => {
      cancelled = true;
      if (loopHandle != null) window.clearTimeout(loopHandle);
    };
  }, [apiBase, refreshKey]);

  useEffect(() => {
    const prev = prevStatesRef.current;
    const next = new Map<number, TimerState>();

    for (const row of timers) {
      next.set(row.id, row.state);
      const previousState = prev.get(row.id);
      if (row.kind !== "timer") continue;
      if (!previousState || previousState === "finished") continue;
      if (row.state !== "finished") continue;

      if (timerNotifications) {
        void notifyTimerFinished(row.name);
      }
      if (timerSound) {
        playTimerFinishedSound();
      }
    }

    prevStatesRef.current = next;
  }, [timers, timerNotifications, timerSound]);

  async function createTimer(): Promise<void> {
    const trimmedName = String(name || "").trim();
    if (!trimmedName) {
      setError("name is required");
      return;
    }

    let durationSeconds = 0;
    if (kind === "timer") {
      const parsedMinutes = Number(minutes);
      if (!Number.isFinite(parsedMinutes) || parsedMinutes <= 0) {
        setError("timer minutes must be > 0");
        return;
      }
      durationSeconds = Math.max(1, Math.round(parsedMinutes * 60));
    }

    setCreatePending(true);
    setError("");
    setNote("");
    try {
      const payload: Record<string, unknown> = {
        name: trimmedName,
        kind
      };
      if (kind === "timer") payload.duration_seconds = durationSeconds;
      await postJson<TimerActionResponse>(`${apiBase}/timers`, payload, apiWriteToken);
      setName("");
      if (kind === "counter") setKind("timer");
      setNote(`created ${kind}: ${trimmedName}`);
      setRefreshKey((v) => v + 1);
    } catch (e) {
      setError(String(e));
    } finally {
      setCreatePending(false);
    }
  }

  async function runAction(
    timerId: number,
    action: TimerAction,
    options?: { successNote?: string }
  ): Promise<void> {
    setActiveTimerId(timerId);
    setError("");
    setNote("");
    try {
      await postJson<TimerActionResponse>(
        `${apiBase}/timers/${timerId}/${action}`,
        {},
        apiWriteToken
      );
      if (action === "reactivate") {
        setListView("active");
      }
      if (options?.successNote) {
        setNote(options.successNote);
      }
      setRefreshKey((v) => v + 1);
    } catch (e) {
      setError(String(e));
    } finally {
      setActiveTimerId(null);
    }
  }

  return (
    <section className="card">
      <div className="cardHd">
        <h2>Timers</h2>
      </div>
      <div className="cardBd timersStack">
        <div className="timersCreatePanel">
          <div className="timersCreateGrid">
            <label className="timersField timersFieldWide">
              <span>name</span>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={kind === "timer" ? "focus sprint" : "coffee count"}
                maxLength={120}
              />
            </label>
            <label className="timersField">
              <span>type</span>
              <div className="timersSelectWrap">
                <select
                  className="timersSelect"
                  value={kind}
                  onChange={(e) => setKind(e.target.value === "counter" ? "counter" : "timer")}
                >
                  <option value="timer">timer</option>
                  <option value="counter">counter</option>
                </select>
              </div>
            </label>
            <label className="timersField">
              <span>{kind === "timer" ? "minutes" : "history"}</span>
              {kind === "timer" ? (
                <input
                  type="number"
                  min={1}
                  max={10_080}
                  step={1}
                  value={minutes}
                  onChange={(e) => setMinutes(e.target.value)}
                />
              ) : (
                <div className="timersHint">stop archives value; reactivate keeps it</div>
              )}
            </label>
            <div className="timersCreateActions">
              <button className="pill active" type="button" onClick={() => void createTimer()} disabled={createPending}>
                {createPending ? "creating..." : "add"}
              </button>
            </div>
          </div>
          <div className="sub timersMetaLine">
            {loading
              ? "loading timers..."
              : `${activeTimers.length} active · ${historyTimers.length} history · ${runningCount} running · ${pausedCount} paused`}
          </div>
          <div className="timersViewMenu" role="tablist" aria-label="timer lists">
            <button
              type="button"
              role="tab"
              aria-selected={listView === "active"}
              className={listView === "active" ? "pill active" : "pill"}
              onClick={() => setListView("active")}
            >
              active ({activeTimers.length})
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={listView === "history"}
              className={listView === "history" ? "pill active" : "pill"}
              onClick={() => setListView("history")}
            >
              history ({historyTimers.length})
            </button>
          </div>
          {note ? <div className="sub timersMessage ok">{note}</div> : null}
          {error ? <div className="sub timersMessage err">{error}</div> : null}
        </div>

        {visibleTimers.length === 0 ? (
          <div className="timersEmpty">
            {listView === "history"
              ? "Noch keine beendeten/gestoppten Timer im Verlauf."
              : "Noch keine aktiven Timer/Zaehler. Lege oben deinen ersten Eintrag an."}
          </div>
        ) : (
          <div className="timersList">
            {visibleTimers.map((row) => {
              const elapsed = asNumber(row.elapsed_seconds);
              const remaining = asNumber(row.remaining_seconds);
              const inHistory = listView === "history";
              const progress = timerDialProgress(row, elapsed);
              const ringOffset = DIAL_CIRCUMFERENCE * (1 - progress);
              const busy = activeTimerId === row.id;
              const isTimer = row.kind === "timer";
              const isCounter = row.kind === "counter";
              const neverStarted = row.state === "idle" && elapsed <= 0;
              const stateLabel = row.state === "idle" && listView === "history" ? "stopped" : row.state;
              const displayValue = isTimer && !inHistory ? fmtClock(remaining) : fmtClock(elapsed);
              const topLabel = isTimer ? "work progress" : "counter runtime";
              const primaryAction: TimerAction = row.state === "running" ? "pause" : "start";
              const primaryLabel =
                isTimer ? (row.state === "running" ? "start break" : "start work") : row.state === "running" ? "pause" : "start";
              const stopLabel = isTimer ? "work done" : "stop";
              const secondaryAction: TimerAction = neverStarted ? "delete" : "stop";
              const secondaryLabel = neverStarted ? "delete" : stopLabel;
              const secondaryClassName = neverStarted ? "pill timersCtlDanger" : "pill timersCtlGhost";
              const itemLabel = isTimer ? "timer" : "counter";
              const dialAriaLabel = isCounter
                ? `${row.name}: counter ${stateLabel}, ${displayValue}`
                : `${row.name}: ${Math.round(progress * 100)} percent complete`;

              return (
                <article className={`timersItem tone-${row.state}`} key={row.id}>
                  <div className="timersDialTop">
                    <span className="timersDialTopLabel">{topLabel}</span>
                    <span className="timersDialTopIcon" aria-hidden="true">
                      ...
                    </span>
                  </div>

                  {isTimer ? (
                    <div className="timersDialShell">
                      <svg
                        className="timersDialSvg"
                        viewBox="0 0 120 120"
                        role="img"
                        aria-label={dialAriaLabel}
                      >
                        <circle className="timersDialTrack" cx="60" cy="60" r={DIAL_RADIUS} />
                        <circle
                          className="timersDialFill"
                          cx="60"
                          cy="60"
                          r={DIAL_RADIUS}
                          style={{
                            strokeDasharray: `${DIAL_CIRCUMFERENCE}`,
                            strokeDashoffset: `${ringOffset}`
                          }}
                        />
                      </svg>
                      <div className="timersDialValue">{displayValue}</div>
                    </div>
                  ) : (
                    <div className="timersCounterShell" role="img" aria-label={dialAriaLabel}>
                      <div className="timersCounterValue">{displayValue}</div>
                      <div className="timersCounterSub">counting up</div>
                      <span className={`timersLiveDot ${row.state === "running" ? "isLive" : ""}`} aria-hidden="true" />
                    </div>
                  )}

                  <div className="timersItemName">{row.name}</div>
                  <div className="timersItemBadges">
                    <span className={`timersBadge kind-${row.kind}`}>{row.kind}</span>
                    <span className={`timersBadge state-${row.state}`}>{stateLabel}</span>
                  </div>

                  <div className="sub timersItemMeta">
                    {inHistory
                      ? row.kind === "timer"
                        ? `${fmtClock(elapsed)} counted down / ${fmtClock(row.duration_seconds)} total`
                        : `${fmtClock(elapsed)} counted up`
                      : row.kind === "timer"
                        ? `${fmtClock(elapsed)} elapsed / ${fmtClock(row.duration_seconds)} total`
                        : `${fmtClock(elapsed)} elapsed`}
                  </div>

                  {inHistory ? (
                    <div className="timersControls">
                      <button
                        type="button"
                        className="pill active timersCtlPrimary"
                        onClick={() => void runAction(row.id, "reactivate")}
                        disabled={busy || createPending}
                      >
                        reactivate
                      </button>
                      <button
                        type="button"
                        className="pill timersCtlDanger"
                        onClick={() => {
                          if (!window.confirm(`Delete ${itemLabel} \"${row.name}\" from history?`)) return;
                          void runAction(row.id, "delete", {
                            successNote: `deleted ${itemLabel}: ${row.name}`
                          });
                        }}
                        disabled={busy || createPending}
                      >
                        delete
                      </button>
                    </div>
                  ) : (
                    <div className="timersControls">
                      <button
                        type="button"
                        className="pill active timersCtlPrimary"
                        onClick={() => void runAction(row.id, primaryAction)}
                        disabled={busy || createPending}
                      >
                        {primaryLabel}
                      </button>
                      <button
                        type="button"
                        className={secondaryClassName}
                        onClick={() => {
                          if (secondaryAction === "delete") {
                            if (!window.confirm(`Delete ${itemLabel} \"${row.name}\"?`)) return;
                            void runAction(row.id, "delete", {
                              successNote: `deleted ${itemLabel}: ${row.name}`
                            });
                            return;
                          }
                          void runAction(row.id, "stop");
                        }}
                        disabled={busy || createPending}
                      >
                        {secondaryLabel}
                      </button>
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
