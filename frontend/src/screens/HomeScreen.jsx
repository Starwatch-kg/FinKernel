import { useState, useEffect, useRef } from "react"
import { motion as Motion, AnimatePresence } from "framer-motion"
import { getDashboard, marketEventAction } from "../api"

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.05, delayChildren: 0 } },
}
const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.2, ease: "easeOut" } },
}
const statItem = {
  hidden: { opacity: 0, scale: 0.95 },
  show: { opacity: 1, scale: 1, transition: { duration: 0.2, ease: "easeOut" } },
}

function AnimatedNumber({ value, suffix = "" }) {
  const [display, setDisplay] = useState(0)
  const ref = useRef(null)
  useEffect(() => {
    const target = parseFloat(String(value).replace(/[^\d.-]/g, "")) || 0
    const duration = 500
    const start = Date.now()
    const frameRate = 1000 / 30 // 30 FPS instead of 60
    let lastUpdate = start
    const tick = () => {
      const now = Date.now()
      if (now - lastUpdate < frameRate) {
        ref.current = requestAnimationFrame(tick)
        return
      }
      lastUpdate = now
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 2)
      setDisplay(Math.round(eased * target))
      if (progress < 1) ref.current = requestAnimationFrame(tick)
    }
    ref.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(ref.current)
  }, [value])
  return <>{display.toLocaleString("ru-RU")}{suffix}</>
}

