export type ThemeMode = "dark" | "light";
export type ContrastMode = "normal" | "high";
export type DesignVariant = "default" | "terminal";

export type UiSettingsSnapshot = {
  themeMode: ThemeMode;
  contrastMode: ContrastMode;
  designVariant: DesignVariant;
  timerNotifications: boolean;
  timerSound: boolean;
  apiWriteToken: string;
};

const KEY_THEME_MODE = "aw.ui.theme";
const KEY_CONTRAST_MODE = "aw.ui.contrast";
const KEY_DESIGN_VARIANT = "aw.ui.design";
const KEY_TIMER_NOTIFICATIONS = "aw.timer.notifications";
const KEY_TIMER_SOUND = "aw.timer.sound";
const KEY_API_WRITE_TOKEN = "aw.api.writeToken";
const IMPORT_KEYS = new Set([
  "themeMode",
  "contrastMode",
  "designVariant",
  "timerNotifications",
  "timerSound",
  "apiWriteToken"
]);

const TRUE_VALUES = new Set(["1", "true", "yes", "on"]);
const FALSE_VALUES = new Set(["0", "false", "no", "off"]);

export const DEFAULT_UI_SETTINGS: UiSettingsSnapshot = {
  themeMode: "dark",
  contrastMode: "normal",
  designVariant: "default",
  timerNotifications: false,
  timerSound: false,
  apiWriteToken: ""
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

function normalizeDesignVariant(value: unknown, fallback: DesignVariant): DesignVariant {
  const raw = String(value || "")
    .trim()
    .toLowerCase();
  if (raw === "terminal") return "terminal";
  if (raw === "default") return "default";
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

function parseThemeModeFromImport(value: unknown, fallback: ThemeMode): ThemeMode {
  if (typeof value === "undefined") return fallback;
  const raw = String(value || "")
    .trim()
    .toLowerCase();
  if (raw === "light" || raw === "white") return "light";
  if (raw === "dark") return "dark";
  throw new Error("themeMode must be 'dark' or 'light'");
}

function parseDesignVariantFromImport(
  value: unknown,
  fallback: DesignVariant
): DesignVariant {
  if (typeof value === "undefined") return fallback;
  const raw = String(value || "")
    .trim()
    .toLowerCase();
  if (raw === "terminal") return "terminal";
  if (raw === "default") return "default";
  throw new Error("designVariant must be 'default' or 'terminal'");
}

function parseContrastModeFromImport(
  value: unknown,
  fallback: ContrastMode
): ContrastMode {
  if (typeof value === "undefined") return fallback;
  const raw = String(value || "")
    .trim()
    .toLowerCase();
  if (raw === "high" || raw === "high-contrast") return "high";
  if (raw === "normal") return "normal";
  throw new Error("contrastMode must be 'normal' or 'high'");
}

function parseBooleanFromImport(
  value: unknown,
  fallback: boolean,
  fieldName: string
): boolean {
  if (typeof value === "undefined") return fallback;
  if (typeof value === "boolean") return value;
  const raw = String(value || "")
    .trim()
    .toLowerCase();
  if (TRUE_VALUES.has(raw)) return true;
  if (FALSE_VALUES.has(raw)) return false;
  throw new Error(`${fieldName} must be a boolean`);
}

function parseStringFromImport(value: unknown, fallback: string): string {
  if (typeof value === "undefined") return fallback;
  return String(value || "").trim();
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

export function getDesignVariant(): DesignVariant {
  return normalizeDesignVariant(readString(KEY_DESIGN_VARIANT), DEFAULT_UI_SETTINGS.designVariant);
}

export function setDesignVariant(variant: DesignVariant): void {
  writeString(KEY_DESIGN_VARIANT, variant);
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

export function getApiWriteToken(): string {
  return readString(KEY_API_WRITE_TOKEN);
}

export function setApiWriteToken(token: string): void {
  writeString(KEY_API_WRITE_TOKEN, String(token || "").trim());
}

export function getUiSettingsSnapshot(): UiSettingsSnapshot {
  return {
    themeMode: getThemeMode(),
    contrastMode: getContrastMode(),
    designVariant: getDesignVariant(),
    timerNotifications: getTimerNotificationsEnabled(),
    timerSound: getTimerSoundEnabled(),
    apiWriteToken: getApiWriteToken()
  };
}

export function applyUiSettingsSnapshot(input: unknown): UiSettingsSnapshot {
  const payload = asRecord(input);
  if (!Object.keys(payload).some((key) => IMPORT_KEYS.has(key))) {
    throw new Error("settings import contains no supported fields");
  }
  const current = getUiSettingsSnapshot();
  const next: UiSettingsSnapshot = {
    themeMode: parseThemeModeFromImport(payload.themeMode, current.themeMode),
    contrastMode: parseContrastModeFromImport(payload.contrastMode, current.contrastMode),
    designVariant: parseDesignVariantFromImport(payload.designVariant, current.designVariant),
    timerNotifications: parseBooleanFromImport(
      payload.timerNotifications,
      current.timerNotifications,
      "timerNotifications"
    ),
    timerSound: parseBooleanFromImport(payload.timerSound, current.timerSound, "timerSound"),
    apiWriteToken: parseStringFromImport(payload.apiWriteToken, current.apiWriteToken)
  };

  setThemeMode(next.themeMode);
  setContrastMode(next.contrastMode);
  setDesignVariant(next.designVariant);
  setTimerNotificationsEnabled(next.timerNotifications);
  setTimerSoundEnabled(next.timerSound);
  setApiWriteToken(next.apiWriteToken);

  return getUiSettingsSnapshot();
}

export function resetUiSettings(): UiSettingsSnapshot {
  setThemeMode(DEFAULT_UI_SETTINGS.themeMode);
  setContrastMode(DEFAULT_UI_SETTINGS.contrastMode);
  setDesignVariant(DEFAULT_UI_SETTINGS.designVariant);
  setTimerNotificationsEnabled(DEFAULT_UI_SETTINGS.timerNotifications);
  setTimerSoundEnabled(DEFAULT_UI_SETTINGS.timerSound);
  setApiWriteToken(DEFAULT_UI_SETTINGS.apiWriteToken);
  return getUiSettingsSnapshot();
}
