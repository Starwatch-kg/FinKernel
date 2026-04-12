import { useState, useEffect } from "react"
import { motion as Motion } from "framer-motion"
import { getOnboardingQuestions, submitOnboarding } from "../api"

export default function OnboardingScreen({ onComplete, userName, onLogout }) {
  const [phase, setPhase] = useState("welcome") // welcome | quiz | result
  const [questions, setQuestions] = useState([])
  const [currentQ, setCurrentQ] = useState(0)
  const [answers, setAnswers] = useState({})
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingQuestions, setLoadingQuestions] = useState(true)
  const [error, setError] = useState(null)

  const fetchQuestions = () => {
    setLoadingQuestions(true)
    setError(null)
    getOnboardingQuestions()
      .then(data => {
        setQuestions(data.questions || [])
        setLoadingQuestions(false)
      })
      .catch(() => {
        setError("Не удалось загрузить вопросы")
        setLoadingQuestions(false)
      })
  }

  useEffect(() => { fetchQuestions() }, [])

  const startQuiz = () => {
    setPhase("quiz")
  }

  const handleAnswer = (questionId, answerId) => {
    const question = questions.find(q => q.id === questionId)

    if (question.type === "multiple") {
      // Toggle selection for multiple choice
      const current = answers[questionId] || []
      const newAnswers = current.includes(answerId)
        ? current.filter(id => id !== answerId)
        : [...current, answerId]
      setAnswers({ ...answers, [questionId]: newAnswers })
    } else if (question.type === "input") {
      // Direct input
      setAnswers({ ...answers, [questionId]: answerId })
    } else {
      // Single choice
      setAnswers({ ...answers, [questionId]: answerId })
    }
  }

  const handleNext = () => {
    if (currentQ < questions.length - 1) {
      setCurrentQ(currentQ + 1)
    } else {
      // Submit
      setLoading(true)
      submitOnboarding(answers)
        .then(res => {
          setResult(res)
          setPhase("result")
          setLoading(false)
        })
        .catch(() => {
          setLoading(false)
          setError("Не удалось отправить ответы")
        })
    }
  }

  const canProceed = () => {
    const q = questions[currentQ]
    if (!q) return false
    const answer = answers[q.id]
    if (q.type === "multiple") {
      return answer && answer.length > 0
    }
    if (q.type === "input") {
      return answer && answer.toString().trim().length > 0
    }
    return answer !== undefined
  }

  const accountBadge = (
    <div style={s.accountBadge}>
      <div style={s.accountAvatar}>{userName?.[0]?.toUpperCase() || "?"}</div>
      <div style={s.accountInfo}>
        <div style={s.accountName}>{userName}</div>
        <div style={s.accountEmail}>{localStorage.getItem("finfuture_email") || ""}</div>
      </div>
      {onLogout && (
        <button onClick={onLogout} style={s.accountLogout}>
          Сменить
        </button>
      )}
    </div>
  )

  if (loadingQuestions) {
    return (
      <div style={s.page}>
        {accountBadge}
        <div style={s.loadingCard}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>📝</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#1a1a1a" }}>Загрузка...</div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div style={s.page}>
        {accountBadge}
        <div style={s.loadingCard}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#1a1a1a", marginBottom: 16 }}>{error}</div>
          <button style={s.startBtn} onClick={fetchQuestions}>Попробовать снова</button>
        </div>
      </div>
    )
  }

  // WELCOME
  if (phase === "welcome") {
    return (
      <div style={s.page}>
        {accountBadge}
        <div style={s.welcomeCard}>
          <div style={s.questBadge}>ФИНАНСОВЫЙ ПРОФИЛЬ</div>
          <div style={s.welcomeIcon}>💰</div>
          <div style={s.welcomeTitle}>Настроим ваши финансы!</div>
          <div style={s.welcomeText}>
            Ответьте на несколько вопросов, чтобы мы могли:{"\n"}
            • Автоматически учитывать вашу зарплату{"\n"}
            • Давать персональные рекомендации{"\n"}
            • Помочь достичь финансовых целей
          </div>

          <div style={s.welcomeFeatures}>
            {[
              { icon: "💵", text: "Автоматический учёт дохода" },
              { icon: "🎯", text: "Персональные цели" },
              { icon: "🤖", text: "AI-рекомендации" },
            ].map((f, i) => (
              <div key={i} style={s.welcomeFeature}>
                <span style={{ fontSize: 20 }}>{f.icon}</span>
                <span style={s.welcomeFeatureText}>{f.text}</span>
              </div>
            ))}
          </div>

          <button style={s.startBtn} onClick={startQuiz}>
            Начать настройку →
          </button>

          <button style={s.skipBtn} onClick={() => onComplete(null)}>
            Пропустить
          </button>
        </div>
      </div>
    )
  }

  // RESULT
  if (phase === "result" && result) {
    return (
      <div style={s.page}>
        {accountBadge}
        <div style={s.resultCard}>
          <div style={s.resultIcon}>✅</div>
          <div style={s.resultTitle}>Профиль настроен!</div>

          {result.profile && (
            <div style={s.profileSummary}>
              {result.profile.monthly_income && (
                <div style={s.summaryItem}>
                  <span style={s.summaryLabel}>Ежемесячный доход:</span>
                  <span style={s.summaryValue}>{result.profile.monthly_income.toLocaleString("ru-RU")} с</span>
                </div>
              )}
              {result.profile.savings_percent > 0 && (
                <div style={s.summaryItem}>
                  <span style={s.summaryLabel}>Цель накоплений:</span>
                  <span style={s.summaryValue}>{result.profile.savings_percent}% от дохода</span>
                </div>
              )}
            </div>
          )}

          {result.recommendations && result.recommendations.length > 0 && (
            <div style={s.recommendations}>
              <div style={s.sectionLabel}>РЕКОМЕНДАЦИИ</div>
              {result.recommendations.map((rec, i) => (
                <div key={i} style={s.recItem}>
                  <span style={s.recIcon}>💡</span>
                  <span style={s.recText}>{rec}</span>
                </div>
              ))}
            </div>
          )}

          {result.xp_bonus && (
            <div style={s.xpBonus}>
              ⚡ +{result.xp_bonus} XP за настройку профиля!
            </div>
          )}

          <button style={s.startBtn} onClick={() => onComplete(result)}>
            Начать пользоваться →
          </button>
        </div>
      </div>
    )
  }

  // QUIZ
  if (loading) {
    return (
      <div style={s.page}>
        <div style={s.loadingCard}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>💾</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#1a1a1a" }}>Сохраняем профиль...</div>
        </div>
      </div>
    )
  }

  const q = questions[currentQ]
  if (!q) return null

  const progress = ((currentQ + 1) / questions.length) * 100

  return (
    <div style={s.page}>
      {accountBadge}

      <div style={s.topBar}>
        <div style={s.questLabel}>
          Вопрос {currentQ + 1} из {questions.length}
        </div>
        <div style={s.progressBar}>
          <div style={{ ...s.progressFill, width: `${progress}%` }} />
        </div>
      </div>

      <div style={s.quizCard}>
        <div style={s.question}>{q.question}</div>

        {q.type === "input" ? (
          <div style={s.inputWrapper}>
            <input
              type={q.input_type || "text"}
              placeholder={q.placeholder || ""}
              value={answers[q.id] || ""}
              onChange={(e) => handleAnswer(q.id, e.target.value)}
              min={q.min}
              max={q.max}
              style={s.input}
            />
            {q.suffix && <span style={s.inputSuffix}>{q.suffix}</span>}
            {q.id === 3 && answers[1] && answers[3] && (
              <div style={s.calculatedAmount}>
                ≈ {Math.round((parseFloat(answers[1]) || 0) * (parseFloat(answers[3]) || 0) / 100).toLocaleString('ru-RU')} с в месяц
              </div>
            )}
          </div>
        ) : (
          <div style={s.options}>
            {q.options.map((opt) => {
              const isSelected = q.type === "multiple"
                ? (answers[q.id] || []).includes(opt.id)
                : answers[q.id] === opt.id

              return (
                <button
                  key={opt.id}
                  onClick={() => handleAnswer(q.id, opt.id)}
                  style={{
                    ...s.optionBtn,
                    ...(isSelected ? s.optionSelected : {}),
                  }}
                >
                  <span style={s.optionCheck}>
                    {isSelected ? "✓" : ""}
                  </span>
                  <span style={s.optionText}>{opt.text}</span>
                </button>
              )
            })}
          </div>
        )}

        {q.type === "multiple" && (
          <div style={s.hint}>Можно выбрать несколько вариантов</div>
        )}

        <button
          style={{
            ...s.nextBtn,
            ...(canProceed() ? {} : s.nextBtnDisabled)
          }}
          onClick={handleNext}
          disabled={!canProceed()}
        >
          {currentQ < questions.length - 1 ? "Далее →" : "Завершить"}
        </button>
      </div>
    </div>
  )
}