export default function HomeScreen({ onStartLesson, onNavigate, isMobile = false }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const load = () => { setLoading(true); setError(null); getDashboard().then(d => { setData(d); setLoading(false) }).catch(e => { setError(e.message || "Ошибка"); setLoading(false) }) }
  useEffect(() => { load() }, [])

  if (loading) return <div style={s.loading}>Загрузка...</div>
  if (error || !data) return <div style={s.loading}><div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div><div style={{ marginBottom: 16 }}>{error || "Ошибка"}</div><button onClick={load} style={{ padding: "10px 24px", borderRadius: 10, border: "1px solid rgba(0,0,0,0.12)", background: "transparent", color: "#b8860b", cursor: "pointer", fontFamily: "inherit" }}>Повторить</button></div>

  const { balance, income, expenses, transactions, forecast, ai_tips, spending_chart, stats } = data

  return (
    <Motion.div style={{ ...s.page, ...(isMobile ? s.pageMobile : {}) }} variants={container} initial="hidden" animate="show">
      {/* Balance Widget with Mini Chart */}
      <Motion.div
        variants={item}
        style={{ ...s.portfolioCard, ...(isMobile ? s.cardMobile : {}) }}
        onClick={() => onNavigate("transactions")}
        whileHover={{ y: -3, boxShadow: "0 10px 32px rgba(0,0,0,0.12)" }}
        whileTap={{ scale: 0.99 }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
      >
        <div style={{ ...s.portfolioHeader, ...(isMobile ? s.portfolioHeaderMobile : {}) }}>
          <div style={{ flex: 1 }}>
            <div style={s.portfolioLabel}>ТЕКУЩИЙ БАЛАНС</div>
            <div style={{ ...s.portfolioValue, ...(isMobile ? s.portfolioValueMobile : {}) }}>
              <AnimatedNumber value={balance?.current || 0} /> с
            </div>
            <div style={s.portfolioPnl}>
              <span style={{ color: "#21a038" }}>↑ {(income?.month || 0).toLocaleString("ru-RU")} с</span>
              {" "}
              <span style={{ color: "#f44336" }}>↓ {(expenses?.month || 0).toLocaleString("ru-RU")} с</span>
            </div>
          </div>

          {/* Mini Trend Chart */}
          {transactions?.length > 0 && (
            <div style={{ width: isMobile ? 96 : 120, height: isMobile ? 52 : 60 }}>
              <svg width="120" height="60" viewBox="0 0 120 60">
                {(() => {
                  // Calculate balance trend from last 7 transactions
                  const recentTxns = transactions.slice(0, 7).reverse()
                  let runningBalance = balance?.current || 0
                  const points = [runningBalance]

                  // Calculate historical balances
                  for (let i = recentTxns.length - 1; i >= 0; i--) {
                    const txn = recentTxns[i]
                    if (txn.type === "income") {
                      runningBalance -= txn.amount
                    } else {
                      runningBalance += txn.amount
                    }
                    points.unshift(runningBalance)
                  }

                  const maxVal = Math.max(...points)
                  const minVal = Math.min(...points)
                  const range = maxVal - minVal || 1

                  // Create path
                  const pathData = points.map((val, i) => {
                    const x = (i / (points.length - 1)) * 110 + 5
                    const y = 50 - ((val - minVal) / range) * 40
                    return `${i === 0 ? 'M' : 'L'} ${x} ${y}`
                  }).join(' ')

                  return (
                    <>
                      <Motion.path
                        d={pathData}
                        fill="none"
                        stroke="#ffdd2d"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        initial={{ pathLength: 0, opacity: 0 }}
                        animate={{ pathLength: 1, opacity: 1 }}
                        transition={{ duration: 1, ease: "easeOut" }}
                      />
                      {points.map((val, i) => {
                        const x = (i / (points.length - 1)) * 110 + 5
                        const y = 50 - ((val - minVal) / range) * 40
                        return (
                          <Motion.circle
                            key={i}
                            cx={x}
                            cy={y}
                            r="2.5"
                            fill="#ffa000"
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ delay: 0.1 + i * 0.1, duration: 0.3 }}
                          />
                        )
                      })}
                    </>
                  )
                })()}
              </svg>
            </div>
          )}

          {!transactions?.length && (
            <Motion.img
              src="/icons/free-icon-money-bag-7510557.png"
              alt=""
              style={{ width: 32, height: 32, opacity: 0.7 }}
              animate={{ y: [0, -4, 0] }}
              transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            />
          )}
        </div>
      </Motion.div>

      {/* Financial Chart */}
      <Motion.div variants={item} style={{ ...s.chartCard, ...(isMobile ? s.cardMobile : {}) }}>
        <div style={s.cardLabel}>ФИНАНСОВАЯ ДИНАМИКА</div>

        {(() => {
          const txns = transactions || []

          // Build per-day buckets only for days that have data
          const dayMap = {}
          txns.forEach(t => {
            const raw = t.date || t.timestamp || ''
            const key = raw ? new Date(raw).toISOString().split('T')[0] : null
            if (!key) return
            if (!dayMap[key]) dayMap[key] = { income: 0, expense: 0, label: new Date(raw).getDate(), dateStr: key }
            if (t.type === 'income') dayMap[key].income += t.amount || 0
            else dayMap[key].expense += t.amount || 0
          })

          // Build sorted array of active days + fill gaps up to 14 days range
          const today = new Date()
          const days = []
          for (let i = 13; i >= 0; i--) {
            const d = new Date(today)
            d.setDate(d.getDate() - i)
            const key = d.toISOString().split('T')[0]
            days.push({
              key,
              label: d.getDate(),
              month: d.toLocaleString('ru-RU', { month: 'short' }),
              income: (dayMap[key] || {}).income || 0,
              expense: (dayMap[key] || {}).expense || 0,
            })
          }

          // Compute cumulative balance from right (today) backwards
          let bal = balance?.current || 0
          for (let i = days.length - 1; i >= 0; i--) {
            days[i].balance = bal
            bal -= (days[i].income - days[i].expense)
          }

          const hasData = txns.length > 0
          const maxBal = Math.max(...days.map(d => d.balance))
          const minBal = Math.min(...days.map(d => d.balance))
          const balRange = Math.max(maxBal - minBal, 1)

          const maxBar = Math.max(...days.map(d => Math.max(d.income, d.expense)), 1)

          const W = 700
          const H = 190
          const PAD = { top: 16, right: 16, bottom: 28, left: 54 }
          const IW = W - PAD.left - PAD.right
          const IH = H - PAD.top - PAD.bottom
          const n = days.length
          const step = IW / Math.max(n - 1, 1)
          const barW = Math.max(step * 0.28, 4)
          const barZone = IH * 0.32   // bottom 32% for bars
          const lineZone = IH * 0.68  // top 68% for balance line

          const getX = i => PAD.left + i * step
          const getBalY = v => {
            const pct = balRange > 0 ? (v - minBal) / balRange : 0.5
            return PAD.top + lineZone * (1 - pct)
          }

          const balPath = days.map((d, i) => `${i === 0 ? 'M' : 'L'} ${getX(i).toFixed(1)} ${getBalY(d.balance).toFixed(1)}`).join(' ')
          const areaPath = balPath +
            ` L ${getX(n - 1).toFixed(1)} ${(PAD.top + lineZone).toFixed(1)}` +
            ` L ${getX(0).toFixed(1)} ${(PAD.top + lineZone).toFixed(1)} Z`

          // Unique gradient id to avoid conflicts across re-renders
          const gradId = 'finGrad_home'

          // Y-axis grid for balance
          const gridRatios = [0, 0.5, 1]

          return (
            <div style={{ position: 'relative', width: '100%' }}>
              <svg
                viewBox={`0 0 ${W} ${H}`}
                preserveAspectRatio="none"
                style={{ display: 'block', width: '100%', height: 180 }}
              >
                <defs>
                  <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#ffdd2d" stopOpacity="0.22" />
                    <stop offset="100%" stopColor="#ffdd2d" stopOpacity="0" />
                  </linearGradient>
                  <clipPath id="chartClip">
                    <rect x={PAD.left} y={PAD.top} width={IW} height={IH} />
                  </clipPath>
                </defs>

                {/* Horizontal grid */}
                {gridRatios.map((r, i) => {
                  const y = PAD.top + lineZone * (1 - r)
                  const val = minBal + balRange * r
                  return (
                    <g key={i}>
                      <line x1={PAD.left} y1={y} x2={W - PAD.right} y2={y}
                        stroke="rgba(0,0,0,0.05)" strokeWidth="1" strokeDasharray={r === 0 ? '0' : '3,3'} />
                      <text x={PAD.left - 6} y={y + 4} textAnchor="end" fontSize="9" fill="rgba(0,0,0,0.35)">
                        {val >= 1000 ? `${(val / 1000).toFixed(0)}к` : Math.round(val)}
                      </text>
                    </g>
                  )
                })}

                {/* Separator between line zone and bar zone */}
                <line
                  x1={PAD.left} y1={PAD.top + lineZone}
                  x2={W - PAD.right} y2={PAD.top + lineZone}
                  stroke="rgba(0,0,0,0.06)" strokeWidth="1"
                />

                {/* Income bars */}
                {days.map((d, i) => {
                  if (d.income === 0) return null
                  const h = (d.income / maxBar) * barZone * 0.85
                  const x = getX(i)
                  const baseY = H - PAD.bottom
                  return (
                    <rect key={`inc-${i}`}
                      x={x - barW - 1} y={baseY - h}
                      width={barW} height={h}
                      fill="#21a038" opacity="0.45" rx="2"
                    />
                  )
                })}

                {/* Expense bars */}
                {days.map((d, i) => {
                  if (d.expense === 0) return null
                  const h = (d.expense / maxBar) * barZone * 0.85
                  const x = getX(i)
                  const baseY = H - PAD.bottom
                  return (
                    <rect key={`exp-${i}`}
                      x={x + 1} y={baseY - h}
                      width={barW} height={h}
                      fill="#f44336" opacity="0.45" rx="2"
                    />
                  )
                })}

                {/* Balance area */}
                {hasData && <path d={areaPath} fill={`url(#${gradId})`} clipPath="url(#chartClip)" />}

                {/* Balance line */}
                {hasData && (
                  <Motion.path
                    d={balPath}
                    fill="none"
                    stroke="#ffdd2d"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    clipPath="url(#chartClip)"
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 0.9, ease: 'easeOut' }}
                  />
                )}

                {/* Balance dots — every 2nd point */}
                {hasData && days.filter((_, i) => i % 2 === 0).map((d, idx) => {
                  const i = idx * 2
                  return (
                    <circle key={`dot-${i}`}
                      cx={getX(i)} cy={getBalY(d.balance)}
                      r="3" fill="#ffdd2d" stroke="#fff" strokeWidth="1.5"
                    />
                  )
                })}

                {/* X-axis date labels */}
                {days.map((d, i) => {
                  // Show every 2nd label
                  if (i % 2 !== 0) return null
                  return (
                    <text key={`xl-${i}`}
                      x={getX(i)} y={H - 8}
                      textAnchor="middle" fontSize="9" fill="rgba(0,0,0,0.38)"
                    >
                      {d.label}
                    </text>
                  )
                })}
              </svg>

              {/* Empty state */}
              {!hasData && (
                <div style={{
                  position: 'absolute', inset: 0,
                  display: 'flex', flexDirection: 'column',
                  alignItems: 'center', justifyContent: 'center',
                  color: 'rgba(0,0,0,0.3)', fontSize: 13,
                }}>
                  <div style={{ fontSize: 28, marginBottom: 8 }}>📊</div>
                  <div>Добавь транзакции, чтобы увидеть динамику</div>
                </div>
              )}

              {/* Legend */}
              <div style={{ display: 'flex', gap: 20, justifyContent: 'center', marginTop: 10, fontSize: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 14, height: 2.5, background: '#ffdd2d', borderRadius: 2 }} />
                  <span style={{ color: 'rgba(0,0,0,0.55)', fontSize: 11 }}>Баланс</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 10, height: 10, background: '#21a038', opacity: 0.5, borderRadius: 2 }} />
                  <span style={{ color: 'rgba(0,0,0,0.55)', fontSize: 11 }}>Доходы</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 10, height: 10, background: '#f44336', opacity: 0.5, borderRadius: 2 }} />
                  <span style={{ color: 'rgba(0,0,0,0.55)', fontSize: 11 }}>Расходы</span>
                </div>
              </div>
            </div>
          )
        })()}
      </Motion.div>

      {/* Forecast + AI Tips */}
      <div style={{ ...s.row, ...(isMobile ? s.rowMobile : {}) }}>
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
                  ? `При текущих тратах ${forecast.daily_avg?.toLocaleString("ru-RU")} с/день`
                  : "Твои расходы под контролем"}
              </div>
              <div style={s.lessonMeta}>
                <span>📊 Средний расход: {forecast.daily_avg?.toLocaleString("ru-RU")} с</span>
              </div>
            </>
          ) : (
            <div style={s.allDone}><img src="/icons/free-icon-target-6745066.png" alt="" style={{ width: 40, height: 40 }} /><div>Добавь транзакции для прогноза</div></div>
          )}
        </Motion.div>

        <Motion.div
          variants={item}
          style={{
            ...s.card,
            background: "linear-gradient(135deg, #fffef5 0%, #ffffff 100%)",
            border: "1px solid rgba(255,221,45,0.15)",
          }}
          whileHover={{ y: -2, boxShadow: "0 8px 28px rgba(255,221,45,0.12)" }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{
                width: 40, height: 40, borderRadius: 12,
                background: "linear-gradient(135deg, #ffdd2d, #ffa000)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 20, boxShadow: "0 4px 12px rgba(255,221,45,0.3)",
              }}>🤖</div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: "#1a1a1a" }}>AI-Советник</div>
                <div style={{ fontSize: 11, color: "rgba(0,0,0,0.35)" }}>Персональные рекомендации</div>
              </div>
            </div>
            <Motion.div
              style={{
                width: 8, height: 8, borderRadius: "50%",
                background: ai_tips?.length ? "#21a038" : "rgba(0,0,0,0.15)",
              }}
              animate={ai_tips?.length ? { scale: [1, 1.3, 1], opacity: [1, 0.7, 1] } : {}}
              transition={{ duration: 2, repeat: Infinity }}
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {ai_tips?.slice(0, 3).map((tip, i) => {
              const tipText = typeof tip === 'string' ? tip : tip.text || tip
              const isWarning = tipText.includes("🚨") || tipText.includes("⚠️")
              const isGood = tipText.includes("✅") || tipText.includes("💰")
              return (
                <Motion.div
                  key={i}
                  style={{
                    display: "flex", alignItems: "flex-start", gap: 10,
                    background: isWarning
                      ? "linear-gradient(135deg, rgba(244,67,54,0.06), rgba(244,67,54,0.02))"
                      : isGood
                        ? "linear-gradient(135deg, rgba(33,160,56,0.06), rgba(33,160,56,0.02))"
                        : "linear-gradient(135deg, rgba(255,221,45,0.08), rgba(255,221,45,0.02))",
                    border: isWarning
                      ? "1px solid rgba(244,67,54,0.12)"
                      : isGood
                        ? "1px solid rgba(33,160,56,0.12)"
                        : "1px solid rgba(255,221,45,0.15)",
                    borderRadius: 12,
                    padding: "12px 14px",
                  }}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.15 + i * 0.07, duration: 0.3 }}
                >
                  <span style={{
                    fontSize: 18, flexShrink: 0, marginTop: 1,
                    filter: "drop-shadow(0 1px 2px rgba(0,0,0,0.1))",
                  }}>
                    {isWarning ? "⚠️" : isGood ? "✅" : "💡"}
                  </span>
                  <span style={{ flex: 1, fontSize: 13, color: "#1a1a1a", lineHeight: 1.5, fontWeight: 500 }}>
                    {tipText}
                  </span>
                </Motion.div>
              )
            })}
          </div>
          {!ai_tips?.length && (
            <div style={{
              textAlign: "center", padding: "24px 20px", color: "rgba(0,0,0,0.3)", fontSize: 13,
              display: "flex", flexDirection: "column", alignItems: "center", gap: 10,
            }}>
              <div style={{
                width: 56, height: 56, borderRadius: 16,
                background: "linear-gradient(135deg, rgba(255,221,45,0.15), rgba(255,160,0,0.1))",
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: 28,
              }}>🤖</div>
              <div>Добавь транзакции для персональных советов</div>
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
                <span style={{ fontSize: 20 }}>{t.category_icon || "💰"}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600 }}>{t.category}</div>
                  <div style={{ fontSize: 12, color: "rgba(0,0,0,0.4)" }}>{t.comment || t.date}</div>
                </div>
                <span style={{ color: t.type === "income" ? "#21a038" : "#f44336", fontWeight: 700 }}>
                  {t.type === "income" ? "+" : "-"}{t.amount?.toLocaleString("ru-RU")} с
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

      {/* Spending by Category with Chart */}
      <Motion.div variants={item} style={s.card}>
        <div style={s.cardLabel}>РАСХОДЫ ПО КАТЕГОРИЯМ</div>

        {/* Pie Chart */}
        {spending_chart?.length > 0 && (
          <div style={{ display: "flex", gap: 24, marginBottom: 20 }}>
            <div style={{ position: "relative", width: 140, height: 140, flexShrink: 0 }}>
              <svg width="140" height="140" viewBox="0 0 140 140" style={{ transform: "rotate(-90deg)" }}>
                {(() => {
                  let currentAngle = 0
                  const total = spending_chart.reduce((sum, cat) => sum + (cat.amount || 0), 0)
                  const colors = ["#ffdd2d", "#ffa000", "#ff8f00", "#ff6f00", "#ff5722", "#e64a19"]
                  return spending_chart.map((cat, i) => {
                    const percent = (cat.amount / total) * 100
                    const angle = (percent / 100) * 360
                    const startAngle = currentAngle
                    currentAngle += angle

                    const radius = 60
                    const centerX = 70
                    const centerY = 70

                    const startRad = (startAngle * Math.PI) / 180
                    const endRad = (currentAngle * Math.PI) / 180

                    const x1 = centerX + radius * Math.cos(startRad)
                    const y1 = centerY + radius * Math.sin(startRad)
                    const x2 = centerX + radius * Math.cos(endRad)
                    const y2 = centerY + radius * Math.sin(endRad)

                    const largeArc = angle > 180 ? 1 : 0

                    return (
                      <Motion.path
                        key={i}
                        d={`M ${centerX} ${centerY} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`}
                        fill={colors[i % colors.length]}
                        initial={{ opacity: 0, scale: 0 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.5, delay: 0.1 + i * 0.1 }}
                      />
                    )
                  })
                })()}
                <circle cx="70" cy="70" r="35" fill="#ffffff" />
              </svg>
              <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", textAlign: "center" }}>
                <div style={{ fontSize: 11, color: "rgba(0,0,0,0.4)", marginBottom: 2 }}>Всего</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: "#1a1a1a" }}>
                  {spending_chart.reduce((sum, cat) => sum + (cat.amount || 0), 0).toLocaleString("ru-RU")} с
                </div>
              </div>
            </div>

            {/* Legend */}
            <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8, justifyContent: "center" }}>
              {spending_chart.slice(0, 6).map((cat, i) => {
                const colors = ["#ffdd2d", "#ffa000", "#ff8f00", "#ff6f00", "#ff5722", "#e64a19"]
                const total = spending_chart.reduce((sum, c) => sum + (c.amount || 0), 0)
                const percent = ((cat.amount / total) * 100).toFixed(1)
                return (
                  <Motion.div
                    key={i}
                    style={{ display: "flex", alignItems: "center", gap: 8 }}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 + i * 0.05 }}
                  >
                    <div style={{ width: 12, height: 12, borderRadius: 2, background: colors[i % colors.length], flexShrink: 0 }} />
                    <span style={{ fontSize: 11, color: "rgba(0,0,0,0.6)", flex: 1 }}>{cat.icon} {cat.category}</span>
                    <span style={{ fontSize: 11, fontWeight: 600, color: "#1a1a1a" }}>{percent}%</span>
                  </Motion.div>
                )
              })}
            </div>
          </div>
        )}

        {/* Bar Chart */}
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
                {cat.amount?.toLocaleString("ru-RU")} с
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
      <Motion.div style={{ ...s.statsRow, ...(isMobile ? s.statsRowMobile : {}) }} variants={container}>
        {[
          { icon: "/icons/free-icon-money-bag-7510557.png", num: stats?.transactions_count || 0, label: "транзакций" },
          { icon: "/icons/free-icon-investment-5531695.png", num: `${(stats?.savings_rate || 0)}%`, label: "сбережений" },
          { icon: "/icons/free-icon-target-6745066.png", num: stats?.categories_used || 0, label: "категорий" },
          { icon: "/icons/free-icon-trophy-1152912.png", num: stats?.achievements || 0, label: "достижений" },
        ].map((st, i) => (
          <Motion.div
            key={i}
            style={{ ...s.statCard, ...(isMobile ? s.statCardMobile : {}) }}
            variants={statItem}
            whileHover={{ y: -4, scale: 1.03, boxShadow: "0 10px 28px rgba(0,0,0,0.1)" }}
            transition={{ type: "spring", stiffness: 350, damping: 18 }}
          >
            <div style={{ marginBottom: 4 }}>
              <img src={st.icon} alt="" style={{ width: 32, height: 32, objectFit: "contain" }} />
            </div>
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
  pageMobile: { maxWidth: "100%" },
  loading: { color: "rgba(0,0,0,0.45)", padding: 40, textAlign: "center", fontSize: 16 },
  portfolioCard: {
    background: "#ffffff",
    borderRadius: 16, padding: "24px 28px", marginBottom: 20,
    cursor: "pointer", border: "1px solid rgba(0,0,0,0.08)",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  cardMobile: {
    padding: "18px 16px",
    borderRadius: 14,
    marginBottom: 14,
  },
  portfolioHeader: { display: "flex", justifyContent: "space-between", alignItems: "center" },
  portfolioHeaderMobile: { alignItems: "flex-start", gap: 12 },
  portfolioLabel: { fontSize: 11, color: "rgba(0,0,0,0.4)", letterSpacing: 2, marginBottom: 8, fontWeight: 600 },
  portfolioValue: { fontSize: 32, fontWeight: 800, color: "#1a1a1a", marginBottom: 4 },
  portfolioValueMobile: { fontSize: 28 },
  portfolioPnl: { fontSize: 15, fontWeight: 600 },
  chartCard: {
    background: "#ffffff", borderRadius: 16, padding: "24px 28px", marginBottom: 20,
    border: "1px solid rgba(0,0,0,0.08)",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  row: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 },
  rowMobile: { gridTemplateColumns: "1fr", gap: 14 },
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
  statsRowMobile: { gridTemplateColumns: "repeat(2, 1fr)", gap: 10 },
  statCard: {
    background: "#ffffff", borderRadius: 12, padding: "16px 12px",
    textAlign: "center", border: "1px solid rgba(0,0,0,0.08)",
    boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
  },
  statCardMobile: { padding: "14px 10px" },
}
