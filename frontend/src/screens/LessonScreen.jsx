import { useState, useEffect } from "react"
import { motion as Motion, AnimatePresence } from "framer-motion"
import { getLessonDetail, completeLesson, trade, getAdaptiveLessonQuestions, getAdaptiveRecommendation, recordAdaptiveAnswer } from "../api"

export default function LessonScreen({ lessonId, aiLessonData, onComplete, onBack }) {
  const [lesson, setLesson] = useState(null)
  const [screenIdx, setScreenIdx] = useState(0)
  const [selected, setSelected] = useState(null)
  const [revealed, setRevealed] = useState(false)
  const [correctCount, setCorrectCount] = useState(0)
  const [totalQuiz, setTotalQuiz] = useState(0)
  const [completed, setCompleted] = useState(false)
  const [result, setResult] = useState(null)
  const [buyTicker, setBuyTicker] = useState(null)
  const [buyShares, setBuyShares] = useState(1)
  const [buyDone, setBuyDone] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    setLesson(null)

    let loadPromise
    if (aiLessonData?.screens) {
      // Карточка уже содержит все экраны
      loadPromise = Promise.resolve(aiLessonData)
    } else {
      loadPromise = getLessonDetail(lessonId)
    }

    loadPromise.then(async (l) => {
      if (l.screens?.length > 0) {
        setLesson(l)
        setLoading(false)
        return
      }
      const mainTopic = l.skill_topic || l.skill?.toLowerCase() || "stocks"
      try {
        const [aqMain, rec] = await Promise.all([
          getAdaptiveLessonQuestions(mainTopic, 1),
          getAdaptiveRecommendation().catch(() => null),
        ])
        const allAdaptive = []
        if (aqMain.ok && aqMain.questions?.length > 0) {
          allAdaptive.push(...aqMain.questions)
        }
        const weakTopic = rec?.recommendation?.topic_focus
        if (weakTopic && weakTopic !== mainTopic) {
          try {
            const aqWeak = await getAdaptiveLessonQuestions(weakTopic, 1)
            if (aqWeak.ok && aqWeak.questions?.length > 0) allAdaptive.push(...aqWeak.questions)
          } catch { /* swallow fetch errors silently */ }
        }
        if (allAdaptive.length > 0) {
          const adaptiveScreens = allAdaptive.map(q => ({
            type: "adaptive_quiz",
            title: `🧠 Адаптивный вопрос`,
            question: q.question,
            options: q.options.map(o => typeof o === "string" ? o : o.text),
            correct_index: q.correct_index,
            explanation: q.explanation,
            adaptive_id: q.id,
            topic: q.topic,
          }))
          const screens = [...(l.screens || [])]
          const insertAt = Math.max(screens.length - 1, 1)
          screens.splice(insertAt, 0, ...adaptiveScreens)
          l = { ...l, screens }
        }
      } catch { /* adaptive questions optional */ }
      setLesson(l)
      setLoading(false)
    }).catch(() => {
      setLoading(false)
      setLesson({ title: "Ошибка генерации", screens: [
        { type: "text", title: "Не удалось сгенерировать урок", content: "Попробуйте ещё раз позже или выберите другой урок." }
      ]})
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lessonId])

  if (loading || !lesson) {
    return (
      <div style={s.loadingScreen}>
        <div style={s.spinner} />
        <div style={s.loadingTitle}>Генерируем урок...</div>
        <div style={s.loadingSubtitle}>ИИ подбирает материал под тебя. Это может занять до минуты.</div>
        <div style={s.loadingDots}>Пожалуйста, подождите</div>
        <button style={s.loadingBackBtn} onClick={onBack}>← Назад</button>
      </div>
    )
  }

  const screens = lesson.screens || []
  const screen = screens[screenIdx]
  const progress = ((screenIdx + 1) / screens.length) * 100
  const isLast = screenIdx === screens.length - 1

  const nextScreen = () => {
    if (isLast) {
      // Complete lesson — для AI-уроков используем stub_id из aiLessonData
      const completeId = aiLessonData?.id || lessonId
      completeLesson(completeId, correctCount, totalQuiz).then(res => {
        setResult(res)
        setCompleted(true)
      })
      return
    }
    setScreenIdx(screenIdx + 1)
    setSelected(null)
    setRevealed(false)
    setBuyTicker(null)
    setBuyDone(false)
    setBuyShares(1)
  }

  const handleOptionSelect = (idx) => {
    if (revealed) return
    setSelected(idx)
  }

  const handleReveal = () => {
    setRevealed(true)
    if (screen.type === "quiz" || screen.type === "decision") {
      setTotalQuiz(t => t + 1)
      const isCorrect = selected === screen.correct_index
      if (isCorrect) setCorrectCount(c => c + 1)
      // Record to ML engine — для AI-уроков берём topic из вопроса
      const topic = screen.topic || lesson.skill_topic || "stocks"
      const qId = lesson.generated ? `ai_${lesson.id}_${screenIdx}` : `lesson_${lessonId}_${screenIdx}`
      recordAdaptiveAnswer(topic, qId, isCorrect, 0, lesson.generated ? "ai_lesson" : "lesson").catch(() => {})
    }
  }

  const handleBuy = () => {
    if (!buyTicker || buyShares < 1) return
    trade(buyTicker, buyShares, "buy").then(res => {
      if (res.ok) setBuyDone(true)
    })
  }

  // Completion screen
  if (completed) {
    return (
      <div style={s.page}>
        <Motion.div
          style={s.completionCard}
          initial={{ opacity: 0, scale: 0.85, y: 24 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 320, damping: 22 }}
        >
          <Motion.div
            style={{ display: "flex", justifyContent: "center", marginBottom: 16 }}
            initial={{ scale: 0, rotate: -20 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: "spring", stiffness: 400, damping: 16, delay: 0.15 }}
          >
            <img src="/icons/free-icon-trophy-1152912.png" alt="" style={{ width: 72, height: 72 }} />
          </Motion.div>
          <Motion.div
            style={s.completionTitle}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
          >
            {lesson.title}
          </Motion.div>
          <Motion.div
            style={s.completionSubtitle}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            Урок пройден!
          </Motion.div>
          <Motion.div
            style={s.completionStats}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.35 }}
          >
            {[
              { icon: "/icons/free-icon-star-11465609.png", text: `+${result?.xp_earned || lesson.xp_reward} XP` },
              { icon: "/icons/free-icon-brain-7827754.png", text: `Навык: ${lesson.skill}` },
              result?.streak > 0 && { icon: "/icons/free-icon-flames-4201705.png", text: `Серия: ${result.streak} дней` },
              totalQuiz > 0 && { icon: "/icons/free-icon-checkmark-16703458.png", text: `Правильных: ${correctCount}/${totalQuiz}` },
            ].filter(Boolean).map((stat, i) => (
              <Motion.div
                key={i}
                style={s.completionStat}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.4 + i * 0.07 }}
              >
                <img src={stat.icon} alt="" style={{ width: 20, height: 20 }} />
                <span>{stat.text}</span>
              </Motion.div>
            ))}
          </Motion.div>
          <Motion.div
            style={s.completionActions}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
          >
            <Motion.button
              style={s.primaryBtn}
              onClick={onComplete}
              whileHover={{ scale: 1.03, boxShadow: "0 8px 24px rgba(255,221,45,0.4)" }}
              whileTap={{ scale: 0.97 }}
            >
              Продолжить обучение
            </Motion.button>
          </Motion.div>
        </Motion.div>
      </div>
    )
  }

  return (
    <div style={s.page}>
      {/* Top bar */}
      <div style={s.topBar}>
        <button style={s.backBtn} onClick={onBack}>← Назад</button>
        <div style={s.progressBar}>
          <Motion.div
            style={s.progressFill}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          />
        </div>
        <Motion.span
          key={screenIdx}
          style={s.progressText}
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          {screenIdx + 1}/{screens.length}
        </Motion.span>
      </div>

      {/* Screen content */}
      <AnimatePresence mode="wait">
      <Motion.div
        style={s.screenCard}
        key={screenIdx}
        initial={{ opacity: 0, x: 30 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        transition={{ duration: 0.28, ease: "easeOut" }}
      >
        {screen.type === "hook" && (
          <HookScreen screen={screen} onNext={nextScreen} />
        )}
        {screen.type === "visual" && (
          <VisualScreen screen={screen} onNext={nextScreen} />
        )}
        {screen.type === "decision" && (
          <DecisionScreen
            screen={screen}
            selected={selected}
            revealed={revealed}
            onSelect={handleOptionSelect}
            onReveal={handleReveal}
            onNext={nextScreen}
          />
        )}
        {screen.type === "consequences" && (
          <ConsequencesScreen screen={screen} onNext={nextScreen} />
        )}
        {screen.type === "insight" && (
          <InsightScreen screen={screen} onNext={nextScreen} />
        )}
        {screen.type === "practice" && (
          <PracticeScreen
            screen={screen}
            buyTicker={buyTicker}
            buyShares={buyShares}
            buyDone={buyDone}
            onSelectTicker={setBuyTicker}
            onSetShares={setBuyShares}
            onBuy={handleBuy}
            onNext={nextScreen}
          />
        )}
        {screen.type === "quiz" && (
          <QuizScreen
            screen={screen}
            selected={selected}
            revealed={revealed}
            onSelect={handleOptionSelect}
            onReveal={handleReveal}
            onNext={nextScreen}
          />
        )}
        {screen.type === "text" && (
          <TextScreen screen={screen} onNext={nextScreen} isLast={isLast} />
        )}
        {screen.type === "adaptive_quiz" && (
          <AdaptiveQuizScreen
            screen={screen}
            selected={selected}
            revealed={revealed}
            onSelect={handleOptionSelect}
            onReveal={() => {
              setRevealed(true)
              setTotalQuiz(t => t + 1)
              const isCorrect = selected === screen.correct_index
              if (isCorrect) setCorrectCount(c => c + 1)
              // Record to ML engine
              recordAdaptiveAnswer(screen.topic, screen.adaptive_id, isCorrect, 0, "lesson").catch(() => {})
            }}
            onNext={nextScreen}
          />
        )}
        {screen.type === "result" && (
          <ResultScreen
            screen={screen}
            lesson={lesson}
            correctCount={correctCount}
            totalQuiz={totalQuiz}
            onFinish={nextScreen}
          />
        )}
      </Motion.div>
      </AnimatePresence>
    </div>
  )
}

// ─── Screen Components ───

function AdaptiveQuizScreen({ screen, selected, revealed, onSelect, onReveal, onNext }) {
  return (
    <div style={s.screenInner}>
      <Motion.div
        style={s.adaptiveBadge}
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "spring", stiffness: 400, damping: 18 }}
      >
        🧠 Подобран под твой уровень
      </Motion.div>
      <Motion.div
        style={s.visualTitle}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05, duration: 0.3 }}
      >
        {screen.question}
      </Motion.div>
      <div style={s.optionsGrid}>
        {screen.options.map((opt, i) => {
          const text = typeof opt === "string" ? opt : opt.text
          const isCorrect = revealed && i === screen.correct_index
          const isWrong = revealed && i === selected && i !== screen.correct_index
          return (
            <Motion.button
              key={i}
              onClick={() => !revealed && onSelect(i)}
              disabled={revealed}
              style={{
                ...s.optionCard,
                ...(selected === i && !revealed ? { borderColor: "#ffdd2d", background: "rgba(255,221,45,0.1)" } : {}),
                ...(isCorrect ? { borderColor: "#21a038", background: "rgba(33,160,56,0.08)" } : {}),
                ...(isWrong ? { borderColor: "#f44336", background: "rgba(244,67,54,0.08)" } : {}),
              }}
              initial={{ opacity: 0, y: 10 }}
              animate={{
                opacity: 1, y: 0,
                x: isWrong ? [0, -8, 8, -6, 6, 0] : 0,
                scale: isCorrect ? [1, 1.03, 1] : 1,
              }}
              transition={{ delay: i * 0.07, duration: 0.28, x: { duration: 0.4 }, scale: { duration: 0.3 } }}
              whileHover={!revealed ? { scale: 1.02, borderColor: "rgba(0,0,0,0.2)" } : {}}
              whileTap={!revealed ? { scale: 0.97 } : {}}
            >
              <span style={{ ...s.optLetter, ...(isCorrect ? { background: "#21a038", color: "#fff" } : {}), ...(isWrong ? { background: "#f44336", color: "#fff" } : {}) }}>
                {String.fromCharCode(65 + i)}
              </span>
              <span>{text}</span>
            </Motion.button>
          )
        })}
      </div>
      <AnimatePresence>
        {revealed && screen.explanation && (
          <Motion.div
            style={s.tipBox}
            initial={{ opacity: 0, y: 8, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            transition={{ duration: 0.3 }}
          >
            💡 {screen.explanation}
          </Motion.div>
        )}
      </AnimatePresence>
      {!revealed && selected !== null && (
        <Motion.button
          style={s.primaryBtn}
          onClick={onReveal}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          whileHover={{ scale: 1.02, boxShadow: "0 6px 18px rgba(255,221,45,0.4)" }}
          whileTap={{ scale: 0.97 }}
        >
          Проверить
        </Motion.button>
      )}
      {revealed && (
        <Motion.button
          style={s.primaryBtn}
          onClick={onNext}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          whileHover={{ scale: 1.02, boxShadow: "0 6px 18px rgba(255,221,45,0.4)" }}
          whileTap={{ scale: 0.97 }}
        >
          Далее →
        </Motion.button>
      )}
    </div>
  )
}

