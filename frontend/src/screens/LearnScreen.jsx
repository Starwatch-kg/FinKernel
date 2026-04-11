import { useState, useEffect, useContext } from "react"
import { motion as Motion, AnimatePresence } from "framer-motion"
import { getModuleLessons } from "../api"
import { DevContext } from "../DevContext"

const API_BASE = import.meta.env.VITE_API_URL || "/api"
const USER_ID = () => localStorage.getItem("finfuture_email") || "demo-user-1"
const TOKEN = () => localStorage.getItem("finfuture_token") || ""

const fetchAIAdvice = () =>
  fetch(`${API_BASE}/v2/ai-advice?userId=${USER_ID()}`, {
    headers: TOKEN() ? { Authorization: `Bearer ${TOKEN()}` } : {},
  }).then(r => r.json()).catch(() => null)

export default function AIAdvisorScreen({ onStartLesson }) {
  const { setAiStatus } = useContext(DevContext)
  const [messages, setMessages] = useState([])
  const [inputText, setInputText] = useState("")
  const [aiAdvice, setAiAdvice] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [sending, setSending] = useState(false)

  const loadAll = () => {
    setLoading(true)
    setError(null)
    setAiStatus("Загрузка советов...")
    fetchAIAdvice()
      .then(data => {
        if (data) {
          setAiAdvice(data)
          if (data.tips?.length > 0) {
            setMessages([
              { role: "assistant", text: "Привет! Я твой финансовый AI-советник. Могу помочь с анализом трат, советами по экономии и планированию бюджета. Задай мне вопрос!" }
            ])
          }
        }
        setLoading(false)
        setAiStatus("✓ Советы загружены")
      })
      .catch(() => {
        setError("Ошибка загрузки")
        setLoading(false)
        setAiStatus("✗ Ошибка")
      })
  }

  useEffect(() => { loadAll() }, [])

  const handleSendMessage = () => {
    if (!inputText.trim() || sending) return
    const userMsg = inputText.trim()
    setMessages(prev => [...prev, { role: "user", text: userMsg }])
    setInputText("")
    setSending(true)

    // Simulate AI response
    setTimeout(() => {
      const responses = [
        "Отличный вопрос! Рекомендую сократить расходы на развлечения на 20% и направить эти деньги в накопления.",
        "Судя по твоим тратам, ты тратишь много на еду вне дома. Попробуй готовить дома чаще — сэкономишь до 30%.",
        "Твой баланс стабилен! Продолжай в том же духе и не забывай откладывать 10-15% от дохода.",
        "Заметил, что в этом месяце расходы выросли. Проверь категорию 'Покупки' — там можно оптимизировать.",
      ]
      const aiResponse = responses[Math.floor(Math.random() * responses.length)]
      setMessages(prev => [...prev, { role: "assistant", text: aiResponse }])
      setSending(false)
    }, 1000)
  }

  if (loading) return <div style={s.loading}>Загрузка...</div>
  if (error) return (
    <div style={s.loading}>
      <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
      <div style={{ marginBottom: 16 }}>{error}</div>
      <button onClick={loadAll} style={s.retryBtn}>Повторить</button>
    </div>
  )

  return (
    <div style={s.layout}>
      {/* Chat Area */}
      <div style={s.page}>
        <Motion.div
          style={s.header}
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <div style={s.pageTitle}>AI-Советник</div>
          <div style={s.subtitle}>Твой персональный финансовый помощник</div>
        </Motion.div>

        {/* Chat Messages */}
        <div style={s.chatContainer}>
          {messages.map((msg, i) => (
            <Motion.div
              key={i}
              style={{
                ...s.messageRow,
                justifyContent: msg.role === "user" ? "flex-end" : "flex-start"
              }}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: i * 0.05 }}
            >
              {msg.role === "assistant" && (
                <div style={s.aiAvatar}>🤖</div>
              )}
              <div style={{
                ...s.messageBubble,
                ...(msg.role === "user" ? s.userBubble : s.aiBubble)
              }}>
                {msg.text}
              </div>
              {msg.role === "user" && (
                <div style={s.userAvatar}>👤</div>
              )}
            </Motion.div>
          ))}
          {sending && (
            <Motion.div
              style={{ ...s.messageRow, justifyContent: "flex-start" }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <div style={s.aiAvatar}>🤖</div>
              <div style={{ ...s.messageBubble, ...s.aiBubble }}>
                <Motion.span
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                >
                  Печатаю...
                </Motion.span>
              </div>
            </Motion.div>
          )}
        </div>

        {/* Input */}
        <div style={s.inputContainer}>
          <input
            type="text"
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            onKeyPress={e => e.key === "Enter" && handleSendMessage()}
            placeholder="Задай вопрос о финансах..."
            style={s.input}
            disabled={sending}
          />
          <Motion.button
            style={s.sendBtn}
            onClick={handleSendMessage}
            disabled={!inputText.trim() || sending}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            ➤
          </Motion.button>
        </div>
      </div>

      {/* Tips Panel */}
      <Motion.div
        style={s.planPanel}
        initial={{ opacity: 0, x: 32 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.45, ease: [0.25, 0.1, 0.25, 1], delay: 0.15 }}
      >
        <div style={s.planHeader}>
          <img src="/icons/free-icon-robot-14224105.png" alt="AI" style={{ width: 22, height: 22 }} />
          <span style={s.planTitle}>Умные советы</span>
        </div>

        {aiAdvice?.tips?.length > 0 ? (
          <div style={s.tipsList}>
            {aiAdvice.tips.map((tip, i) => (
              <Motion.div
                key={i}
                style={s.tipCard}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 * i, duration: 0.3 }}
              >
                <div style={s.tipIcon}>{tip.icon || "💡"}</div>
                <div style={s.tipText}>{tip.text}</div>
              </Motion.div>
            ))}
          </div>
        ) : (
          <div style={{ textAlign: "center", padding: "20px 0", color: "rgba(0,0,0,0.4)", fontSize: 13 }}>
            Добавь транзакции, чтобы получить персональные советы
          </div>
        )}
      </Motion.div>
    </div>
  )
}

