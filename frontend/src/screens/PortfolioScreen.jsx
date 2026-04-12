import { useState, useEffect, useRef } from "react"
import { motion as Motion } from "framer-motion"
import { getDashboard, addTransaction, getTransactions, deleteTransaction } from "../api"
import { getSettings } from "../settings"

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.05 } },
}
const item = {
  hidden: { opacity: 0, y: 20 },
  show:   { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.25, 0.1, 0.25, 1] } },
}

function formatAmountInput(value) {
  const normalized = String(value || "")
    .replace(/[^\d.,\s]/g, "")
    .replace(/\s+/g, "")
    .replace(",", ".")

  if (!normalized) return ""

  const parts = normalized.split(".")
  const integerPart = (parts[0] || "").replace(/^0+(?=\d)/, "")
  const groupedInteger = (integerPart || "0").replace(/\B(?=(\d{3})+(?!\d))/g, " ")
  const fractionalPart = parts.slice(1).join("").slice(0, 2)

  return fractionalPart ? `${groupedInteger}.${fractionalPart}` : groupedInteger
}

function AnimatedNumber({ value, suffix = "", masked = false }) {
  const [display, setDisplay] = useState(0)
  const ref = useRef(null)
  useEffect(() => {
    if (masked) return
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
  }, [value, masked])
  if (masked) return <>•••••</>
  return <>{display.toLocaleString("ru-RU")}{suffix}</>
}