function TextScreen({ screen, onNext, isLast }) {
  return (
    <div style={s.screenInner}>
      {screen.title && <div style={s.hookTitle}>{screen.title}</div>}
      {screen.highlight && <div style={s.highlight}>{screen.highlight}</div>}
      <div style={{ ...s.hookText, whiteSpace: "pre-line" }}>{screen.content || screen.text}</div>
      {screen.tip && (
        <div style={s.tipBox}>💡 {screen.tip}</div>
      )}
      <button style={s.primaryBtn} onClick={onNext}>
        {isLast ? "Завершить урок ✓" : "Далее →"}
      </button>
    </div>
  )
}

function HookScreen({ screen, onNext }) {
  return (
    <div style={s.screenInner}>
      {screen.highlight && (
        <div style={s.highlight}>{screen.highlight}</div>
      )}
      <div style={s.hookTitle}>{screen.title}</div>
      <div style={s.hookText}>{screen.text}</div>
      <button style={s.primaryBtn} onClick={onNext}>Далее →</button>
    </div>
  )
}

function VisualScreen({ screen, onNext }) {
  return (
    <div style={s.screenInner}>
      <div style={s.visualTitle}>{screen.title}</div>
      <div style={s.visualText}>{screen.text}</div>

      {/* Interactive placeholder — visual representation */}
      {screen.interactive === "inflation_calculator" && (
        <InflationCalc params={screen.params} />
      )}
      {screen.interactive === "compound_calculator" && (
        <CompoundCalc params={screen.params} />
      )}
      {screen.interactive === "risk_return_scale" && (
        <RiskReturnScale params={screen.params} />
      )}
      {screen.interactive === "pe_comparison" && (
        <PEComparison params={screen.params} />
      )}
      {screen.interactive === "dividend_calculator" && (
        <DividendCalc params={screen.params} />
      )}

      {/* Generic interactive card */}
      {!["inflation_calculator", "compound_calculator", "risk_return_scale", "pe_comparison", "dividend_calculator"].includes(screen.interactive) && screen.interactive && (
        <div style={s.interactiveBox}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>📊</div>
          <div style={{ fontSize: 13, color: "rgba(0,0,0,0.45)" }}>Интерактивная визуализация</div>
        </div>
      )}

      {screen.params?.tabs && (
        <TabsVisual tabs={screen.params.tabs} />
      )}
      {screen.params?.factors && (
        <FactorsVisual factors={screen.params.factors} />
      )}
      {screen.params?.items && !screen.params?.tabs && !screen.params?.factors && (
        <ItemsVisual items={screen.params.items} />
      )}

      <button style={s.primaryBtn} onClick={onNext}>Далее →</button>
    </div>
  )
}

