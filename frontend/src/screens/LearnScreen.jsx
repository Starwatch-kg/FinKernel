import { useState, useEffect, useRef, useContext, useCallback } from "react"
import { motion as Motion, AnimatePresence } from "framer-motion"
import { DevContext } from "../DevContext"

const API_BASE = import.meta.env.VITE_API_URL || "/api"
const TOKEN = () => localStorage.getItem("finfuture_token") || ""

const fetchAIAdvice = () =>
  fetch(`${API_BASE}/v2/ai-advice`, {
    headers: TOKEN() ? { Authorization: `Bearer ${TOKEN()}` } : {},
  }).then(r => r.json()).catch(() => null)

const sendChatMessage = (message) =>
  fetch(`${API_BASE}/ai-chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(TOKEN() ? { Authorization: `Bearer ${TOKEN()}` } : {}),
    },
    body: JSON.stringify({ message }),
  }).then(r => r.json())

const QUICK_ACTIONS = [
  { label: "Как сэкономить?", icon: "💰", msg: "Как мне сэкономить больше денег в этом месяце?" },
  { label: "Анализ трат", icon: "📊", msg: "Проанализируй мои расходы и дай конкретные советы" },
  { label: "Куда инвестировать?", icon: "📈", msg: "Куда лучше инвестировать небольшую сумму начинающему?" },
  { label: "План накоплений", icon: "🎯", msg: "Помоги составить реалистичный план накоплений" },
  { label: "Подушка безопасности", icon: "🛡", msg: "Как правильно создать финансовую подушку безопасности?" },
  { label: "Метод 50/30/20", icon: "⚖️", msg: "Объясни метод бюджетирования 50/30/20 и как его применить" },
]

const PROVIDER_LABELS = {
  groq: { label: "Groq", color: "#21a038", bg: "rgba(33,160,56,0.08)" },
  openrouter: { label: "OpenRouter", color: "#1565c0", bg: "rgba(21,101,192,0.08)" },
  fallback: { label: "Локальный анализ", color: "rgba(0,0,0,0.35)", bg: "rgba(0,0,0,0.04)" },
}

function ProviderBadge({ provider }) {
  if (!provider) return null
  const p = PROVIDER_LABELS[provider] || PROVIDER_LABELS.fallback
  return (
    <span style={{
      display: "inline-block",
      marginTop: 6,
      padding: "2px 8px",
      borderRadius: 6,
      fontSize: 10,
      fontWeight: 600,
      color: p.color,
      background: p.bg,
      letterSpacing: 0.3,
    }}>
      {p.label}
    </span>
  )
}

function TextWithNewlines({ text }) {
  return (
    <span style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
      {text}
    </span>
  )
}

export default function AIAdvisorScreen({ onStartLesson, isMobile = false }) {
  const { setAiStatus } = useContext(DevContext)
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Привет! 👋 Я твой финансовый AI-советник.\n\nМогу помочь с анализом трат, советуемой экономией и планированием бюджета. Задай вопрос или выбери тему ниже.",
    },
  ])
  const [inputText, setInputText] = useState("")
  const [aiAdvice, setAiAdvice] = useState(null)
  const [adviceLoading, setAdviceLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [showTips, setShowTips] = useState(true)
  const chatEndRef = useRef(null)
  const inputRef = useRef(null)

  const scrollToBottom = useCallback(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [])

  useEffect(() => { scrollToBottom() }, [messages, sending])

  useEffect(() => {
    setAdviceLoading(true)
    setAiStatus("Загрузка советов...")
    fetchAIAdvice()
      .then(data => {
        if (data) setAiAdvice(data)
        setAiStatus("✓ Советы загружены")
      })
      .catch(() => setAiStatus("✗ Ошибка загрузки"))
      .finally(() => setAdviceLoading(false))
  }, [])

  const handleSendMessage = async (overrideMsg) => {
    const userMsg = (overrideMsg || inputText).trim()
    if (!userMsg || sending) return

    setMessages(prev => [...prev, { role: "user", text: userMsg }])
    setInputText("")
    setSending(true)

    try {
      const data = await sendChatMessage(userMsg)
      const aiText = data?.response || "Извини, не удалось получить ответ. Попробуй ещё раз."
      setMessages(prev => [...prev, {
        role: "assistant",
        text: aiText,
        provider: data?.provider,
      }])
    } catch {
      setMessages(prev => [...prev, {
        role: "assistant",
        text: "Произошла ошибка. Проверь подключение и попробуй снова.",
        isError: true,
      }])
    }
    setSending(false)
    setTimeout(() => inputRef.current?.focus(), 100)
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const isFirstMessage = messages.length <= 1

  return (
    <div style={s.page}>
      {/* ── Page header ── */}
      <Motion.div
        style={s.pageHeader}
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <div style={s.pageHeaderLeft}>
          <div style={s.aiAvatar}>
            <span style={{ fontSize: 22 }}>🤖</span>
            <Motion.div
              style={s.onlineDot}
              animate={{ scale: [1, 1.4, 1], opacity: [1, 0.6, 1] }}
              transition={{ duration: 2.5, repeat: Infinity }}
            />
          </div>
          <div>
            <div style={s.pageTitle}>AI-Советник</div>
            <div style={s.pageSubtitle}>Персональный финансовый помощник</div>
          </div>
        </div>

        {/* Tips toggle */}
        <button
          style={{ ...s.tipsToggle, ...(showTips ? s.tipsToggleActive : {}) }}
          onClick={() => setShowTips(v => !v)}
          title={showTips ? "Скрыть советы" : "Показать советы"}
        >
          💡 Советы
        </button>
      </Motion.div>

      {/* ── Main layout ── */}
      <div style={{
        ...s.layout,
        ...(isMobile ? s.layoutMobile : {}),
        gridTemplateColumns: isMobile ? "1fr" : (showTips ? "1fr 280px" : "1fr")
      }}>

        {/* ── Chat column ── */}
        <Motion.div
          style={{ ...s.chatCard, ...(isMobile ? s.chatCardMobile : {}) }}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
        >
          {/* Messages area */}
          <div style={{ ...s.messagesArea, ...(isMobile ? s.messagesAreaMobile : {}) }}>
            <AnimatePresence initial={false}>
              {messages.map((msg, i) => (
                <Motion.div
                  key={i}
                  style={{
                    ...s.msgRow,
                    justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                  }}
                  initial={{ opacity: 0, y: 10, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ duration: 0.22, ease: "easeOut" }}
                >
                  {msg.role === "assistant" && (
                    <div style={s.msgAvatarAI}>🤖</div>
                  )}

                  <div style={{
                    ...s.bubble,
                    ...(msg.role === "user" ? s.bubbleUser : s.bubbleAI),
                    ...(msg.isError ? s.bubbleError : {}),
                  }}>
                    <TextWithNewlines text={msg.text} />
                    {msg.role === "assistant" && msg.provider && (
                      <ProviderBadge provider={msg.provider} />
                    )}
                  </div>

                  {msg.role === "user" && (
                    <div style={s.msgAvatarUser}>
                      {(localStorage.getItem("finfuture_name")?.[0] || "Я").toUpperCase()}
                    </div>
                  )}
                </Motion.div>
              ))}
            </AnimatePresence>

            {/* Typing indicator */}
            <AnimatePresence>
              {sending && (
                <Motion.div
                  style={{ ...s.msgRow, justifyContent: "flex-start" }}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 4 }}
                >
                  <div style={s.msgAvatarAI}>🤖</div>
                  <div style={{ ...s.bubble, ...s.bubbleAI, padding: "14px 18px" }}>
                    <div style={s.typingWrap}>
                      {[0, 1, 2].map(i => (
                        <Motion.span
                          key={i}
                          style={s.typingDot}
                          animate={{ y: [0, -5, 0], opacity: [0.4, 1, 0.4] }}
                          transition={{ duration: 0.7, repeat: Infinity, delay: i * 0.18 }}
                        />
                      ))}
                    </div>
                  </div>
                </Motion.div>
              )}
            </AnimatePresence>

            <div ref={chatEndRef} />
          </div>

          {/* Quick action chips — only on first message */}
          <AnimatePresence>
            {isFirstMessage && !sending && (
              <Motion.div
                style={s.quickGrid}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.25, delay: 0.2 }}
              >
                {QUICK_ACTIONS.map((qa, i) => (
                  <Motion.button
                    key={i}
                    style={s.quickChip}
                    onClick={() => handleSendMessage(qa.msg)}
                    whileHover={{ y: -2, boxShadow: "0 4px 14px rgba(255,221,45,0.2)", borderColor: "rgba(255,221,45,0.4)" }}
                    whileTap={{ scale: 0.96 }}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.25 + i * 0.05, duration: 0.2 }}
                  >
                    <span style={s.chipIcon}>{qa.icon}</span>
                    <span style={s.chipLabel}>{qa.label}</span>
                  </Motion.button>
                ))}
              </Motion.div>
            )}
          </AnimatePresence>

          {/* Input row */}
          <div style={s.inputRow}>
            <div style={s.inputWrap}>
              <input
                ref={inputRef}
                type="text"
                value={inputText}
                onChange={e => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Задай вопрос о финансах..."
                style={s.input}
                disabled={sending}
                maxLength={1000}
              />
              {inputText && (
                <button
                  style={s.clearBtn}
                  onClick={() => setInputText("")}
                  tabIndex={-1}
                  title="Очистить"
                >✕</button>
              )}
            </div>
            <Motion.button
              style={{
                ...s.sendBtn,
                opacity: (!inputText.trim() || sending) ? 0.45 : 1,
                cursor: (!inputText.trim() || sending) ? "not-allowed" : "pointer",
              }}
              onClick={() => handleSendMessage()}
              disabled={!inputText.trim() || sending}
              whileHover={inputText.trim() && !sending ? { scale: 1.06 } : {}}
              whileTap={inputText.trim() && !sending ? { scale: 0.93 } : {}}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </Motion.button>
          </div>
        </Motion.div>

        {/* ── Tips sidebar ── */}
        <AnimatePresence>
          {showTips && (
            <Motion.div
              style={s.tipsCol}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.3 }}
            >
              {/* AI Tips card */}
              <div style={s.tipsCard}>
                <div style={s.tipsHeader}>
                  <span style={{ fontSize: 16 }}>💡</span>
                  <span style={s.tipsTitle}>Умные советы</span>
                </div>

                {adviceLoading ? (
                  <div style={s.tipsLoading}>
                    {[80, 60, 70].map((w, i) => (
                      <div key={i} style={s.tipSkeleton}>
                        <div style={{ ...s.tipSkLine, width: 24, height: 24, borderRadius: "50%", flexShrink: 0 }} />
                        <div style={{ flex: 1 }}>
                          <div style={{ ...s.tipSkLine, width: `${w}%`, marginBottom: 4 }} />
                          <div style={{ ...s.tipSkLine, width: `${w - 15}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : aiAdvice?.tips?.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {aiAdvice.tips.map((tip, i) => {
                      const isWarn = tip.icon === "⚠️" || tip.icon === "🚨"
                      const isGood = tip.icon === "✅" || tip.icon === "💰"
                      return (
                        <Motion.div
                          key={i}
                          style={{
                            ...s.tipItem,
                            background: isWarn
                              ? "rgba(244,67,54,0.05)"
                              : isGood
                                ? "rgba(33,160,56,0.05)"
                                : "rgba(255,221,45,0.06)",
                            borderColor: isWarn
                              ? "rgba(244,67,54,0.12)"
                              : isGood
                                ? "rgba(33,160,56,0.12)"
                                : "rgba(255,221,45,0.15)",
                          }}
                          initial={{ opacity: 0, x: 8 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.08, duration: 0.25 }}
                          whileHover={{ y: -1, boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }}
                        >
                          <span style={s.tipItemIcon}>{tip.icon || "💡"}</span>
                          <span style={s.tipItemText}>{tip.text}</span>
                        </Motion.div>
                      )
                    })}
                  </div>
                ) : (
                  <div style={s.tipsEmpty}>
                    <div style={{ fontSize: 28, marginBottom: 6 }}>📝</div>
                    <div>Добавь транзакции для персональных советов</div>
                  </div>
                )}
              </div>

              {/* Hot topics */}
              <div style={s.topicsCard}>
                <div style={s.tipsHeader}>
                  <span style={{ fontSize: 16 }}>🔥</span>
                  <span style={s.tipsTitle}>Популярные темы</span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {[
                    "Как вести личный бюджет?",
                    "Подушка безопасности",
                    "Инвестиции для начинающих",
                    "Как погасить долги быстрее?",
                  ].map((topic, i) => (
                    <Motion.button
                      key={i}
                      style={s.topicBtn}
                      onClick={() => handleSendMessage(topic)}
                      whileHover={{ x: 3, background: "rgba(255,221,45,0.08)", borderColor: "rgba(255,221,45,0.25)" }}
                      whileTap={{ scale: 0.97 }}
                    >
                      <span style={{ color: "rgba(0,0,0,0.3)", fontSize: 12 }}>→</span>
                      <span>{topic}</span>
                    </Motion.button>
                  ))}
                </div>
              </div>

              {/* AI disclaimer */}
              <div style={s.disclaimer}>
                <span style={{ fontSize: 14 }}>ℹ️</span>
                <span>Советы носят информационный характер. Проконсультируйтесь со специалистом перед принятием финансовых решений.</span>
              </div>
            </Motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

