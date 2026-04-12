import { useState, useEffect } from "react"
import { motion as Motion } from "framer-motion"
import { getDashboard } from "../api"
import { getSettings } from "../settings"

export default function Sidebar({ active, onNavigate, userName, onLogout, refreshKey, isMobile = false }) {
  const [data, setData] = useState(null)
  const [localRefresh, setLocalRefresh] = useState(0)
  const [settings, setSettings] = useState(getSettings)

  useEffect(() => {
    getDashboard().then(setData).catch(() => {})
  }, [refreshKey, localRefresh])

  // Listen for trade events
  useEffect(() => {
    const handler = () => setLocalRefresh(k => k + 1)
    window.addEventListener("finfuture-transaction", handler)
    return () => window.removeEventListener("finfuture-transaction", handler)
  }, [])

  // Listen for settings changes
  useEffect(() => {
    const handler = () => setSettings(getSettings())
    window.addEventListener("finfuture-settings", handler)
    return () => window.removeEventListener("finfuture-settings", handler)
  }, [])

  const hide = settings.hideBalance
  const mask = (val) => hide ? "•••••" : val

  const level = data?.level_info?.current || { name: "Новичок", icon: "🌱", level: 1 }
  const xp = data?.xp || 0
  const xpFrom = data?.level_info?.current?.xp_from || 0
  const xpTo = data?.level_info?.next?.xp_from || data?.level_info?.current?.xp_to || 200
  const xpProgress = xpTo > xpFrom ? (xp - xpFrom) / (xpTo - xpFrom) : 0
  const streak = data?.streak || 0
  const balance = data?.balance?.current ?? 0
  const income = data?.income?.month ?? 0
  const expenses = data?.expenses?.month ?? 0
  const balanceChange = income - expenses
  const changeSign = balanceChange >= 0

  const tabs = [
    { id: "home", label: "Главная", icon: "/icons/free-icon-home-6529015.png" },
    { id: "transactions", label: "Транзакции", icon: "/icons/free-icon-money-bag-7510557.png" },
    { id: "ai-advisor", label: "AI-Советник", icon: "/icons/free-icon-robot-14224105.png" },
    { id: "achievements", label: "Достижения", icon: "/icons/free-icon-checkmark-16703458.png" },
    { id: "about", label: "О проекте", icon: "/icons/tbank/book-open.png" },
    { id: "settings", label: "Настройки", icon: "/icons/free-icon-setting-6619132.png" },
  ]

  return (
    <Motion.div
      style={{ ...s.sidebar, ...(isMobile ? s.sidebarMobile : {}) }}
      initial={isMobile ? { y: -18, opacity: 0 } : { x: -40, opacity: 0 }}
      animate={isMobile ? { y: 0, opacity: 1 } : { x: 0, opacity: 1 }}
      transition={{ duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
    >
      {/* Logo */}
      <Motion.div
        style={s.logo}
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.3 }}
      >
        <img src="/icons/F-Kernel.png" alt="Kernel" style={{...s.logoImg, cursor: "pointer"}} onClick={() => onNavigate("home")} />
      </Motion.div>

      <div style={{ ...s.divider, ...(isMobile ? s.dividerMobile : {}) }} />

      {/* Balance Summary */}
      <Motion.div
        style={s.portfolioBox}
        onClick={() => onNavigate("transactions")}
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.15, duration: 0.3 }}
        whileHover={{ scale: 1.02, background: "#eef0f2" }}
        whileTap={{ scale: 0.98 }}
      >
        <div style={s.portfolioLabel}>БАЛАНС</div>
        <Motion.div
          style={s.portfolioValue}
          key={balance}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          {mask(balance.toLocaleString("ru-RU", { maximumFractionDigits: 0 }) + " с")}
        </Motion.div>
        <div style={{ ...s.portfolioPnl, color: changeSign ? "#21a038" : "#f44336" }}>
          {hide ? "•••" : `${changeSign ? "+" : ""}${balanceChange.toLocaleString("ru-RU")} с за месяц`}
        </div>
        {expenses > 0 && (
          <div style={s.portfolioFree}>
            Расходы: {mask(expenses.toLocaleString("ru-RU", { maximumFractionDigits: 0 }) + " с")}
          </div>
        )}
      </Motion.div>

      <div style={{ ...s.divider, ...(isMobile ? s.dividerMobile : {}) }} />

      {/* Navigation */}
      <nav style={{ ...s.nav, ...(isMobile ? s.navMobile : {}) }}>
        {tabs.map((t, i) => (
          <Motion.button
            key={t.id}
            onClick={() => onNavigate(t.id)}
            style={{
              ...s.navBtn,
              ...(isMobile ? s.navBtnMobile : {}),
              ...(active === t.id ? s.navBtnActive : {}),
              position: "relative",
            }}
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 + i * 0.05, duration: 0.28 }}
            whileHover={{ x: 3, background: active === t.id ? "rgba(255,221,45,0.15)" : "rgba(0,0,0,0.04)" }}
            whileTap={{ scale: 0.97 }}
          >
            {active === t.id && (
              <Motion.div
                layoutId="nav-indicator"
                style={{
                  position: "absolute", left: 0, top: "15%", bottom: "15%",
                  width: 3, background: "#ffdd2d", borderRadius: "0 3px 3px 0",
                }}
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}
            <img src={t.icon} alt="" style={{ ...s.navIconImg, ...(isMobile ? s.navIconImgMobile : {}) }} />
            <span style={isMobile ? s.navTextMobile : undefined}>{t.label}</span>
          </Motion.button>
        ))}
      </nav>

      <div style={{ ...s.divider, ...(isMobile ? s.dividerMobile : {}) }} />

      {/* Level & XP */}
      <Motion.div
        style={s.levelBox}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.45, duration: 0.3 }}
      >
        <div style={s.levelHeader}>
          <Motion.span
            style={s.levelIcon}
            animate={{ rotate: [0, -5, 5, 0] }}
            transition={{ duration: 2, repeat: Infinity, repeatDelay: 4, ease: "easeInOut" }}
          >
            {level.icon}
          </Motion.span>
          <span style={s.levelName}>{level.name}</span>
        </div>
        <div style={s.xpBar}>
          <Motion.div
            style={s.xpFill}
            initial={{ width: 0 }}
            animate={{ width: `${Math.min(xpProgress * 100, 100)}%` }}
            transition={{ duration: 0.9, ease: "easeOut", delay: 0.5 }}
          />
        </div>
        <div style={s.xpText}>{xp} / {xpTo} XP</div>
      </Motion.div>

      {/* Streak */}
      {streak > 0 && (
        <Motion.div
          style={s.streakBox}
          initial={{ opacity: 0, scale: 0.85 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: "spring", stiffness: 400, damping: 18, delay: 0.55 }}
        >
          <Motion.img
            src="/icons/free-icon-flames-4201705.png"
            alt=""
            style={{ width: 20, height: 20 }}
            animate={{ scale: [1, 1.2, 1], rotate: [-5, 5, -5] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
          />
          <span style={s.streakNum}>{streak}</span>
          <span style={s.streakLabel}>{streak === 1 ? "день" : streak < 5 ? "дня" : "дней"}</span>
        </Motion.div>
      )}

      <div style={{ flex: 1, minHeight: isMobile ? 0 : undefined }} />

      {/* User */}
      <Motion.div
        style={{ ...s.userBox, ...(isMobile ? s.userBoxMobile : {}) }}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.3 }}
      >
        <Motion.div
          style={s.avatar}
          whileHover={{ scale: 1.08 }}
          transition={{ type: "spring", stiffness: 400, damping: 16 }}
        >
          {userName?.[0]?.toUpperCase() || "?"}
        </Motion.div>
        <div style={s.userInfo}>
          <div style={s.userName}>{userName}</div>
          <div style={s.userEmail}>{localStorage.getItem("finfuture_email") || ""}</div>
        </div>
      </Motion.div>
      <Motion.button
        onClick={onLogout}
        style={{ ...s.logoutBtn, ...(isMobile ? s.logoutBtnMobile : {}) }}
        whileHover={{ background: "rgba(244,67,54,0.06)", color: "#f44336", borderColor: "rgba(244,67,54,0.2)" }}
        transition={{ duration: 0.2 }}
      >
        Выйти
      </Motion.button>
    </Motion.div>
  )
}

