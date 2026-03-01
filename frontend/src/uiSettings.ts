export type ThemeMode = "dark" | "light";
export type ContrastMode = "normal" | "high";

export type UiSettingsSnapshot = {
  themeMode: ThemeMode;
  contrastMode: ContrastMode;
  timerNotifications: boolean;
  timerSound: boolean;
};

const KEY_THEME_MODE = "aw.ui.theme";
const KEY_CONTRAST_MODE = "aw.ui.contrast";
const KEY_TIMER_NOTIFICATIONS = "aw.timer.notifications";
const KEY_TIMER_SOUND = "aw.timer.sound";

const TRUE_VALUES = new Set(["1", "true", "yes", "on"]);
const FALSE_VALUES = new Set(["0", "false", "no", "off"]);

export const DEFAULT_UI_SETTINGS: UiSettingsSnapshot = {
  themeMode: "dark",
  contrastMode: "normal",
  timerNotifications: false,
  timerSound: false
};

function localStorageSafe(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function readString(key: string): string {
  const storage = localStorageSafe();
  if (!storage) return "";
  try {
    return String(storage.getItem(key) || "").trim();
  } catch {
    return "";
  }
}

function writeString(key: string, value: string): void {
  const storage = localStorageSafe();
  if (!storage) return;
  try {
    storage.setItem(key, String(value));
  } catch {
    // ignore storage write errors
  }
}

function readBoolean(key: string, fallback: boolean): boolean {
  const raw = readString(key).toLowerCase();
  if (TRUE_VALUES.has(raw)) return true;
  if (FALSE_VALUES.has(raw)) return false;
  return fallback;
}

function writeBoolean(key: string, value: boolean): void {
  writeString(key, value ? "1" : "0");
}

function normalizeThemeMode(value: unknown, fallback: ThemeMode): ThemeMode {
  const raw = String(value || "")
    .trim()
    .toLowerCase();
  if (raw === "light" || raw === "white") return "light";
  if (raw === "dark") return "dark";
  return fallback;
}

function normalizeContrastMode(value: unknown, fallback: ContrastMode): ContrastMode {
  const raw = String(value || "")
    .trim()
    .toLowerCase();
  if (raw === "high" || raw === "high-contrast") return "high";
  if (raw === "normal") return "normal";
  return fallback;
}

function normalizeBoolean(value: unknown, fallback: boolean): boolean {
  if (typeof value === "boolean") return value;
  const raw = String(value || "")
    .trim()
    .toLowerCase();
  if (TRUE_VALUES.has(raw)) return true;
  if (FALSE_VALUES.has(raw)) return false;
  return fallback;
}

function asRecord(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("settings import must be a JSON object");
  }
  return value as Record<string, unknown>;
}

export function getThemeMode(): ThemeMode {
  return normalizeThemeMode(readString(KEY_THEME_MODE), DEFAULT_UI_SETTINGS.themeMode);
}

export function setThemeMode(mode: ThemeMode): void {
  writeString(KEY_THEME_MODE, mode);
}

export function getContrastMode(): ContrastMode {
  return normalizeContrastMode(readString(KEY_CONTRAST_MODE), DEFAULT_UI_SETTINGS.contrastMode);
}

export function setContrastMode(mode: ContrastMode): void {
  writeString(KEY_CONTRAST_MODE, mode);
}

export function getTimerNotificationsEnabled(): boolean {
  return readBoolean(KEY_TIMER_NOTIFICATIONS, DEFAULT_UI_SETTINGS.timerNotifications);
}

export function setTimerNotificationsEnabled(enabled: boolean): void {
  writeBoolean(KEY_TIMER_NOTIFICATIONS, enabled);
}

export function getTimerSoundEnabled(): boolean {
  return readBoolean(KEY_TIMER_SOUND, DEFAULT_UI_SETTINGS.timerSound);
}

export function setTimerSoundEnabled(enabled: boolean): void {
  writeBoolean(KEY_TIMER_SOUND, enabled);
}

export function getUiSettingsSnapshot(): UiSettingsSnapshot {
  return {
    themeMode: getThemeMode(),
    contrastMode: getContrastMode(),
    timerNotifications: getTimerNotificationsEnabled(),
    timerSound: getTimerSoundEnabled()
  };
}

export function applyUiSettingsSnapshot(input: unknown): UiSettingsSnapshot {
  const payload = asRecord(input);
  const current = getUiSettingsSnapshot();
  const next: UiSettingsSnapshot = {
    themeMode: normalizeThemeMode(payload.themeMode, current.themeMode),
    contrastMode: normalizeContrastMode(payload.contrastMode, current.contrastMode),
    timerNotifications: normalizeBoolean(payload.timerNotifications, current.timerNotifications),
    timerSound: normalizeBoolean(payload.timerSound, current.timerSound)
  };

  setThemeMode(next.themeMode);
  setContrastMode(next.contrastMode);
  setTimerNotificationsEnabled(next.timerNotifications);
  setTimerSoundEnabled(next.timerSound);

  return getUiSettingsSnapshot();
}

export function resetUiSettings(): UiSettingsSnapshot {
  setThemeMode(DEFAULT_UI_SETTINGS.themeMode);
  setContrastMode(DEFAULT_UI_SETTINGS.contrastMode);
  setTimerNotificationsEnabled(DEFAULT_UI_SETTINGS.timerNotifications);
  setTimerSoundEnabled(DEFAULT_UI_SETTINGS.timerSound);
  return getUiSettingsSnapshot();
}