export default function TransactionsScreen({ onRefresh }) {
  const [balance, setBalance] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [view, setView] = useState("all") // all | income | expense
  const [showAddModal, setShowAddModal] = useState(false)
  const [newTransaction, setNewTransaction] = useState({
    amount: "",
    category: "",
    type: "expense",
    comment: "",
    date: new Date().toISOString().split("T")[0]
  })
  const [message, setMessage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [settings, setSettings] = useState(getSettings)

  useEffect(() => {
    const handler = () => setSettings(getSettings())
    window.addEventListener("finfuture-settings", handler)
    return () => window.removeEventListener("finfuture-settings", handler)
  }, [])

  const hide = settings.hideBalance
  const mask = (val) => hide ? "•••••" : val

  const refresh = () => {
    setLoading(true); setError(null)
    Promise.all([getDashboard(), getTransactions()])
      .then(([dashData, t]) => {
        // Extract balance from dashboard data
        const balanceData = {
          current: dashData?.balance?.current || 0,
          income_month: dashData?.income?.month || 0,
          expenses_month: dashData?.expenses?.month || 0
        }
        setBalance(balanceData)
        setTransactions(t)
        setLoading(false)
      })
      .catch(e => { setError(e.message||"Ошибка"); setLoading(false) })
  }

  useEffect(() => { refresh() }, [])

  const handleAddTransaction = () => {
    if (!newTransaction.amount || !newTransaction.category) {
      setMessage({ type: "error", text: "Заполни все поля" })
      return
    }
    addTransaction(newTransaction)
      .then(() => {
        setMessage({ type: "success", text: "Транзакция добавлена" })
        setShowAddModal(false)
        setNewTransaction({ amount: "", category: "", type: "expense", comment: "", date: new Date().toISOString().split("T")[0] })
        refresh()
        onRefresh?.()
      })
      .catch(e => setMessage({ type: "error", text: e.message || "Ошибка" }))
  }

  if (loading) return <div style={s.loading}>Загрузка...</div>
  if (error || !balance) return <div style={s.loading}><div style={{fontSize:48,marginBottom:16}}>⚠️</div><div style={{marginBottom:16}}>{error||"Ошибка"}</div><button onClick={refresh} style={{padding:"10px 24px",borderRadius:10,border:"1px solid rgba(0,0,0,0.1)",background:"transparent",color:"#ffdd2d",cursor:"pointer",fontFamily:"inherit"}}>Повторить</button></div>

  const filteredTransactions = view === "all" ? transactions : transactions.filter(t => t.type === view)

  return (
    <Motion.div style={s.page} variants={container} initial="hidden" animate="show">
      {/* Header */}
      <Motion.div variants={item} style={s.header}>
        <div>
          <div style={s.headerLabel}>ТЕКУЩИЙ БАЛАНС</div>
          <div style={s.headerValue}>
            <AnimatedNumber value={balance.current} suffix=" с" masked={hide} />
          </div>
          <div style={s.headerPnl}>
            <span style={{ color: "#21a038" }}>↑ {mask((balance.income_month || 0).toLocaleString("ru-RU"))} с</span>
            {" "}
            <span style={{ color: "#f44336" }}>↓ {mask((balance.expenses_month || 0).toLocaleString("ru-RU"))} с</span>
          </div>
        </div>
        <Motion.button
          style={s.addBtn}
          onClick={() => setShowAddModal(true)}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          + Добавить
        </Motion.button>
      </Motion.div>

      {/* Message */}
      {message && (
        <div style={{
          ...s.tradeMsg,
          background: message.type === "success" ? "rgba(33,160,56,0.15)" : "rgba(244,67,54,0.15)",
          color: message.type === "success" ? "#21a038" : "#f44336",
        }}>
          {message.text}
          <button onClick={() => setMessage(null)} style={s.closeMsgBtn}>✕</button>
        </div>
      )}

      {/* Tabs */}
      <Motion.div variants={item} style={s.tabs}>
        {[
          { id: "all", label: "Все" },
          { id: "income", label: "Доходы" },
          { id: "expense", label: "Расходы" },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setView(t.id)}
            style={{ ...s.tab, ...(view === t.id ? s.tabActive : {}) }}
          >{t.label}</button>
        ))}
      </Motion.div>

      {/* Transactions List */}
      <Motion.div variants={item} style={s.historyList}>
        {filteredTransactions.length > 0 ? filteredTransactions.map((t, i) => (
          <div key={i} style={s.historyRow}>
            <div style={{ fontSize: 24 }}>{t.category_icon || (t.type === "income" ? "💰" : "💸")}</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#1a1a1a" }}>
                {t.category}
              </div>
              <div style={{ fontSize: 12, color: "rgba(0,0,0,0.4)" }}>
                {t.comment || new Date(t.date).toLocaleDateString("ru-RU")}
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{
                fontSize: 15, fontWeight: 700,
                color: t.type === "income" ? "#21a038" : "#f44336",
              }}>
                {t.type === "income" ? "+" : "-"}{mask(t.amount?.toLocaleString("ru-RU"))} с
              </div>
              <div style={{ fontSize: 11, color: "rgba(0,0,0,0.3)" }}>
                {new Date(t.date).toLocaleDateString("ru-RU")}
              </div>
            </div>
          </div>
        )) : (
          <div style={s.emptyState}>
            <div style={{ marginBottom: 12 }}><img src="/icons/free-icon-mailbox-725683.png" alt="" style={{width:48,height:48}} /></div>
            <div>Нет транзакций</div>
          </div>
        )}
      </Motion.div>
      {/* Add Transaction Modal */}
      {showAddModal && (
        <div style={s.modalOverlay} onClick={() => setShowAddModal(false)}>
          <div style={s.modal} onClick={e => e.stopPropagation()}>
            <div style={s.modalHeader}>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#1a1a1a" }}>Новая транзакция</div>
              <button onClick={() => setShowAddModal(false)} style={s.modalClose}>✕</button>
            </div>

            {/* Type Toggle */}
            <div style={s.tradeToggle}>
              <button
                style={{ ...s.tradeToggleBtn, ...(newTransaction.type === "income" ? s.tradeToggleBuy : {}) }}
                onClick={() => setNewTransaction({ ...newTransaction, type: "income" })}
              >Доход</button>
              <button
                style={{ ...s.tradeToggleBtn, ...(newTransaction.type === "expense" ? s.tradeToggleSell : {}) }}
                onClick={() => setNewTransaction({ ...newTransaction, type: "expense" })}
              >Расход</button>
            </div>

            {/* Amount */}
            <div style={s.formGroup}>
              <label style={s.formLabel}>Сумма</label>
              <input
                type="text"
                inputMode="decimal"
                value={newTransaction.amount}
                onChange={e => setNewTransaction({ ...newTransaction, amount: formatAmountInput(e.target.value) })}
                placeholder="1 000"
                style={s.formInput}
              />
            </div>

            {/* Category */}
            <div style={s.formGroup}>
              <label style={s.formLabel}>Категория</label>
              <div style={{
                display: "grid",
                gridTemplateColumns: "repeat(4, 1fr)",
                gap: 8,
              }}>
                {(newTransaction.type === "expense"
                  ? [
                    { value: "Еда", icon: "🍔", color: "#ff9800" },
                    { value: "Транспорт", icon: "🚗", color: "#2196f3" },
                    { value: "Развлечения", icon: "🎮", color: "#9c27b0" },
                    { value: "Покупки", icon: "🛍️", color: "#e91e63" },
                    { value: "Здоровье", icon: "💊", color: "#4caf50" },
                    { value: "Образование", icon: "📚", color: "#ff5722" },
                    { value: "Другое", icon: "💸", color: "#607d8b" },
                  ]
                  : [
                    { value: "Зарплата", icon: "💰", color: "#4caf50" },
                    { value: "Фриланс", icon: "💼", color: "#2196f3" },
                    { value: "Инвестиции", icon: "📈", color: "#ff9800" },
                    { value: "Подарок", icon: "🎁", color: "#e91e63" },
                    { value: "Другое", icon: "💵", color: "#607d8b" },
                  ]
                ).map(cat => {
                  const isActive = newTransaction.category === cat.value
                  return (
                    <button
                      key={cat.value}
                      type="button"
                      onClick={() => setNewTransaction({ ...newTransaction, category: cat.value })}
                      style={{
                        display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
                        padding: "12px 4px", borderRadius: 12, border: "1.5px solid",
                        borderColor: isActive ? cat.color : "rgba(0,0,0,0.06)",
                        background: isActive
                          ? `${cat.color}12`
                          : "#fafafa",
                        cursor: "pointer", fontFamily: "inherit",
                        transition: "all 0.2s ease",
                        transform: isActive ? "scale(1.04)" : "scale(1)",
                        boxShadow: isActive ? `0 3px 12px ${cat.color}20` : "none",
                      }}
                    >
                      <span style={{ fontSize: 22 }}>{cat.icon}</span>
                      <span style={{
                        fontSize: 11, fontWeight: isActive ? 700 : 500,
                        color: isActive ? cat.color : "rgba(0,0,0,0.55)",
                        lineHeight: 1.2, textAlign: "center",
                      }}>{cat.value}</span>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Date */}
            <div style={s.formGroup}>
              <label style={s.formLabel}>Дата</label>
              <input
                type="date"
                value={newTransaction.date}
                onChange={e => setNewTransaction({ ...newTransaction, date: e.target.value })}
                style={s.formInput}
              />
            </div>

            {/* Comment */}
            <div style={s.formGroup}>
              <label style={s.formLabel}>Комментарий (необязательно)</label>
              <input
                type="text"
                value={newTransaction.comment}
                onChange={e => setNewTransaction({ ...newTransaction, comment: e.target.value })}
                placeholder="Описание транзакции"
                style={s.formInput}
              />
            </div>

            <button style={{
              ...s.tradeBtn,
              background: newTransaction.type === "income" ? "#ffa000" : "#ff8f00",
            }} onClick={handleAddTransaction}>
              Добавить транзакцию
            </button>
          </div>
        </div>
      )}
    </Motion.div>
  )
}

const s = {
  page: { maxWidth: 900, margin: "0 auto" },
  loading: { color: "rgba(0,0,0,0.45)", padding: 40, textAlign: "center" },
  header: {
    display: "flex", justifyContent: "space-between", alignItems: "flex-start",
    marginBottom: 16,
  },
  headerLabel: { fontSize: 11, color: "rgba(0,0,0,0.4)", letterSpacing: 2, marginBottom: 6 },
  headerValue: { fontSize: 36, fontWeight: 800, color: "#1a1a1a", marginBottom: 4 },
  headerPnl: { fontSize: 16, fontWeight: 600 },
  addBtn: {
    padding: "12px 24px", borderRadius: 10, border: "none",
    background: "#ffdd2d", color: "#1a1a1a", fontSize: 14, fontWeight: 700,
    cursor: "pointer", fontFamily: "inherit",
  },
  tabs: { display: "flex", gap: 4, marginBottom: 16 },
  tab: {
    padding: "8px 20px", border: "1px solid rgba(0,0,0,0.06)",
    borderRadius: 8, background: "transparent", color: "rgba(0,0,0,0.45)",
    fontSize: 13, cursor: "pointer", fontFamily: "inherit", fontWeight: 500,
  },
  tabActive: { background: "rgba(255,221,45,0.1)", color: "#ffdd2d", borderColor: "rgba(255,221,45,0.2)" },
  tradeMsg: {
    padding: "12px 16px", borderRadius: 10, marginBottom: 16,
    fontSize: 13, fontWeight: 600, display: "flex", alignItems: "center", justifyContent: "space-between",
    position: "relative", zIndex: 1000,
  },
  closeMsgBtn: {
    background: "transparent", border: "none", color: "inherit",
    fontSize: 16, cursor: "pointer", padding: "0 4px",
  },
  historyList: { display: "flex", flexDirection: "column", gap: 2 },
  historyRow: {
    display: "flex", alignItems: "center", gap: 12,
    padding: "12px 16px", borderRadius: 12,
    background: "#ffffff",
    border: "1px solid rgba(0,0,0,0.04)",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  emptyState: {
    textAlign: "center", padding: "40px 20px",
    display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
    color: "rgba(0,0,0,0.4)", fontSize: 14,
  },
  // Modal
  modalOverlay: {
    position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)",
    display: "flex", alignItems: "center", justifyContent: "center", zIndex: 200,
  },
  modal: {
    background: "#ffffff", borderRadius: 20, padding: "28px 24px",
    width: 400, maxWidth: "90vw", border: "1px solid rgba(0,0,0,0.06)",
    boxShadow: "0 4px 24px rgba(0,0,0,0.12)",
  },
  modalHeader: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 },
  modalClose: {
    background: "transparent", border: "none",
    color: "rgba(0,0,0,0.4)", fontSize: 20, cursor: "pointer",
  },
  tradeToggle: { display: "flex", gap: 4, marginBottom: 16 },
  tradeToggleBtn: {
    flex: 1, padding: "10px 0", border: "1px solid rgba(0,0,0,0.06)",
    borderRadius: 8, background: "transparent", color: "rgba(0,0,0,0.45)",
    fontSize: 14, fontWeight: 600, cursor: "pointer", fontFamily: "inherit",
  },
  tradeToggleBuy: { background: "rgba(255,221,45,0.15)", color: "#ffdd2d", borderColor: "rgba(255,221,45,0.3)" },
  tradeToggleSell: { background: "rgba(255,221,45,0.15)", color: "#ffdd2d", borderColor: "rgba(255,221,45,0.3)" },
  formGroup: { marginBottom: 16 },
  formLabel: { display: "block", fontSize: 13, fontWeight: 600, color: "#1a1a1a", marginBottom: 6 },
  formInput: {
    width: "100%", padding: "10px 12px", borderRadius: 8,
    border: "1px solid rgba(0,0,0,0.12)", fontSize: 14,
    fontFamily: "inherit", outline: "none",
  },
  tradeBtn: {
    width: "100%", padding: "14px 0", border: "none", borderRadius: 12,
    color: "#fff", fontSize: 15, fontWeight: 700, cursor: "pointer", fontFamily: "inherit",
  },
}