const s = {
  layout: { display: "flex", gap: 40, maxWidth: 1100, margin: "0 auto" },
  page: { flex: 1, maxWidth: 600, margin: "0 auto", paddingBottom: 60 },
  loading: { color: "rgba(0,0,0,0.45)", padding: 60, textAlign: "center", fontSize: 16 },
  retryBtn: {
    padding: "10px 24px", borderRadius: 10, border: "1px solid rgba(0,0,0,0.1)",
    background: "transparent", color: "#ffdd2d", cursor: "pointer", fontFamily: "inherit",
  },
  header: { textAlign: "center", marginBottom: 40 },
  pageTitle: { fontSize: 28, fontWeight: 800, color: "#1a1a1a", marginBottom: 4 },
  subtitle: { fontSize: 14, color: "rgba(0,0,0,0.4)", marginBottom: 8 },
  chatContainer: {
    background: "#fff", borderRadius: 16, padding: "20px",
    border: "1px solid rgba(0,0,0,0.08)", marginBottom: 16,
    minHeight: 400, maxHeight: 500, overflowY: "auto",
    display: "flex", flexDirection: "column", gap: 12,
  },
  messageRow: { display: "flex", alignItems: "flex-end", gap: 8 },
  aiAvatar: {
    width: 32, height: 32, borderRadius: "50%", background: "#f0f0f0",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 18, flexShrink: 0,
  },
  userAvatar: {
    width: 32, height: 32, borderRadius: "50%", background: "#ffdd2d",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 18, flexShrink: 0,
  },
  messageBubble: {
    padding: "10px 14px", borderRadius: 12, maxWidth: "70%",
    fontSize: 14, lineHeight: 1.5,
  },
  aiBubble: {
    background: "#f6f7f8", color: "#1a1a1a",
  },
  userBubble: {
    background: "#ffdd2d", color: "#1a1a1a",
  },
  inputContainer: { display: "flex", gap: 8 },
  input: {
    flex: 1, padding: "12px 16px", borderRadius: 12,
    border: "1px solid rgba(0,0,0,0.12)", fontSize: 14,
    fontFamily: "inherit", outline: "none",
  },
  sendBtn: {
    width: 48, height: 48, borderRadius: 12, border: "none",
    background: "#ffdd2d", color: "#1a1a1a", fontSize: 20,
    cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
  },
  planPanel: {
    width: 280, flexShrink: 0, background: "#fff", borderRadius: 16,
    border: "1px solid rgba(0,0,0,0.08)", padding: "20px 16px",
    alignSelf: "flex-start", position: "sticky", top: 24,
  },
  planHeader: { display: "flex", alignItems: "center", gap: 8, marginBottom: 12 },
  planTitle: { fontSize: 16, fontWeight: 700, color: "#1a1a1a" },
  tipsList: { display: "flex", flexDirection: "column", gap: 10 },
  tipCard: {
    padding: "12px", background: "rgba(255,221,45,0.08)", borderRadius: 10,
    border: "1px solid rgba(255,221,45,0.15)", display: "flex", gap: 10,
  },
  tipIcon: { fontSize: 20, flexShrink: 0 },
  tipText: { fontSize: 13, color: "#1a1a1a", lineHeight: 1.5 },
}
