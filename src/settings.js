const SETTINGS_KEY = "finfuture_settings"

function loadSettings() {
  try {
    return JSON.parse(localStorage.getItem(SETTINGS_KEY)) || {}
  } catch { return {} }
}

export function saveSettings(s) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(s))
  window.dispatchEvent(new Event("finfuture-settings"))
}

export function getSettings() {
  const s = loadSettings()
  return {
    hideBalance: s.hideBalance ?? false,
    confirmTrades: s.confirmTrades ?? true,
    animations: s.animations ?? true,
    compactList: s.compactList ?? false,
    showPnlPercent: s.showPnlPercent ?? true,
  }
}