function DecisionScreen({ screen, selected, revealed, onSelect, onReveal, onNext }) {
  const options = screen.options || []
  return (
    <div style={s.screenInner}>
      <div style={s.decisionTitle}>{screen.title}</div>
      <div style={s.decisionText}>{screen.text}</div>
      <div style={s.optionsList}>
        {options.map((opt, i) => (
          <div key={i}>
            <button
              onClick={() => onSelect(i)}
              style={{
                ...s.optionBtn,
                ...(selected === i ? s.optionSelected : {}),
                ...(revealed && selected === i ? (opt.is_better ? s.optionBetter : s.optionNeutral) : {}),
              }}
            >
              <span style={s.optionEmoji}>{opt.emoji || "•"}</span>
              <span style={s.optionText}>{opt.text}</span>
              {opt.detail && <div style={s.optionDetail}>{opt.detail}</div>}
            </button>
            {revealed && selected === i && opt.outcome && (
              <div style={s.outcomeBox}>{opt.outcome}</div>
            )}
          </div>
        ))}
      </div>
      {screen.note && revealed && (
        <div style={s.noteBox}>{screen.note}</div>
      )}
      {screen.reveal && revealed && (
        <div style={s.noteBox}>{screen.reveal}</div>
      )}
      {!revealed && selected !== null ? (
        <button style={s.primaryBtn} onClick={onReveal}>Подтвердить выбор</button>
      ) : revealed ? (
        <button style={s.primaryBtn} onClick={onNext}>Далее →</button>
      ) : null}
    </div>
  )
}

