import { useEffect, useState } from "react";

import { getThemeMode, setThemeMode, type ThemeMode } from "./uiSettings";

export function useThemeMode(): [ThemeMode, (mode: ThemeMode) => void] {
  const [themeMode, setThemeModeState] = useState<ThemeMode>(() => getThemeMode());

  useEffect(() => {
    if (typeof document === "undefined") return;
    document.body.classList.toggle("theme-light", themeMode === "light");
  }, [themeMode]);

  function onThemeModeChange(next: ThemeMode): void {
    setThemeModeState(next);
    setThemeMode(next);
  }

  return [themeMode, onThemeModeChange];
}
