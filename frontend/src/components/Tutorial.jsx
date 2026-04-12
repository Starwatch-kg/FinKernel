import { useState } from "react"

const STEPS = [
  {
    title: "Добро пожаловать в FinKernel!",
    text: "Умный финансовый ассистент для управления личными финансами. Здесь ты научишься контролировать расходы, планировать бюджет и достигать финансовых целей.",
    icon: "👋",
    highlight: null,
  },
  {
    title: "Учёт транзакций",
    text: "Записывай все свои доходы и расходы. Отслеживай, куда уходят деньги. Анализируй свои траты по категориям и периодам.",
    icon: "💰",
    highlight: "portfolio",
  },
  {
    title: "AI-советник",
    text: "Получай персональные рекомендации от искусственного интеллекта. AI анализирует твои траты и подсказывает, как оптимизировать бюджет и сэкономить больше.",
    icon: "🤖",
    highlight: "learn",
  },
  {
    title: "Ежедневные миссии",
    text: "Каждый день — 3 простые задачи: добавить транзакции, пройти урок, проверить бюджет. Выполняй их регулярно и получай бонусы XP.",
    icon: "🎯",
    highlight: "missions",
  },
  {
    title: "Бюджет и планирование",
    text: "Создавай бюджеты по категориям. Устанавливай лимиты расходов. Следи за соблюдением плана и получай уведомления при превышении.",
    icon: "📊",
    highlight: "event",
  },
  {
    title: "Достижения и прогресс",
    text: "Зарабатывай XP за финансовую дисциплину. Открывай 30 уникальных достижений. Повышай уровень и держи серию активных дней!",
    icon: "🏆",
    highlight: "achievements",
  },
  {
    title: "Готов начать?",
    text: "Начни с добавления первой транзакции. Это займёт всего минуту, и ты сразу увидишь свою финансовую картину!",
    icon: "🚀",
    highlight: null,
  },
]

export default function Tutorial({ onComplete, userName }) {
  const [step, setStep] = useState(0)
  const current = STEPS[step]
  const isLast = step === STEPS.length - 1
  const progress = ((step + 1) / STEPS.length) * 100

  return (
    <div style={s.overlay}>
      <div style={s.backdrop} />
      <div style={s.modal}>
        {/* Progress */}
        <div style={s.progressBar}>
          <div style={{ ...s.progressFill, width: `${progress}%` }} />
        </div>
        <div style={s.stepCount}>{step + 1} из {STEPS.length}</div>

        {/* Content */}
        <div style={s.iconWrap}>{current.icon}</div>
        <h2 style={s.title}>
          {step === 0 ? `${current.title.replace("!", `, ${userName}!`)}` : current.title}
        </h2>
        <p style={s.text}>{current.text}</p>

        {/* Highlight hint */}
        {current.highlight && (
          <div style={s.hint}>
            💡 Посмотри на {
              current.highlight === "portfolio" ? "раздел «Транзакции» в главном меню" :
              current.highlight === "learn" ? "раздел «Обучение» в боковом меню" :
              current.highlight === "missions" ? "карточку «Ежедневные миссии» на главной" :
              current.highlight === "event" ? "раздел «Бюджет» в боковом меню" :
              current.highlight === "achievements" ? "раздел «Достижения» в боковом меню" : ""
            }
          </div>
        )}

        {/* Buttons */}
        <div style={s.buttons}>
          {step > 0 && (
            <button style={s.backBtn} onClick={() => setStep(s => s - 1)}>
              ← Назад
            </button>
          )}
          <button
            style={isLast ? s.startBtn : s.nextBtn}
            onClick={() => {
              if (isLast) {
                localStorage.setItem("pulse_tutorial_done", "1")
                onComplete()
              } else {
                setStep(s => s + 1)
              }
            }}
          >
            {isLast ? "Начать обучение! 🚀" : "Далее →"}
          </button>
        </div>

        {/* Skip */}
        {!isLast && (
          <button style={s.skipBtn} onClick={() => {
            localStorage.setItem("pulse_tutorial_done", "1")
            onComplete()
          }}>
            Пропустить обучение
          </button>
        )}
      </div>
    </div>
  )
}

const s = {
  overlay: {
    position: "fixed",
    inset: 0,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
  },
  backdrop: {
    position: "absolute",
    inset: 0,
    background: "rgba(0,0,0,0.4)",
  },
  modal: {
    position: "relative",
    background: "#ffffff",
    borderRadius: 24,
    padding: "36px 32px 28px",
    maxWidth: 480,
    width: "90%",
    textAlign: "center",
    boxShadow: "0 8px 40px rgba(0,0,0,0.15)",
    zIndex: 1,
  },
  progressBar: {
    height: 4,
    background: "rgba(0,0,0,0.06)",
    borderRadius: 2,
    overflow: "hidden",
    marginBottom: 8,
  },
  progressFill: {
    height: "100%",
    background: "linear-gradient(90deg, #ffdd2d, #ffa000)",
    borderRadius: 2,
    transition: "width 0.3s ease",
  },
  stepCount: {
    fontSize: 12,
    color: "rgba(0,0,0,0.35)",
    marginBottom: 20,
  },
  iconWrap: {
    fontSize: 56,
    marginBottom: 16,
  },
  title: {
    fontSize: 22,
    fontWeight: 800,
    color: "#1a1a1a",
    marginBottom: 12,
    lineHeight: 1.3,
  },
  text: {
    fontSize: 15,
    color: "rgba(0,0,0,0.6)",
    lineHeight: 1.7,
    marginBottom: 20,
  },
  hint: {
    padding: "10px 16px",
    background: "rgba(255,221,45,0.12)",
    borderRadius: 10,
    fontSize: 13,
    color: "#8b6914",
    marginBottom: 20,
    textAlign: "left",
  },
  buttons: {
    display: "flex",
    gap: 8,
    marginBottom: 8,
  },
  nextBtn: {
    flex: 1,
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
  startBtn: {
    flex: 1,
    padding: "14px 0",
    border: "none",
    borderRadius: 12,
    background: "#ffdd2d",
    color: "#1a1a1a",
    fontSize: 16,
    fontWeight: 700,
    cursor: "pointer",
    fontFamily: "inherit",
  },
  backBtn: {
    padding: "14px 20px",
    border: "1px solid rgba(0,0,0,0.1)",
    borderRadius: 12,
    background: "transparent",
    color: "rgba(0,0,0,0.5)",
    fontSize: 14,
    fontWeight: 500,
    cursor: "pointer",
    fontFamily: "inherit",
  },
  skipBtn: {
    background: "none",
    border: "none",
    color: "rgba(0,0,0,0.3)",
    fontSize: 13,
    cursor: "pointer",
    fontFamily: "inherit",
    padding: "8px 0",
    marginTop: 4,
  },
}