function ConsequencesScreen({ screen, onNext }) {
  return (
    <div style={s.screenInner}>
      <div style={s.consequencesTitle}>{screen.title}</div>
      <div style={s.consequencesText}>{screen.text}</div>
      <div style={s.interactiveBox}>
        <div style={{ fontSize: 48 }}>📊</div>
      </div>
      <button style={s.primaryBtn} onClick={onNext}>Далее →</button>
    </div>
  )
}

function InsightScreen({ screen, onNext }) {
  return (
    <div style={s.screenInner}>
      <div style={s.insightIcon}>{screen.icon || "💡"}</div>
      <div style={s.insightText}>{screen.text}</div>
      <button style={s.primaryBtn} onClick={onNext}>Далее →</button>
    </div>
  )
}

function PracticeScreen({ screen, buyTicker, buyShares, buyDone, onSelectTicker, onSetShares, onBuy, onNext }) {
  const suggestions = screen.suggestions || ["AAPL", "SBER", "KO"]
  const stockData = {
    AAPL: { name: "Apple", price: 17500, emoji: "🍎" },
    SBER: { name: "Сбербанк", price: 290, emoji: "🏦" },
    KO: { name: "Coca-Cola", price: 6000, emoji: "🥤" },
    TSLA: { name: "Tesla", price: 25000, emoji: "⚡" },
    MSFT: { name: "Microsoft", price: 42000, emoji: "🪟" },
    GAZP: { name: "Газпром", price: 165, emoji: "🔥" },
    NVDA: { name: "Nvidia", price: 88000, emoji: "🎮" },
  }

  return (
    <div style={s.screenInner}>
      <div style={s.practiceTitle}>{screen.title}</div>
      <div style={s.practiceText}>{screen.text}</div>

      {buyDone ? (
        <div style={s.buySuccess}>
          <div style={{ fontSize: 48 }}>🎉</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: "#21a038", marginTop: 8 }}>Акция куплена!</div>
          <button style={s.primaryBtn} onClick={onNext}>Далее →</button>
        </div>
      ) : (
        <>
          <div style={s.stockPicker}>
            {suggestions.map(ticker => {
              const st = stockData[ticker] || { name: ticker, price: 0, emoji: "📊" }
              return (
                <button
                  key={ticker}
                  onClick={() => onSelectTicker(ticker)}
                  style={{
                    ...s.stockPickBtn,
                    ...(buyTicker === ticker ? s.stockPickSelected : {}),
                  }}
                >
                  <span style={{ fontSize: 24 }}>{st.emoji}</span>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "#1a1a1a" }}>{st.name}</div>
                  <div style={{ fontSize: 11, color: "rgba(0,0,0,0.4)" }}>{st.price?.toLocaleString("ru-RU")} с</div>
                </button>
              )
            })}
          </div>

          {buyTicker && (
            <div style={s.buyControls}>
              <div style={s.sharesRow}>
                <button style={s.shareBtn} onClick={() => onSetShares(Math.max(1, buyShares - 1))}>−</button>
                <div style={s.sharesDisplay}>
                  <div style={s.sharesNum}>{buyShares}</div>
                  <div style={s.sharesLabel}>акций</div>
                </div>
                <button style={s.shareBtn} onClick={() => onSetShares(buyShares + 1)}>+</button>
              </div>
              <div style={s.totalRow}>
                Итого: {(buyShares * (stockData[buyTicker]?.price || 0)).toLocaleString("ru-RU")} с
              </div>
              <button style={s.buyBtn} onClick={onBuy}>Купить 🛒</button>
            </div>
          )}

          {!buyTicker && (
            <button style={{ ...s.primaryBtn, opacity: 0.5 }} disabled>Выбери акцию</button>
          )}
        </>
      )}
    </div>
  )
}

