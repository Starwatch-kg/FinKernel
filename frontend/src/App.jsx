import { useState, useEffect } from "react"
import { AnimatePresence, motion as Motion } from "framer-motion"
import { DevContext } from "./DevContext"

const pageVariants = {
  initial: { opacity: 0, y: 18, scale: 0.99 },
  animate: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.3, ease: [0.25, 0.1, 0.25, 1] } },
  exit:    { opacity: 0, y: -10, scale: 0.99, transition: { duration: 0.18 } },
}
const LLM_MODEL = "Qwen 2.5 7B"
import Sidebar from "./components/Sidebar"
import HomeScreen from "./screens/HomeScreen"
import TransactionsScreen from "./screens/PortfolioScreen"
import AIAdvisorScreen from "./screens/LearnScreen"
import LessonScreen from "./screens/LessonScreen"
import AchievementsScreen from "./screens/AchievementsScreen"
import SettingsScreen from "./screens/SettingsScreen"
import AboutScreen from "./screens/AboutScreen"
import AuthScreen from "./screens/AuthScreen"
import Tutorial from "./components/Tutorial"
import { clearAuth, isAdmin } from "./api"
import { getSettings } from "./settings"

export default function App() {
  const validTabs = ["home", "transactions", "ai-advisor", "achievements", "about", "settings"]
  const savedTab = localStorage.getItem("finfuture_tab") || "home"
  const initialTab = validTabs.includes(savedTab) ? savedTab : "home"
  const [screen, setScreen] = useState(initialTab)
  const [tab, setTab] = useState(initialTab)
  const [user, setUser] = useState(null)
  const [lessonId, setLessonId] = useState(null)
  const [aiLessonData, setAiLessonData] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [initializing, setInitializing] = useState(true)
  const [showTutorial, setShowTutorial] = useState(false)
  const [devMode, setDevMode] = useState(false)
  const [timeOffset, setTimeOffset] = useState(0)
  const [unlockAll, setUnlockAll] = useState(false)
  const [aiStatus, setAiStatus] = useState("")
  const [aiLog, setAiLog] = useState([])
  const [appSettings, setAppSettings] = useState(getSettings)

  useEffect(() => {
    const handler = () => setAppSettings(getSettings())
    window.addEventListener("finfuture-settings", handler)
    return () => window.removeEventListener("finfuture-settings", handler)
  }, [])

  // Toggle global no-animations class on <html>
  useEffect(() => {
    if (appSettings.animations) {
      document.documentElement.classList.remove("no-animations")
    } else {
      document.documentElement.classList.add("no-animations")
    }
  }, [appSettings.animations])

  // On mount: restore saved session
  useEffect(() => {
    const savedName = localStorage.getItem("finfuture_name")
    const savedEmail = localStorage.getItem("finfuture_email")
    if (savedName && savedEmail) {
      setUser(savedName)
    }
    setInitializing(false)
  }, [])

  const handleAuth = (name, isNewUser = false) => {
    setUser(name)
    // Show tutorial for new users
    if (isNewUser && !localStorage.getItem("finfuture_tutorial_done")) {
      setShowTutorial(true)
    }
  }

  const handleLogout = () => {
    setUser(null)
    setShowTutorial(false)
    clearAuth()
    localStorage.removeItem("finfuture_tutorial_done")
  }

  const handleNavigate = (id) => {
    setTab(id)
    setScreen(id)
    localStorage.setItem("finfuture_tab", id)
  }

  const handleStartLesson = (id, aiData = null) => {
    setLessonId(id)
    setAiLessonData(aiData || null)
    setScreen("lesson")
  }

  const handleLessonComplete = () => {
    setRefreshKey(k => k + 1)
    setScreen("ai-advisor")
    setTab("ai-advisor")
    localStorage.setItem("finfuture_tab", "ai-advisor")
  }

  const handleBack = () => {
    setScreen("ai-advisor")
    setTab("ai-advisor")
    localStorage.setItem("finfuture_tab", "ai-advisor")
  }

  // Initial loading
  if (initializing) {
    return (
      <Motion.div style={s.center} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}>
        <Motion.div
          animate={{ scale: [1, 1.15, 1], opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
          style={{ fontSize: 13, letterSpacing: 1 }}
        >Загрузка...</Motion.div>
      </Motion.div>
    )
  }

  // Step 1: Not logged in → Auth screen
  if (!user) {
    return (
      <div style={s.fullPage}>
        <AuthScreen onAuth={handleAuth} />
      </div>
    )
  }

  // Step 2: Main app
  return (
    <DevContext.Provider value={{ devMode, timeOffset, unlockAll, aiStatus, setAiStatus: (msg) => { setAiStatus(msg); setAiLog(log => [...log.slice(-19), { time: new Date().toLocaleTimeString("ru-RU"), msg }]) }, aiLog }}>
      <div style={s.layout}>
        {/* Admin panel - only visible for admin@admin.com */}
        {isAdmin() && (
          <>
            <button
              onClick={() => setDevMode(d => !d)}
              style={s.devBtn}
              title="Админ-панель"
            >⚙</button>

            {devMode && (
              <div style={s.devPanel}>
                <div style={s.devTitle}>Админ-панель</div>
                <div style={s.devRow}>
                  <span style={s.devLabel}>Время: +{timeOffset}ч</span>
                  <button style={s.devAction} onClick={() => setTimeOffset(0)}>Сброс</button>
                </div>
                <div style={s.devRow}>
                  <label style={s.devLabel}>
                    <input
                      type="checkbox"
                      checked={unlockAll}
                      onChange={e => setUnlockAll(e.target.checked)}
                      style={{ marginRight: 6 }}
                    />
                    Разблокировать все карточки
                  </label>
                </div>
                <div style={s.devInfo}>
                  Сдвиг: {new Date(Date.now() + timeOffset * 3600000).toLocaleString("ru-RU")}
                </div>
                <div style={s.devDivider} />
                <div style={s.devAiHeader}>
                  <span>🤖 AI ({LLM_MODEL})</span>
                  <span style={{ ...s.devAiDot, background: aiStatus.includes("...") ? "#FFA000" : aiStatus.includes("✓") ? "#21a038" : "rgba(0,0,0,0.15)" }} />
                </div>
                <div style={s.devAiStatus}>{aiStatus || "Ожидание"}</div>
                <div style={s.devAiLog}>
                  {aiLog.map((entry, i) => (
                    <div key={i} style={s.devAiLogEntry}>
                      <span style={s.devAiLogTime}>{entry.time}</span> {entry.msg}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {showTutorial && (
          <Tutorial
            userName={user}
            onComplete={() => setShowTutorial(false)}
          />
        )}
        <Sidebar
          active={tab}
          onNavigate={handleNavigate}
          userName={user}
          onLogout={handleLogout}
          refreshKey={refreshKey}
        />
        <main style={s.main}>
          {appSettings.animations ? (
            <AnimatePresence mode="wait">
              {screen === "home" && (
                <Motion.div key={`home-${refreshKey}`} {...pageVariants}>
                  <HomeScreen onStartLesson={handleStartLesson} onNavigate={handleNavigate} />
                </Motion.div>
              )}
              {screen === "transactions" && (
                <Motion.div key="transactions" {...pageVariants}>
                  <TransactionsScreen onRefresh={() => setRefreshKey(k => k + 1)} />
                </Motion.div>
              )}
              {screen === "ai-advisor" && (
                <Motion.div key="ai-advisor" {...pageVariants}>
                  <AIAdvisorScreen onStartLesson={handleStartLesson} />
                </Motion.div>
              )}
              {screen === "lesson" && (
                <Motion.div key={`lesson-${lessonId}`} {...pageVariants}>
                  <LessonScreen lessonId={lessonId} aiLessonData={aiLessonData} onComplete={handleLessonComplete} onBack={handleBack} />
                </Motion.div>
              )}
              {screen === "achievements" && (
                <Motion.div key="achievements" {...pageVariants}>
                  <AchievementsScreen />
                </Motion.div>
              )}
              {screen === "about" && (
                <Motion.div key="about" {...pageVariants}>
                  <AboutScreen />
                </Motion.div>
              )}
              {screen === "settings" && (
                <Motion.div key="settings" {...pageVariants}>
                  <SettingsScreen />
                </Motion.div>
              )}
            </AnimatePresence>
          ) : (
            <>
              {screen === "home" && <HomeScreen onStartLesson={handleStartLesson} onNavigate={handleNavigate} />}
              {screen === "transactions" && <TransactionsScreen onRefresh={() => setRefreshKey(k => k + 1)} />}
              {screen === "ai-advisor" && <AIAdvisorScreen onStartLesson={handleStartLesson} />}
              {screen === "lesson" && <LessonScreen lessonId={lessonId} aiLessonData={aiLessonData} onComplete={handleLessonComplete} onBack={handleBack} />}
              {screen === "achievements" && <AchievementsScreen />}
              {screen === "about" && <AboutScreen />}
              {screen === "settings" && <SettingsScreen />}
            </>
          )}
        </main>
      </div>
    </DevContext.Provider>
  )
}

const s = {
  fullPage: {
    minHeight: "100vh",
    background: "#f6f7f8",
    fontFamily: "Inter, sans-serif",
  },
  center: {
    minHeight: "100vh",
    background: "#f6f7f8",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontFamily: "Inter, sans-serif",
    color: "rgba(0,0,0,0.45)",
  },
  layout: {
    display: "flex",
    minHeight: "100vh",
    background: "#f6f7f8",
    fontFamily: "Inter, sans-serif",
    color: "#1a1a1a",
  },
  main: {
    flex: 1,
    marginLeft: 260,
    minHeight: "100vh",
    padding: "24px 32px",
    overflowY: "auto",
  },
  devBtn: {
    position: "fixed", bottom: 8, right: 8, zIndex: 9999,
    width: 28, height: 28, borderRadius: 6,
    border: "1px solid rgba(0,0,0,0.1)", background: "rgba(255,255,255,0.9)",
    cursor: "pointer", fontSize: 14, color: "rgba(0,0,0,0.4)",
    display: "flex", alignItems: "center", justifyContent: "center",
  },
  devPanel: {
    position: "fixed", bottom: 40, right: 8, zIndex: 9999,
    background: "#fff", border: "1px solid rgba(0,0,0,0.15)",
    borderRadius: 10, padding: "12px 16px", width: 220,
    boxShadow: "0 4px 16px rgba(0,0,0,0.12)", fontSize: 12,
    maxHeight: "60vh", overflowY: "auto",
  },
  devTitle: {
    fontWeight: 700, fontSize: 13, marginBottom: 10,
    color: "#1a1a1a", borderBottom: "1px solid rgba(0,0,0,0.06)", paddingBottom: 6,
  },
  devRow: {
    display: "flex", alignItems: "center", gap: 6, marginBottom: 8,
  },
  devLabel: {
    flex: 1, fontSize: 12, color: "#1a1a1a", display: "flex", alignItems: "center", cursor: "pointer",
  },
  devAction: {
    padding: "3px 8px", borderRadius: 5, border: "1px solid rgba(0,0,0,0.12)",
    background: "#f6f7f8", cursor: "pointer", fontSize: 11, fontFamily: "inherit",
  },
  devInfo: {
    fontSize: 10, color: "rgba(0,0,0,0.35)", marginTop: 4,
  },
  devDivider: { height: 1, background: "rgba(0,0,0,0.08)", margin: "10px 0" },
  devAiHeader: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    fontSize: 12, fontWeight: 600, color: "#1a1a1a", marginBottom: 4,
  },
  devAiDot: { width: 8, height: 8, borderRadius: "50%" },
  devAiStatus: { fontSize: 11, color: "rgba(0,0,0,0.5)", marginBottom: 6 },
  devAiLog: { maxHeight: 120, overflowY: "auto", fontSize: 10, color: "rgba(0,0,0,0.4)" },
  devAiLogEntry: { padding: "2px 0", borderBottom: "1px solid rgba(0,0,0,0.04)" },
  devAiLogTime: { color: "rgba(0,0,0,0.25)", marginRight: 4 },
}
