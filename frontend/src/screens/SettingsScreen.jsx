import { useState } from "react"
import { getSettings, saveSettings } from "../settings"

export default function SettingsScreen() {
  const [settings, setSettings] = useState(getSettings)

  const toggle = (key) => {
    const updated = { ...settings, [key]: !settings[key] }
    setSettings(updated)
    saveSettings(updated)
  }

  const Switch = ({ on }) => (
    <div style={{ ...s.switch, ...(on ? s.switchOn : {}) }}>
      <div style={{ ...s.switchDot, ...(on ? s.switchDotOn : {}) }} />
    </div>
  )

  return (
    <div style={s.page}>
      <div style={s.title}>Настройки</div>

      <div style={s.card}>
        <div style={s.sectionTitle}>Приватность</div>
        <div style={s.row} onClick={() => toggle("hideBalance")}>
          <div>
            <div style={s.rowLabel}>Скрывать баланс</div>
            <div style={s.rowHint}>Суммы в портфеле и сайдбаре заменяются на •••</div>
          </div>
          <Switch on={settings.hideBalance} />
        </div>
      </div>

      <div style={s.card}>
        <div style={s.sectionTitle}>О приложении</div>
        <div style={s.about}>Kernel — платформа для обучения инвестированию через интерактивные уроки и виртуальный портфель</div>
        <div style={s.version}>Версия 2.0.0</div>
      </div>
    </div>
  )
}

const s = {
  page: { maxWidth: 500, margin: "0 auto" },
  title: { fontSize: 28, fontWeight: 800, color: "#1a1a1a", marginBottom: 20 },
  card: {
    background: "#ffffff", borderRadius: 16, padding: "20px 24px",
    border: "1px solid rgba(0,0,0,0.08)", marginBottom: 12,
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  sectionTitle: {
    fontSize: 11, fontWeight: 700, color: "rgba(0,0,0,0.4)",
    textTransform: "uppercase", letterSpacing: 1, marginBottom: 14,
  },
  row: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    padding: "8px 0", cursor: "pointer", userSelect: "none",
  },
  rowLabel: { fontSize: 14, fontWeight: 600, color: "#1a1a1a" },
  rowHint: { fontSize: 12, color: "rgba(0,0,0,0.4)", marginTop: 2 },
  separator: {
    height: 1, background: "rgba(0,0,0,0.06)", margin: "8px 0",
  },
  switch: {
    width: 44, height: 24, borderRadius: 12, background: "rgba(0,0,0,0.1)",
    position: "relative", transition: "background 0.2s", flexShrink: 0, marginLeft: 16,
    cursor: "pointer",
  },
  switchOn: { background: "#ffdd2d" },
  switchDot: {
    width: 20, height: 20, borderRadius: "50%", background: "#fff",
    position: "absolute", top: 2, left: 2,
    transition: "left 0.2s", boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
  },
  switchDotOn: { left: 22 },
  about: { fontSize: 13, color: "rgba(0,0,0,0.45)", marginBottom: 8, lineHeight: 1.5 },
  version: { fontSize: 12, color: "rgba(0,0,0,0.3)" },
}