function QuizScreen({ screen, selected, revealed, onSelect, onReveal, onNext }) {
  const options = screen.options || []
  const correct = screen.correct_index
  return (
    <div style={s.screenInner}>
      <div style={s.quizQuestion}>{screen.question}</div>
      <div style={s.optionsList}>
        {options.map((opt, i) => (
          <button
            key={i}
            onClick={() => onSelect(i)}
            disabled={revealed}
            style={{
              ...s.quizOption,
              ...(selected === i && !revealed ? s.quizOptionSelected : {}),
              ...(revealed && i === correct ? s.quizOptionCorrect : {}),
              ...(revealed && selected === i && i !== correct ? s.quizOptionWrong : {}),
            }}
          >
            <span style={s.quizDot}>
              {revealed ? (i === correct ? "✓" : selected === i ? "✗" : "") : String.fromCharCode(65 + i)}
            </span>
            <span>{opt}</span>
          </button>
        ))}
      </div>
      {revealed && screen.explanation && (
        <div style={s.explanationBox}>
          <span style={{ fontWeight: 700 }}>💡 </span>{screen.explanation}
        </div>
      )}
      {!revealed && selected !== null ? (
        <button style={s.primaryBtn} onClick={onReveal}>Проверить</button>
      ) : revealed ? (
        <button style={s.primaryBtn} onClick={onNext}>Далее →</button>
      ) : null}
    </div>
  )
}

function ResultScreen({ screen, lesson, correctCount, totalQuiz, onFinish }) {
  return (
    <div style={s.screenInner}>
      <div style={s.resultIcon}><img src="/icons/free-icon-trophy-1152912.png" alt="" style={{width:64,height:64}} /></div>
      <div style={s.resultTitle}>{screen.title || "Урок пройден!"}</div>
      <div style={s.resultStats}>
        <div style={s.resultStat}>✅ +{lesson.xp_reward} XP</div>
        <div style={s.resultStat}>🧠 Навык: {lesson.skill}</div>
        {totalQuiz > 0 && (
          <div style={s.resultStat}>📝 Правильных ответов: {correctCount}/{totalQuiz}</div>
        )}
      </div>
      <button style={s.primaryBtn} onClick={onFinish}>
        {screen.is_final ? "Завершить курс 🏆" : "Завершить урок"}
      </button>
    </div>
  )
}

// ─── Interactive Widgets ───

