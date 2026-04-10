import { useState, useEffect, useRef } from "react"
import { motion as Motion, AnimatePresence } from "framer-motion"
import { getDashboard, marketEventAction, checkPortfolio } from "../api"

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.05 } },
}
const item = {
  hidden: { opacity: 0, y: 20 },
  show:   { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.25, 0.1, 0.25, 1] } },
}
const statItem = {
  hidden: { opacity: 0, scale: 0.8, y: 10 },
  show:   { opacity: 1, scale: 1, y: 0, transition: { type: "spring", stiffness: 400, damping: 20 } },
}

function AnimatedNumber({ value, suffix = "" }) {
  const [display, setDisplay] = useState(0)
  const ref = useRef(null)
  useEffect(() => {
    const target = parseFloat(String(value).replace(/[^\d.-]/g, "")) || 0
    const duration = 700
    const start = Date.now()
    const tick = () => {
      const elapsed = Date.now() - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplay(Math.round(eased * target))
      if (progress < 1) ref.current = requestAnimationFrame(tick)
    }
    ref.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(ref.current)
  }, [value])
  return <>{display.toLocaleString("ru-RU")}{suffix}</>
}

export default function HomeScreen({ onStartLesson, onNavigate }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const load = () => { setLoading(true); setError(null); getDashboard().then(d => { setData(d); setLoading(false) }).catch(e => { setError(e.message||"Ошибка"); setLoading(false) }); checkPortfolio().catch(() => {}) }
  useEffect(() => { load() }, [])

  if (loading) return <div style={s.loading}>Загрузка...</div>
  if (error || !data) return <div style={s.loading}><div style={{fontSize:48,marginBottom:16}}>⚠️</div><div style={{marginBottom:16}}>{error||"Ошибка"}</div><button onClick={load} style={{padding:"10px 24px",borderRadius:10,border:"1px solid rgba(0,0,0,0.12)",background:"transparent",color:"#b8860b",cursor:"pointer",fontFamily:"inherit"}}>Повторить</button></div>

  const { balance, income, expenses, transactions, forecast, ai_tips, spending_chart, stats } = data

  return (
    <Motion.div style={s.page} variants={container} initial="hidden" animate="show">
      {/* Balance Widget */}
      <Motion.div
        variants={item}
        style={s.portfolioCard}
        onClick={() => onNavigate("transactions")}
        whileHover={{ y: -3, boxShadow: "0 10px 32px rgba(0,0,0,0.12)" }}
        whileTap={{ scale: 0.99 }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
      >
        <div style={s.portfolioHeader}>
          <div>
            <div style={s.portfolioLabel}>ТЕКУЩИЙ БАЛАНС</div>
            <div style={s.portfolioValue}>
              <AnimatedNumber value={balance || 0} /> ₽
            </div>
            <div style={s.portfolioPnl}>
              <span style={{ color: "#21a038" }}>↑ {(income || 0).toLocaleString("ru-RU")} ₽</span>
              {" "}
              <span style={{ color: "#f44336" }}>↓ {(expenses || 0).toLocaleString("ru-RU")} ₽</span>
            </div>
          </div>
          <Motion.img
            src="/icons/free-icon-money-bag-7510557.png"
            alt=""
            style={{ width: 32, height: 32, opacity: 0.7 }}
            animate={{ y: [0, -4, 0] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>
      </Motion.div>

      {/* Forecast + AI Tips */}
      <div style={s.row}>
        <Motion.div variants={item} style={s.card} whileHover={{ y: -2, boxShadow: "0 8px 24px rgba(0,0,0,0.09)" }} transition={{ type: "spring", stiffness: 300, damping: 20 }}>
          <div style={s.cardLabel}>ПРОГНОЗ</div>
          {forecast?.days_left !== undefined ? (
            <>
              <div style={s.lessonTitle}>
                {forecast.days_left > 0
                  ? `Деньги закончатся через ${forecast.days_left} дн.`
                  : "Бюджет в норме"}
              </div>
              <div style={s.lessonSub}>
                {forecast.days_left > 0
                  ? `При текущих тратах ${forecast.daily_avg?.toLocaleString("ru-RU")} ₽/день`
                  : "Твои расходы под контролем"}
              </div>
              <div style={s.lessonMeta}>
                <span>📊 Средний расход: {forecast.daily_avg?.toLocaleString("ru-RU")} ₽</span>
              </div>
            </>
          ) : (
            <div style={s.allDone}><img src="/icons/free-icon-target-6745066.png" alt="" style={{width:40,height:40}} /><div>Добавь транзакции для прогноза</div></div>
          )}
        </Motion.div>

        <Motion.div variants={item} style={s.card} whileHover={{ y: -2, boxShadow: "0 8px 24px rgba(0,0,0,0.09)" }} transition={{ type: "spring", stiffness: 300, damping: 20 }}>
          <div style={s.cardLabel}>СОВЕТЫ ОТ AI</div>
          <div style={s.missionsList}>
            {ai_tips?.slice(0, 3).map((tip, i) => (
              <Motion.div
                key={i}
                style={s.missionItem}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.15 + i * 0.07, duration: 0.3 }}
              >
                <span style={{ fontSize: 18, flexShrink: 0 }}>💡</span>
                <span style={{ flex: 1, fontSize: 13, color: "#1a1a1a", lineHeight: 1.4 }}>
                  {tip.text}
                </span>
              </Motion.div>
            ))}
          </div>
          {!ai_tips?.length && (
            <div style={{ textAlign: "center", padding: "20px 0", color: "rgba(0,0,0,0.4)", fontSize: 13 }}>
              Добавь транзакции, чтобы получить персональные советы
            </div>
          )}
        </Motion.div>
      </div>

      {/* Recent Transactions */}
      <AnimatePresence>
      {transactions?.length > 0 && (
        <Motion.div
          style={s.eventCard}
          variants={item}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.35 }}
        >
          <div style={{ fontSize: 11, color: "#b8860b", fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>
            ПОСЛЕДНИЕ ТРАНЗАКЦИИ
          </div>
          {transactions.slice(0, 3).map((t, i) => (
            <div key={i} style={{ display: "flex", gap: 12, fontSize: 14, padding: "8px 0", color: "#1a1a1a", borderBottom: i < 2 ? "1px solid rgba(0,0,0,0.04)" : "none" }}>
              <span style={{ fontSize: 20 }}>💸</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{t.category}</div>
                <div style={{ fontSize: 12, color: "rgba(0,0,0,0.4)" }}>
                  {t.description || new Date(t.timestamp).toLocaleDateString("ru-RU")}
                </div>
              </div>
              <span style={{ color: t.type === "income" ? "#21a038" : "#f44336", fontWeight: 700 }}>
                {t.type === "income" ? "+" : "-"}{t.amount?.toLocaleString("ru-RU")} ₽
              </span>
            </div>
          ))}
          <Motion.button
            style={{ ...s.startBtn, marginTop: 12 }}
            onClick={() => onNavigate("transactions")}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
          >
            Все транзакции →
          </Motion.button>
        </Motion.div>
      )}
      </AnimatePresence>

      {/* Spending by Category */}
      <Motion.div variants={item} style={s.card}>
        <div style={s.cardLabel}>РАСХОДЫ ПО КАТЕГОРИЯМ</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {spending_chart?.map((cat, ci) => (
            <Motion.div
              key={cat.category}
              style={{ display: "flex", alignItems: "center", gap: 12 }}
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 + ci * 0.06, duration: 0.3 }}
            >
              <span style={{ fontSize: 20 }}>{cat.icon}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#1a1a1a", marginBottom: 4 }}>{cat.category}</div>
                <div style={{ height: 6, background: "rgba(0,0,0,0.06)", borderRadius: 3, overflow: "hidden" }}>
                  <Motion.div
                    style={{
                      height: "100%",
                      background: cat.color || "linear-gradient(90deg, #ffdd2d, #ffa000)",
                      borderRadius: 3,
                    }}
                    initial={{ width: 0 }}
                    animate={{ width: `${cat.percent}%` }}
                    transition={{ duration: 0.8, delay: 0.2 + ci * 0.08, ease: "easeOut" }}
                  />
                </div>
              </div>
              <span style={{ fontSize: 12, color: "rgba(0,0,0,0.4)", width: 80, textAlign: "right" }}>
                {cat.amount?.toLocaleString("ru-RU")} ₽
              </span>
            </Motion.div>
          ))}
          {!spending_chart?.length && (
            <div style={{ textAlign: "center", padding: "20px 0", color: "rgba(0,0,0,0.4)", fontSize: 13 }}>
              Нет данных о расходах
            </div>
          )}
        </div>
      </Motion.div>

      {/* Stats */}
      <Motion.div style={s.statsRow} variants={container}>
        {[
          { icon: "/icons/free-icon-money-bag-7510557.png", num: stats?.transactions_count || 0, label: "транзакций" },
          { icon: "/icons/free-icon-investment-5531695.png", num: `${(stats?.savings_rate || 0)}%`, label: "сбережений" },
          { icon: "/icons/free-icon-target-6745066.png", num: stats?.categories_used || 0, label: "категорий" },
          { icon: "/icons/free-icon-trophy-1152912.png", num: stats?.achievements || 0, label: "достижений" },
        ].map((st, i) => (
          <Motion.div
            key={i}
            style={s.statCard}
            variants={statItem}
            whileHover={{ y: -4, scale: 1.03, boxShadow: "0 10px 28px rgba(0,0,0,0.1)" }}
            transition={{ type: "spring", stiffness: 350, damping: 18 }}
          >
            <Motion.div
              style={{ marginBottom: 4 }}
              animate={{ y: [0, -3, 0] }}
              transition={{ duration: 2.5 + i * 0.4, repeat: Infinity, ease: "easeInOut", delay: i * 0.3 }}
            >
              <img src={st.icon} alt="" style={{ width: 32, height: 32, objectFit: "contain" }} />
            </Motion.div>
            <div style={{ fontSize: 20, fontWeight: 700, color: "#1a1a1a", marginBottom: 2 }}>{st.num}</div>
            <div style={{ fontSize: 11, color: "rgba(0,0,0,0.4)" }}>{st.label}</div>
          </Motion.div>
        ))}
      </Motion.div>
    </Motion.div>
  )
}