// ─── Styles ─────────────────────────────────────────────────────────────────

const s = {
  page: {
    maxWidth: 1060,
    margin: "0 auto",
    display: "flex",
    flexDirection: "column",
    gap: 16,
    height: "calc(100vh - 60px)",
    paddingBottom: 8,
  },

  // Header
  pageHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    flexShrink: 0,
  },
  pageHeaderLeft: {
    display: "flex",
    alignItems: "center",
    gap: 14,
  },
  aiAvatar: {
    position: "relative",
    width: 48,
    height: 48,
    borderRadius: 14,
    background: "linear-gradient(135deg, #fff9d6, #fff3a3)",
    border: "1px solid rgba(255,221,45,0.2)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    boxShadow: "0 2px 8px rgba(255,221,45,0.15)",
  },
  onlineDot: {
    position: "absolute",
    bottom: 3,
    right: 3,
    width: 9,
    height: 9,
    borderRadius: "50%",
    background: "#21a038",
    border: "2px solid #fff",
  },
  pageTitle: {
    fontSize: 18,
    fontWeight: 700,
    color: "#1a1a1a",
    lineHeight: 1.2,
  },
  pageSubtitle: {
    fontSize: 12,
    color: "rgba(0,0,0,0.4)",
    marginTop: 2,
  },
  tipsToggle: {
    padding: "8px 16px",
    border: "1px solid rgba(0,0,0,0.08)",
    borderRadius: 10,
    background: "#fff",
    color: "rgba(0,0,0,0.5)",
    fontSize: 13,
    fontWeight: 500,
    cursor: "pointer",
    fontFamily: "inherit",
    transition: "all 0.2s",
  },
  tipsToggleActive: {
    background: "rgba(255,221,45,0.1)",
    borderColor: "rgba(255,221,45,0.3)",
    color: "#b8860b",
  },

  // Layout
  layout: {
    flex: 1,
    display: "grid",
    gap: 16,
    minHeight: 0,
    transition: "grid-template-columns 0.3s",
  },
  layoutMobile: {
    gap: 12,
  },

  // Chat card
  chatCard: {
    background: "#ffffff",
    borderRadius: 18,
    border: "1px solid rgba(0,0,0,0.06)",
    boxShadow: "0 2px 12px rgba(0,0,0,0.04)",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    minHeight: 0,
  },
  chatCardMobile: {
    minHeight: "60vh",
  },

  // Messages
  messagesArea: {
    flex: 1,
    overflowY: "auto",
    padding: "20px 24px",
    display: "flex",
    flexDirection: "column",
    gap: 14,
    scrollBehavior: "smooth",
  },
  messagesAreaMobile: {
    padding: "16px 14px",
    gap: 12,
  },
  msgRow: {
    display: "flex",
    alignItems: "flex-end",
    gap: 10,
  },
  msgAvatarAI: {
    width: 32,
    height: 32,
    borderRadius: 10,
    background: "rgba(255,221,45,0.12)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 16,
    flexShrink: 0,
    border: "1px solid rgba(255,221,45,0.15)",
  },
  msgAvatarUser: {
    width: 32,
    height: 32,
    borderRadius: 10,
    background: "linear-gradient(135deg, #ffdd2d, #ffc800)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 13,
    fontWeight: 700,
    color: "#1a1a1a",
    flexShrink: 0,
    boxShadow: "0 2px 8px rgba(255,221,45,0.3)",
  },
  bubble: {
    padding: "11px 15px",
    borderRadius: 16,
    maxWidth: "72%",
    fontSize: 14,
    lineHeight: 1.6,
    color: "#1a1a1a",
  },
  bubbleAI: {
    background: "#f6f7f8",
    borderBottomLeftRadius: 4,
    border: "1px solid rgba(0,0,0,0.04)",
  },
  bubbleUser: {
    background: "linear-gradient(135deg, #ffdd2d, #ffca00)",
    borderBottomRightRadius: 4,
    boxShadow: "0 2px 10px rgba(255,221,45,0.25)",
  },
  bubbleError: {
    background: "rgba(244,67,54,0.06)",
    border: "1px solid rgba(244,67,54,0.12)",
  },
  typingWrap: {
    display: "flex",
    gap: 5,
    alignItems: "center",
  },
  typingDot: {
    display: "inline-block",
    width: 7,
    height: 7,
    borderRadius: "50%",
    background: "rgba(0,0,0,0.2)",
  },

  // Quick chips
  quickGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: 8,
    padding: "0 20px 12px",
  },
  quickChip: {
    display: "flex",
    alignItems: "center",
    gap: 7,
    padding: "9px 13px",
    border: "1px solid rgba(0,0,0,0.07)",
    borderRadius: 12,
    background: "#fafafa",
    cursor: "pointer",
    fontFamily: "inherit",
    transition: "all 0.2s",
    textAlign: "left",
  },
  chipIcon: { fontSize: 16, flexShrink: 0 },
  chipLabel: {
    fontSize: 12,
    fontWeight: 500,
    color: "#1a1a1a",
    lineHeight: 1.3,
  },

  // Input
  inputRow: {
    display: "flex",
    gap: 10,
    padding: "14px 20px",
    borderTop: "1px solid rgba(0,0,0,0.05)",
    background: "#fcfcfc",
    flexShrink: 0,
  },
  inputWrap: {
    flex: 1,
    position: "relative",
  },
  input: {
    width: "100%",
    padding: "12px 40px 12px 16px",
    borderRadius: 12,
    border: "1px solid rgba(0,0,0,0.09)",
    fontSize: 14,
    fontFamily: "inherit",
    outline: "none",
    background: "#fff",
    color: "#1a1a1a",
    boxSizing: "border-box",
    transition: "border-color 0.2s, box-shadow 0.2s",
  },
  clearBtn: {
    position: "absolute",
    right: 10,
    top: "50%",
    transform: "translateY(-50%)",
    border: "none",
    background: "none",
    color: "rgba(0,0,0,0.3)",
    cursor: "pointer",
    fontSize: 12,
    padding: "4px",
    lineHeight: 1,
  },
  sendBtn: {
    width: 46,
    height: 46,
    borderRadius: 12,
    border: "none",
    background: "linear-gradient(135deg, #ffdd2d, #ffa000)",
    color: "#1a1a1a",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    boxShadow: "0 3px 10px rgba(255,221,45,0.3)",
    flexShrink: 0,
    transition: "all 0.2s",
  },

  // Tips sidebar
  tipsCol: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
    overflowY: "auto",
  },
  tipsCard: {
    background: "#fff",
    borderRadius: 16,
    border: "1px solid rgba(0,0,0,0.06)",
    padding: "16px 18px",
    boxShadow: "0 2px 8px rgba(0,0,0,0.03)",
  },
  tipsHeader: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 12,
  },
  tipsTitle: {
    fontSize: 13,
    fontWeight: 700,
    color: "#1a1a1a",
  },
  tipsLoading: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  tipSkeleton: {
    display: "flex",
    gap: 10,
    alignItems: "flex-start",
  },
  tipSkLine: {
    height: 12,
    background: "linear-gradient(90deg, #f0f0f0 25%, #e8e8e8 50%, #f0f0f0 75%)",
    backgroundSize: "200% 100%",
    borderRadius: 4,
    animation: "shimmer 1.4s infinite",
  },
  tipItem: {
    display: "flex",
    alignItems: "flex-start",
    gap: 10,
    padding: "11px 13px",
    borderRadius: 12,
    border: "1px solid",
    cursor: "default",
    transition: "all 0.2s",
  },
  tipItemIcon: { fontSize: 18, flexShrink: 0, marginTop: 1 },
  tipItemText: { fontSize: 12, color: "#1a1a1a", lineHeight: 1.55 },
  tipsEmpty: {
    textAlign: "center",
    padding: "20px 10px",
    color: "rgba(0,0,0,0.35)",
    fontSize: 12,
  },
  topicsCard: {
    background: "#fff",
    borderRadius: 16,
    border: "1px solid rgba(0,0,0,0.06)",
    padding: "16px 18px",
    boxShadow: "0 2px 8px rgba(0,0,0,0.03)",
  },
  topicBtn: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    width: "100%",
    textAlign: "left",
    padding: "9px 12px",
    borderRadius: 10,
    border: "1px solid rgba(0,0,0,0.06)",
    background: "#fafafa",
    color: "#1a1a1a",
    fontSize: 12,
    fontWeight: 500,
    cursor: "pointer",
    fontFamily: "inherit",
    transition: "all 0.2s",
  },
  disclaimer: {
    display: "flex",
    gap: 8,
    alignItems: "flex-start",
    padding: "10px 12px",
    borderRadius: 10,
    background: "rgba(0,0,0,0.02)",
    border: "1px solid rgba(0,0,0,0.04)",
    fontSize: 11,
    color: "rgba(0,0,0,0.35)",
    lineHeight: 1.5,
  },
}