function InflationCalc({ params }) {
  const [rate, setRate] = useState(params?.rates?.[2] || 8)
  const initial = params?.initial || 100000
  const years = params?.years || 10
  const values = Array.from({ length: years + 1 }, (_, y) => Math.round(initial / Math.pow(1 + rate / 100, y)))
  return (
    <div style={s.widget}>
      <div style={s.widgetLabel}>Ставка инфляции: {rate}%</div>
      <input type="range" min={params?.rates?.[0] || 4} max={params?.rates?.[4] || 12}
        value={rate} onChange={e => setRate(+e.target.value)} style={s.slider} />
      <div style={s.widgetGrid}>
        {[0, 1, 3, 5, 10].filter(y => y <= years).map(y => (
          <div key={y} style={s.widgetItem}>
            <div style={s.widgetItemLabel}>{y === 0 ? "Сейчас" : `Через ${y} лет`}</div>
            <div style={{
              ...s.widgetItemValue,
              color: y === 0 ? "#21a038" : values[y] < initial * 0.7 ? "#f44336" : "#ffdd2d",
            }}>
              {values[y]?.toLocaleString("ru-RU")} с
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function CompoundCalc({ params }) {
  const [rate, setRate] = useState(10)
  const monthly = params?.monthly || 10000
  const results = [10, 20, 30].map(years => {
    let total = 0
    for (let m = 0; m < years * 12; m++) {
      total = (total + monthly) * (1 + rate / 100 / 12)
    }
    return { years, total: Math.round(total), invested: monthly * years * 12 }
  })
  return (
    <div style={s.widget}>
      <div style={s.widgetLabel}>Доходность: {rate}% годовых</div>
      <input type="range" min={5} max={15} value={rate} onChange={e => setRate(+e.target.value)} style={s.slider} />
      <div style={s.widgetGrid}>
        {results.map(r => (
          <div key={r.years} style={s.widgetItem}>
            <div style={s.widgetItemLabel}>{r.years} лет</div>
            <div style={s.widgetItemValue}>{r.total.toLocaleString("ru-RU")} с</div>
            <div style={{ fontSize: 10, color: "rgba(0,0,0,0.3)" }}>
              вложено: {r.invested.toLocaleString("ru-RU")} с
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function RiskReturnScale({ params }) {
  const items = params?.items || []
  return (
    <div style={s.widget}>
      {items.map((item, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "8px 0" }}>
          <span style={{ fontSize: 20 }}>{item.emoji}</span>
          <span style={{ flex: 1, fontSize: 13, color: "#1a1a1a" }}>{item.name}</span>
          <div style={{ display: "flex", gap: 4 }}>
            {Array.from({ length: 5 }, (_, j) => (
              <div key={j} style={{
                width: 12, height: 12, borderRadius: 2,
                background: j < item.risk ? (item.risk >= 4 ? "#f44336" : item.risk >= 3 ? "#FFA000" : "#21a038") : "rgba(0,0,0,0.06)",
              }} />
            ))}
          </div>
          <span style={{ fontSize: 12, color: "#ffdd2d", width: 40, textAlign: "right" }}>~{item.return_pct}%</span>
        </div>
      ))}
    </div>
  )
}

function PEComparison({ params }) {
  const companies = params?.companies || []
  return (
    <div style={s.widget}>
      {companies.map((c, i) => (
        <div key={i} style={{ padding: "10px 0", borderBottom: i < companies.length - 1 ? "1px solid rgba(0,0,0,0.04)" : "none" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "#1a1a1a" }}>{c.name}</span>
            <span style={{ fontSize: 14, fontWeight: 700, color: "#ffdd2d" }}>P/E {c.pe}</span>
          </div>
          <div style={{ fontSize: 12, color: "rgba(0,0,0,0.4)" }}>{c.comment}</div>
          <div style={{ marginTop: 4, height: 4, background: "rgba(0,0,0,0.08)", borderRadius: 2, overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${Math.min(c.pe / 80 * 100, 100)}%`, background: c.pe > 40 ? "#f44336" : c.pe > 20 ? "#FFA000" : "#21a038", borderRadius: 2 }} />
          </div>
        </div>
      ))}
    </div>
  )
}

function DividendCalc({ params }) {
  const stocks = params?.stocks || []
  const [amounts, setAmounts] = useState(stocks.reduce((acc, st) => ({ ...acc, [st.ticker]: 0 }), {}))
  const _totalInvested = Object.values(amounts).reduce((s, v) => s + v, 0)
  const totalDividend = stocks.reduce((s, st) => s + (amounts[st.ticker] || 0) * st.yield / 100, 0)
  return (
    <div style={s.widget}>
      {stocks.map(st => (
        <div key={st.ticker} style={{ display: "flex", alignItems: "center", gap: 12, padding: "8px 0" }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: "#1a1a1a", width: 90 }}>{st.name}</span>
          <span style={{ fontSize: 11, color: "#21a038" }}>{st.yield}%</span>
          <input type="range" min={0} max={500000} step={10000}
            value={amounts[st.ticker] || 0}
            onChange={e => setAmounts(prev => ({ ...prev, [st.ticker]: +e.target.value }))}
            style={{ ...s.slider, flex: 1 }} />
          <span style={{ fontSize: 11, color: "rgba(0,0,0,0.4)", width: 60, textAlign: "right" }}>
            {(amounts[st.ticker] || 0).toLocaleString("ru-RU")}
          </span>
        </div>
      ))}
      <div style={{ marginTop: 12, padding: "12px", background: "rgba(255,221,45,0.1)", borderRadius: 8, textAlign: "center" }}>
        <div style={{ fontSize: 12, color: "rgba(0,0,0,0.45)" }}>Годовой дивидендный доход</div>
        <div style={{ fontSize: 24, fontWeight: 800, color: "#ffdd2d" }}>{Math.round(totalDividend).toLocaleString("ru-RU")} с/год</div>
        <div style={{ fontSize: 11, color: "rgba(0,0,0,0.3)" }}>{Math.round(totalDividend / 12).toLocaleString("ru-RU")} с/мес</div>
      </div>
    </div>
  )
}

function TabsVisual({ tabs }) {
  const [active, setActive] = useState(0)
  return (
    <div style={s.widget}>
      <div style={{ display: "flex", gap: 4, marginBottom: 12 }}>
        {tabs.map((t, i) => (
          <button key={i} onClick={() => setActive(i)} style={{
            flex: 1, padding: "8px", border: "1px solid rgba(0,0,0,0.06)", borderRadius: 6,
            background: active === i ? "rgba(255,221,45,0.1)" : "transparent",
            color: active === i ? "#ffdd2d" : "rgba(0,0,0,0.45)",
            fontSize: 12, cursor: "pointer", fontFamily: "inherit",
          }}>{t.icon}</button>
        ))}
      </div>
      <div style={{ textAlign: "center", padding: "12px", fontSize: 14, color: "#1a1a1a" }}>
        {tabs[active]?.title}
      </div>
    </div>
  )
}

function FactorsVisual({ factors }) {
  return (
    <div style={s.widget}>
      {factors.map((f, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 0" }}>
          <span style={{ fontSize: 18 }}>{f.icon}</span>
          <span style={{ flex: 1, fontSize: 13, color: "#1a1a1a" }}>{f.name}</span>
          <span style={{
            fontSize: 10, padding: "2px 8px", borderRadius: 4, fontWeight: 700,
            background: f.impact === "high" ? "rgba(244,67,54,0.15)" : f.impact === "medium" ? "rgba(255,160,0,0.15)" : "rgba(33,160,56,0.15)",
            color: f.impact === "high" ? "#f44336" : f.impact === "medium" ? "#FFA000" : "#21a038",
          }}>
            {f.impact === "high" ? "Сильное" : f.impact === "medium" ? "Среднее" : "Слабое"}
          </span>
        </div>
      ))}
    </div>
  )
}

function ItemsVisual({ items }) {
  return (
    <div style={s.widget}>
      {items.map((item, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 0" }}>
          <span style={{ fontSize: 18 }}>{item.emoji}</span>
          <span style={{ flex: 1, fontSize: 13, color: "#1a1a1a" }}>{item.name}</span>
        </div>
      ))}
    </div>
  )
}

// ─── Styles ───

// Inject spinner keyframes once
if (typeof document !== "undefined" && !document.getElementById("spinner-keyframes")) {
  const style = document.createElement("style")
  style.id = "spinner-keyframes"
  style.textContent = `@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`
  document.head.appendChild(style)
}

const s = {
  page: { maxWidth: 680, margin: "0 auto" },
  loading: { color: "rgba(0,0,0,0.45)", padding: 60, textAlign: "center", fontSize: 16 },
  loadingScreen: {
    display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
    minHeight: "60vh", textAlign: "center",
  },
  spinner: {
    width: 48, height: 48, border: "4px solid rgba(0,0,0,0.08)",
    borderTop: "4px solid #9c27b0", borderRadius: "50%",
    animation: "spin 1s linear infinite", marginBottom: 24,
  },
  loadingTitle: { fontSize: 20, fontWeight: 700, color: "#1a1a1a", marginBottom: 8 },
  loadingSubtitle: { fontSize: 14, color: "rgba(0,0,0,0.4)", marginBottom: 8 },
  loadingDots: { fontSize: 12, color: "rgba(0,0,0,0.25)", marginBottom: 24 },
  loadingBackBtn: {
    padding: "10px 24px", border: "1px solid rgba(0,0,0,0.12)", borderRadius: 10,
    background: "transparent", color: "rgba(0,0,0,0.5)", fontSize: 14,
    cursor: "pointer", fontFamily: "inherit",
  },
  topBar: { display: "flex", alignItems: "center", gap: 12, marginBottom: 24 },
  backBtn: {
    background: "transparent", border: "none", color: "rgba(0,0,0,0.45)",
    fontSize: 14, cursor: "pointer", fontFamily: "inherit", padding: "4px 0",
    flexShrink: 0,
  },
  progressBar: {
    flex: 1, height: 6, background: "rgba(0,0,0,0.06)", borderRadius: 3, overflow: "hidden",
  },
  progressFill: {
    height: "100%", background: "linear-gradient(90deg, #ffdd2d, #FFA000)",
    borderRadius: 3, transition: "width 0.4s ease",
  },
  progressText: { fontSize: 12, color: "rgba(0,0,0,0.3)", flexShrink: 0 },
  screenCard: {
    background: "#ffffff", borderRadius: 20, padding: "32px 28px",
    border: "1px solid rgba(0,0,0,0.08)",
    animation: "fadeIn 0.3s ease",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  screenInner: { display: "flex", flexDirection: "column", gap: 20 },
  // Hook
  highlight: {
    padding: "8px 16px", background: "rgba(255,221,45,0.1)", borderRadius: 8,
    color: "#ffdd2d", fontSize: 14, fontWeight: 700, textAlign: "center",
  },
  adaptiveBadge: {
    display: "inline-block", padding: "4px 12px", background: "rgba(255,221,45,0.15)",
    borderRadius: 20, color: "#8b6914", fontSize: 11, fontWeight: 700, letterSpacing: 1,
    marginBottom: 12,
  },
  optionsGrid: {
    display: "flex", flexDirection: "column", gap: 8, marginBottom: 16,
  },
  optionCard: {
    display: "flex", alignItems: "center", gap: 12, padding: "14px 16px",
    border: "1px solid rgba(0,0,0,0.1)", borderRadius: 12, background: "#fff",
    cursor: "pointer", fontSize: 14, textAlign: "left", fontFamily: "inherit",
    color: "#1a1a1a", transition: "all 0.2s",
  },
  optLetter: {
    width: 28, height: 28, borderRadius: "50%", background: "rgba(0,0,0,0.05)",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 12, fontWeight: 700, flexShrink: 0,
  },
  tipBox: {
    padding: "12px 16px", background: "rgba(255,221,45,0.12)", borderRadius: 10,
    color: "#8b6914", fontSize: 14, lineHeight: 1.6, marginBottom: 16,
  },
  hookTitle: { fontSize: 24, fontWeight: 800, color: "#1a1a1a" },
  hookText: { fontSize: 16, color: "rgba(0,0,0,0.6)", lineHeight: 1.7, whiteSpace: "pre-line" },
  // Visual
  visualTitle: { fontSize: 20, fontWeight: 700, color: "#1a1a1a" },
  visualText: { fontSize: 14, color: "rgba(0,0,0,0.55)", lineHeight: 1.6, whiteSpace: "pre-line" },
  interactiveBox: {
    padding: "32px 20px", background: "rgba(0,0,0,0.03)", borderRadius: 12,
    textAlign: "center", border: "1px dashed rgba(0,0,0,0.06)",
  },
  // Decision
  decisionTitle: { fontSize: 20, fontWeight: 700, color: "#1a1a1a" },
  decisionText: { fontSize: 14, color: "rgba(0,0,0,0.55)", lineHeight: 1.6 },
  optionsList: { display: "flex", flexDirection: "column", gap: 8 },
  optionBtn: {
    width: "100%", padding: "14px 16px", border: "1px solid rgba(0,0,0,0.06)",
    borderRadius: 12, background: "rgba(0,0,0,0.03)", color: "#1a1a1a",
    fontSize: 14, cursor: "pointer", textAlign: "left", fontFamily: "inherit",
    display: "flex", alignItems: "flex-start", gap: 12, transition: "all 0.2s",
  },
  optionSelected: { borderColor: "#ffdd2d", background: "rgba(255,221,45,0.08)" },
  optionBetter: { borderColor: "#21a038", background: "rgba(33,160,56,0.1)" },
  optionNeutral: { borderColor: "rgba(0,0,0,0.1)" },
  optionEmoji: { fontSize: 20, flexShrink: 0 },
  optionText: { fontSize: 14, lineHeight: 1.5 },
  optionDetail: { fontSize: 11, color: "rgba(0,0,0,0.4)", marginTop: 4 },
  outcomeBox: {
    padding: "12px 16px", background: "rgba(255,221,45,0.06)", borderRadius: 8,
    fontSize: 13, color: "rgba(0,0,0,0.55)", lineHeight: 1.5, marginTop: 4,
    borderLeft: "3px solid #ffdd2d",
  },
  noteBox: {
    padding: "12px 16px", background: "rgba(0,0,0,0.04)", borderRadius: 8,
    fontSize: 13, color: "rgba(0,0,0,0.55)", lineHeight: 1.5, fontStyle: "italic",
  },
  // Consequences
  consequencesTitle: { fontSize: 20, fontWeight: 700, color: "#1a1a1a" },
  consequencesText: { fontSize: 14, color: "rgba(0,0,0,0.55)", lineHeight: 1.6 },
  // Insight
  insightIcon: { fontSize: 48, textAlign: "center" },
  insightText: {
    fontSize: 18, fontWeight: 600, color: "#1a1a1a", textAlign: "center",
    lineHeight: 1.7, whiteSpace: "pre-line",
  },
  // Practice
  practiceTitle: { fontSize: 20, fontWeight: 700, color: "#1a1a1a" },
  practiceText: { fontSize: 14, color: "rgba(0,0,0,0.55)", lineHeight: 1.6 },
  stockPicker: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 },
  stockPickBtn: {
    padding: "16px 8px", border: "1px solid rgba(0,0,0,0.06)",
    borderRadius: 12, background: "rgba(0,0,0,0.03)",
    cursor: "pointer", textAlign: "center", fontFamily: "inherit",
    display: "flex", flexDirection: "column", alignItems: "center", gap: 6,
    transition: "all 0.2s",
  },
  stockPickSelected: { borderColor: "#ffdd2d", background: "rgba(255,221,45,0.08)" },
  buyControls: { display: "flex", flexDirection: "column", gap: 12, alignItems: "center" },
  sharesRow: { display: "flex", alignItems: "center", gap: 20 },
  shareBtn: {
    width: 40, height: 40, borderRadius: 10, border: "1px solid rgba(0,0,0,0.06)",
    background: "transparent", color: "#1a1a1a", fontSize: 20, cursor: "pointer",
    display: "flex", alignItems: "center", justifyContent: "center",
  },
  sharesDisplay: { textAlign: "center" },
  sharesNum: { fontSize: 28, fontWeight: 800, color: "#1a1a1a" },
  sharesLabel: { fontSize: 11, color: "rgba(0,0,0,0.4)" },
  totalRow: { fontSize: 14, color: "rgba(0,0,0,0.45)" },
  buyBtn: {
    padding: "12px 40px", border: "none", borderRadius: 10,
    background: "#21a038", color: "#fff", fontSize: 15, fontWeight: 700,
    cursor: "pointer", fontFamily: "inherit",
  },
  buySuccess: { textAlign: "center", padding: "20px 0" },
  // Quiz
  quizQuestion: { fontSize: 18, fontWeight: 700, color: "#1a1a1a", lineHeight: 1.5 },
  quizOption: {
    width: "100%", padding: "14px 16px", border: "1px solid rgba(0,0,0,0.06)",
    borderRadius: 12, background: "rgba(0,0,0,0.03)", color: "#1a1a1a",
    fontSize: 14, cursor: "pointer", textAlign: "left", fontFamily: "inherit",
    display: "flex", alignItems: "center", gap: 12, transition: "all 0.2s",
  },
  quizOptionSelected: { borderColor: "#ffdd2d", background: "rgba(255,221,45,0.08)" },
  quizOptionCorrect: { borderColor: "#21a038", background: "rgba(33,160,56,0.1)" },
  quizOptionWrong: { borderColor: "#f44336", background: "rgba(244,67,54,0.1)" },
  quizDot: {
    width: 28, height: 28, borderRadius: "50%", background: "rgba(0,0,0,0.08)",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 12, fontWeight: 700, flexShrink: 0,
  },
  explanationBox: {
    padding: "12px 16px", background: "rgba(33,160,56,0.08)", borderRadius: 10,
    fontSize: 13, color: "rgba(0,0,0,0.55)", lineHeight: 1.5,
    borderLeft: "3px solid #21a038",
  },
  // Result
  resultIcon: { fontSize: 64, textAlign: "center" },
  resultTitle: { fontSize: 24, fontWeight: 800, color: "#1a1a1a", textAlign: "center" },
  resultStats: { display: "flex", flexDirection: "column", gap: 8, alignItems: "center" },
  resultStat: { fontSize: 14, color: "rgba(0,0,0,0.55)" },
  // Completion
  completionCard: {
    background: "#ffffff", borderRadius: 20, padding: "48px 32px",
    textAlign: "center", border: "1px solid rgba(0,0,0,0.08)",
    maxWidth: 500, margin: "60px auto",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  confetti: { fontSize: 72, marginBottom: 16 },
  completionTitle: { fontSize: 24, fontWeight: 800, color: "#1a1a1a", marginBottom: 8 },
  completionSubtitle: { fontSize: 16, color: "rgba(0,0,0,0.45)", marginBottom: 24 },
  completionStats: { display: "flex", flexDirection: "column", gap: 12, marginBottom: 32 },
  completionStat: {
    display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
    fontSize: 15, color: "#1a1a1a",
  },
  completionStatIcon: { fontSize: 20 },
  completionActions: { display: "flex", gap: 8, justifyContent: "center" },
  // Shared
  primaryBtn: {
    width: "100%", padding: "14px 0", border: "none", borderRadius: 12,
    background: "#ffdd2d", color: "#000", fontSize: 15, fontWeight: 700,
    cursor: "pointer", fontFamily: "inherit", transition: "all 0.2s",
  },
  // Widgets
  widget: {
    padding: "16px", background: "#f6f7f8", borderRadius: 12,
    border: "1px solid rgba(0,0,0,0.08)",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  widgetLabel: { fontSize: 13, color: "rgba(0,0,0,0.45)", marginBottom: 8 },
  slider: { width: "100%", accentColor: "#ffdd2d" },
  widgetGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))", gap: 8, marginTop: 12 },
  widgetItem: { textAlign: "center", padding: "8px" },
  widgetItemLabel: { fontSize: 11, color: "rgba(0,0,0,0.4)", marginBottom: 4 },
  widgetItemValue: { fontSize: 15, fontWeight: 700 },
}
