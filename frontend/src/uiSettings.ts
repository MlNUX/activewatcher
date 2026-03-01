export type ThemeMode = "dark" | "light";

const KEY_THEME_MODE = "aw.ui.theme";

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

export function getThemeMode(): ThemeMode {
  const raw = readString(KEY_THEME_MODE).toLowerCase();
  if (raw === "light" || raw === "white") return "light";
  return "dark";
}

export function setThemeMode(mode: ThemeMode): void {
  writeString(KEY_THEME_MODE, mode);
}