const s = {
  page: { maxWidth: 900, margin: "0 auto" },
  loading: { color: "rgba(0,0,0,0.45)", padding: 40, textAlign: "center", fontSize: 16 },
  portfolioCard: {
    background: "#ffffff",
    borderRadius: 16, padding: "24px 28px", marginBottom: 20,
    cursor: "pointer", border: "1px solid rgba(0,0,0,0.08)",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  portfolioHeader: { display: "flex", justifyContent: "space-between", alignItems: "center" },
  portfolioLabel: { fontSize: 11, color: "rgba(0,0,0,0.4)", letterSpacing: 2, marginBottom: 8, fontWeight: 600 },
  portfolioValue: { fontSize: 32, fontWeight: 800, color: "#1a1a1a", marginBottom: 4 },
  portfolioPnl: { fontSize: 15, fontWeight: 600 },
  row: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 },
  card: {
    background: "#ffffff", borderRadius: 16, padding: "20px 24px",
    border: "1px solid rgba(0,0,0,0.08)", marginBottom: 16,
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  cardLabel: { fontSize: 11, color: "rgba(0,0,0,0.4)", letterSpacing: 2, marginBottom: 12, fontWeight: 600 },
  lessonModule: { fontSize: 12, color: "rgba(0,0,0,0.5)", marginBottom: 6 },
  lessonTitle: { fontSize: 18, fontWeight: 700, color: "#1a1a1a", marginBottom: 4 },
  lessonSub: { fontSize: 13, color: "rgba(0,0,0,0.5)", marginBottom: 12 },
  lessonMeta: { display: "flex", gap: 16, fontSize: 12, color: "rgba(0,0,0,0.4)", marginBottom: 16 },
  startBtn: {
    width: "100%", padding: "12px 0", border: "none", borderRadius: 10,
    background: "#ffdd2d", color: "#1a1a1a", fontSize: 15, fontWeight: 700,
    cursor: "pointer", fontFamily: "inherit",
  },
  allDone: { textAlign: "center", padding: "20px 0", color: "rgba(0,0,0,0.5)", fontSize: 14 },
  missionsList: { display: "flex", flexDirection: "column", gap: 10 },
  missionItem: { display: "flex", alignItems: "center", gap: 8 },
  bonusBanner: {
    marginTop: 12, padding: "8px 12px", background: "rgba(255,221,45,0.15)",
    borderRadius: 8, color: "#b8860b", fontSize: 12, fontWeight: 600,
    display: "flex", alignItems: "center", justifyContent: "center",
  },
  eventCard: {
    background: "#ffffff",
    borderRadius: 16, padding: "20px 24px", marginBottom: 20,
    border: "1px solid rgba(0,0,0,0.08)",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  statsRow: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 },
  statCard: {
    background: "#ffffff", borderRadius: 12, padding: "16px 12px",
    textAlign: "center", border: "1px solid rgba(0,0,0,0.08)",
    boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
  },
}