const s = {
  page: {
    minHeight: "100vh",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: "20px",
    background: "#f6f7f8",
    fontFamily: "Inter, sans-serif",
  },
  welcomeCard: {
    background: "#ffffff",
    borderRadius: 24,
    padding: "48px 36px",
    maxWidth: 480,
    width: "100%",
    textAlign: "center",
    border: "1px solid rgba(0,0,0,0.08)",
    boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
  },
  questBadge: {
    display: "inline-block",
    padding: "6px 16px",
    background: "rgba(255,221,45,0.15)",
    borderRadius: 20,
    color: "#b8860b",
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: 2,
    marginBottom: 20,
  },
  welcomeIcon: { fontSize: 56, marginBottom: 16 },
  welcomeTitle: { fontSize: 28, fontWeight: 800, color: "#1a1a1a", marginBottom: 12 },
  welcomeText: {
    fontSize: 15,
    color: "rgba(0,0,0,0.55)",
    lineHeight: 1.7,
    marginBottom: 28,
    whiteSpace: "pre-line",
    textAlign: "left",
  },
  welcomeFeatures: { display: "flex", flexDirection: "column", gap: 12, marginBottom: 32 },
  welcomeFeature: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "10px 16px",
    background: "#f6f7f8",
    borderRadius: 10,
    textAlign: "left",
  },
  welcomeFeatureText: { fontSize: 14, color: "#1a1a1a" },
  startBtn: {
    width: "100%",
    padding: "16px 0",
    border: "none",
    borderRadius: 14,
    background: "#ffdd2d",
    color: "#1a1a1a",
    fontSize: 16,
    fontWeight: 700,
    cursor: "pointer",
    fontFamily: "inherit",
    marginBottom: 12,
  },
  skipBtn: {
    background: "transparent",
    border: "none",
    color: "rgba(0,0,0,0.35)",
    fontSize: 13,
    cursor: "pointer",
    fontFamily: "inherit",
    padding: "8px 0",
  },
  topBar: {
    width: "100%",
    maxWidth: 620,
    display: "flex",
    alignItems: "center",
    gap: 12,
    marginBottom: 20,
  },
  questLabel: { fontSize: 13, color: "rgba(0,0,0,0.45)", flexShrink: 0 },
  progressBar: {
    flex: 1,
    height: 6,
    background: "rgba(0,0,0,0.06)",
    borderRadius: 3,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    background: "linear-gradient(90deg, #ffdd2d, #ffa000)",
    borderRadius: 3,
    transition: "width 0.4s ease",
  },
  quizCard: {
    background: "#ffffff",
    borderRadius: 20,
    padding: "32px 28px",
    maxWidth: 620,
    width: "100%",
    border: "1px solid rgba(0,0,0,0.08)",
    boxShadow: "0 2px 12px rgba(0,0,0,0.06)",
  },
  question: {
    fontSize: 20,
    fontWeight: 700,
    color: "#1a1a1a",
    marginBottom: 24,
    lineHeight: 1.4,
  },
  options: { display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 },
  optionBtn: {
    width: "100%",
    padding: "14px 16px",
    border: "1px solid rgba(0,0,0,0.1)",
    borderRadius: 12,
    background: "#ffffff",
    color: "#1a1a1a",
    fontSize: 15,
    cursor: "pointer",
    textAlign: "left",
    fontFamily: "inherit",
    display: "flex",
    alignItems: "center",
    gap: 12,
    transition: "all 0.2s",
    outline: "none",
  },
  optionSelected: {
    borderColor: "#ffdd2d",
    background: "rgba(255,221,45,0.1)",
    boxShadow: "0 0 0 2px #ffdd2d",
  },
  optionCheck: {
    width: 24,
    height: 24,
    borderRadius: "50%",
    border: "2px solid rgba(0,0,0,0.1)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 14,
    fontWeight: 700,
    flexShrink: 0,
    color: "#ffdd2d",
  },
  optionText: { flex: 1, lineHeight: 1.4 },
  hint: {
    fontSize: 12,
    color: "rgba(0,0,0,0.4)",
    marginBottom: 16,
    textAlign: "center",
  },
  nextBtn: {
    width: "100%",
    padding: "14px 0",
    border: "none",
    borderRadius: 12,
    background: "#ffdd2d",
    color: "#1a1a1a",
    fontSize: 15,
    fontWeight: 700,
    cursor: "pointer",
    fontFamily: "inherit",
  },
  nextBtnDisabled: {
    opacity: 0.5,
    cursor: "not-allowed",
  },
  loadingCard: {
    textAlign: "center",
    padding: 40,
  },
  resultCard: {
    background: "#ffffff",
    borderRadius: 24,
    padding: "36px 28px",
    maxWidth: 560,
    width: "100%",
    border: "1px solid rgba(0,0,0,0.08)",
    boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
    textAlign: "center",
  },
  resultIcon: { fontSize: 64, marginBottom: 16 },
  resultTitle: { fontSize: 24, fontWeight: 800, color: "#1a1a1a", marginBottom: 24 },
  profileSummary: {
    background: "#f6f7f8",
    borderRadius: 12,
    padding: "16px",
    marginBottom: 24,
    textAlign: "left",
  },
  summaryItem: {
    display: "flex",
    justifyContent: "space-between",
    padding: "8px 0",
    borderBottom: "1px solid rgba(0,0,0,0.06)",
  },
  summaryLabel: { fontSize: 13, color: "rgba(0,0,0,0.55)" },
  summaryValue: { fontSize: 14, fontWeight: 700, color: "#1a1a1a" },
  recommendations: { marginBottom: 24, textAlign: "left" },
  sectionLabel: {
    fontSize: 11,
    color: "rgba(0,0,0,0.4)",
    letterSpacing: 2,
    marginBottom: 12,
    fontWeight: 700,
  },
  recItem: {
    display: "flex",
    gap: 10,
    padding: "10px 12px",
    background: "rgba(255,221,45,0.08)",
    borderRadius: 10,
    marginBottom: 8,
  },
  recIcon: { fontSize: 18, flexShrink: 0 },
  recText: { fontSize: 13, color: "#1a1a1a", lineHeight: 1.5 },
  xpBonus: {
    padding: "12px 16px",
    background: "rgba(255,221,45,0.15)",
    borderRadius: 10,
    color: "#b8860b",
    fontSize: 14,
    fontWeight: 700,
    marginBottom: 20,
  },
  accountBadge: {
    position: "fixed",
    bottom: 20,
    left: 20,
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "10px 14px",
    background: "#ffffff",
    borderRadius: 12,
    border: "1px solid rgba(0,0,0,0.08)",
    boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
    zIndex: 50,
  },
  accountAvatar: {
    width: 32,
    height: 32,
    borderRadius: "50%",
    background: "#ffdd2d",
    color: "#1a1a1a",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 700,
    fontSize: 14,
    flexShrink: 0,
  },
  accountInfo: { overflow: "hidden" },
  accountName: {
    fontSize: 12,
    fontWeight: 600,
    color: "#1a1a1a",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  accountEmail: {
    fontSize: 10,
    color: "rgba(0,0,0,0.4)",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  accountLogout: {
    padding: "4px 10px",
    border: "1px solid rgba(0,0,0,0.1)",
    borderRadius: 6,
    background: "transparent",
    color: "rgba(0,0,0,0.45)",
    fontSize: 11,
    cursor: "pointer",
    fontFamily: "inherit",
    marginLeft: 4,
    flexShrink: 0,
  },
  inputWrapper: {
    position: "relative",
    marginBottom: 20,
  },
  input: {
    width: "100%",
    padding: "16px 20px",
    border: "2px solid rgba(0,0,0,0.1)",
    borderRadius: 12,
    fontSize: 18,
    fontFamily: "inherit",
    fontWeight: 600,
    color: "#1a1a1a",
    outline: "none",
    transition: "all 0.2s",
    boxSizing: "border-box",
    /* Remove number input arrows */
    MozAppearance: "textfield",
  },
  inputSuffix: {
    position: "absolute",
    right: 20,
    top: "50%",
    transform: "translateY(-50%)",
    fontSize: 18,
    fontWeight: 600,
    color: "rgba(0,0,0,0.3)",
    pointerEvents: "none",
  },
  calculatedAmount: {
    marginTop: 8,
    fontSize: 14,
    color: "#21a038",
    fontWeight: 600,
    textAlign: "center",
  },
}
