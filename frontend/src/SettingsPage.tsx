import { type ThemeMode } from "./uiSettings";

export function SettingsPage({
  themeMode,
  onThemeModeChange
}: {
  themeMode: ThemeMode;
  onThemeModeChange: (mode: ThemeMode) => void;
}) {
  return (
    <section className="card">
      <div className="cardHd">
        <h2>Settings</h2>
      </div>
      <div className="cardBd settingsStack">
        <div className="settingsPanel">
          <div className="settingsGrid">
            <div className="settingsField">
              <span>white mode</span>
              <div className="settingsToggleRow">
                <button
                  type="button"
                  className={themeMode === "light" ? "pill active" : "pill"}
                  onClick={() => onThemeModeChange("light")}
                >
                  on
                </button>
                <button
                  type="button"
                  className={themeMode === "dark" ? "pill active" : "pill"}
                  onClick={() => onThemeModeChange("dark")}
                >
                  off
                </button>
              </div>
            </div>
          </div>

          <div className="sub settingsHint">
            theme changes are applied instantly and saved in your browser.
          </div>
        </div>
      </div>
    </section>
  );
}