const s = {
  sidebar: {
    position: "fixed",
    left: 0,
    top: 0,
    bottom: 0,
    width: 260,
    background: "#ffffff",
    borderRight: "1px solid rgba(0,0,0,0.08)",
    display: "flex",
    flexDirection: "column",
    padding: "20px 16px",
    zIndex: 100,
    overflowY: "auto",
  },
  sidebarMobile: {
    position: "sticky",
    width: "100%",
    top: 0,
    bottom: "auto",
    left: "auto",
    borderRight: "none",
    borderBottom: "1px solid rgba(0,0,0,0.08)",
    padding: "12px 12px 10px",
    zIndex: 200,
    overflowY: "visible",
  },
  logo: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "4px 8px",
    marginBottom: 4,
  },
  logoImg: {
    height: 32,
    objectFit: "contain",
  },
  divider: {
    height: 1,
    background: "rgba(0,0,0,0.06)",
    margin: "12px 0",
  },
  dividerMobile: {
    margin: "10px 0",
  },
  portfolioBox: {
    background: "#f6f7f8",
    borderRadius: 12,
    padding: "12px 14px",
    cursor: "pointer",
    transition: "background 0.2s",
  },
  portfolioLabel: {
    fontSize: 11,
    color: "rgba(0,0,0,0.45)",
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: 4,
    fontWeight: 600,
  },
  portfolioValue: {
    fontSize: 20,
    fontWeight: 700,
    color: "#1a1a1a",
  },
  portfolioPnl: {
    fontSize: 13,
    fontWeight: 600,
    marginTop: 2,
  },
  portfolioFree: {
    fontSize: 11,
    color: "rgba(0,0,0,0.4)",
    marginTop: 4,
  },
  nav: {
    display: "flex",
    flexDirection: "column",
    gap: 2,
  },
  navMobile: {
    flexDirection: "row",
    gap: 8,
    overflowX: "auto",
    paddingBottom: 4,
  },
  navBtn: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "10px 14px",
    border: "none",
    borderRadius: 10,
    background: "transparent",
    color: "rgba(0,0,0,0.55)",
    fontSize: 14,
    fontWeight: 500,
    cursor: "pointer",
    transition: "all 0.2s",
    textAlign: "left",
    width: "100%",
    fontFamily: "inherit",
  },
  navBtnMobile: {
    minWidth: 112,
    padding: "10px 12px",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    gap: 6,
    textAlign: "center",
    flexShrink: 0,
  },
  navBtnActive: {
    background: "rgba(255,221,45,0.15)",
    color: "#1a1a1a",
    fontWeight: 600,
  },
  navIconImg: {
    width: 22,
    height: 22,
    objectFit: "contain",
  },
  navIconImgMobile: {
    width: 20,
    height: 20,
  },
  navTextMobile: {
    fontSize: 11,
    lineHeight: 1.2,
  },
  levelBox: {
    padding: "12px 14px",
    background: "#f6f7f8",
    borderRadius: 12,
    marginBottom: 8,
  },
  levelHeader: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 8,
  },
  levelIcon: { fontSize: 20 },
  levelName: {
    fontSize: 13,
    fontWeight: 600,
    color: "#1a1a1a",
  },
  xpBar: {
    height: 6,
    background: "rgba(0,0,0,0.06)",
    borderRadius: 3,
    overflow: "hidden",
    marginBottom: 4,
  },
  xpFill: {
    height: "100%",
    background: "linear-gradient(90deg, #ffdd2d, #ffa000)",
    borderRadius: 3,
    transition: "width 0.5s ease",
  },
  xpText: {
    fontSize: 11,
    color: "rgba(0,0,0,0.4)",
  },
  streakBox: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "10px 14px",
    background: "linear-gradient(135deg, rgba(255,152,0,0.1), rgba(255,87,34,0.06))",
    borderRadius: 12,
    marginTop: 4,
  },
  streakNum: {
    fontSize: 20,
    fontWeight: 800,
    color: "#ff9800",
  },
  streakLabel: {
    fontSize: 13,
    color: "rgba(0,0,0,0.45)",
  },
  userBox: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "8px 4px",
    marginBottom: 4,
  },
  userBoxMobile: {
    padding: "8px 2px 0",
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: "50%",
    background: "#ffdd2d",
    color: "#1a1a1a",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 700,
    fontSize: 16,
    flexShrink: 0,
  },
  userInfo: {
    overflow: "hidden",
  },
  userName: {
    fontSize: 13,
    fontWeight: 600,
    color: "#1a1a1a",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  userEmail: {
    fontSize: 11,
    color: "rgba(0,0,0,0.4)",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  logoutBtn: {
    padding: "8px 14px",
    border: "1px solid rgba(0,0,0,0.08)",
    borderRadius: 8,
    background: "transparent",
    color: "rgba(0,0,0,0.45)",
    fontSize: 12,
    cursor: "pointer",
    fontFamily: "inherit",
    transition: "all 0.2s",
    width: "100%",
  },
  logoutBtnMobile: {
    marginTop: 8,
  },
}
