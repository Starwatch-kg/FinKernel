import { useState, useEffect } from "react"
import { getExperience, postInteraction } from "../api"

export default function CardScreen({ onDone, onBack }) {
  const [card, setCard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [confirmed, setConfirmed] = useState(false)
  const [result, setResult] = useState(null)
  const [correctIndex, setCorrectIndex] = useState(null)

  useEffect(() => {
    getExperience().then(data => {
      setCard(data)
      setLoading(false)
    })
  }, [])

  const handleSelect = (index) => {
    if (result?.is_correct || (result && !result.is_correct)) return
    setSelected(index)
    setConfirmed(false)
  }

  const handleRetry = () => {
    setSelected(null)
    setConfirmed(false)
    setResult(null)
  }

  const handleConfirm = async () => {
    if (selected === null || confirmed) return
    setConfirmed(true)

    // Если уже знаем правильный ответ (повторная попытка) — проверяем локально
    if (correctIndex !== null) {
      const isCorrect = selected === correctIndex
      setResult({ is_correct: isCorrect, correct_index: correctIndex })
      return
    }

    const res = await postInteraction(card.id, selected)
    if (res.correct_index !== null && res.correct_index !== undefined) {
      setCorrectIndex(res.correct_index)
    }
    setResult(res)
  }

  if (loading) return (
    <div style={s.page}>
      <div style={{ ...s.card, ...s.skeleton }}>
        <div style={{ ...s.skLine, width: "40%", height: 14, marginBottom: 20 }} />
        <div style={{ ...s.skLine, width: "90%", height: 20, marginBottom: 8 }} />
        <div style={{ ...s.skLine, width: "60%", height: 20, marginBottom: 28 }} />
        {[1,2,3,4].map(i => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 14, padding: "12px 8px" }}>
            <div style={{ ...s.skLine, width: 24, height: 24, borderRadius: "50%", flexShrink: 0 }} />
            <div style={{ ...s.skLine, width: `${50 + i * 10}%`, height: 16 }} />
          </div>
        ))}
      </div>
    </div>
  )

  const isWrong = result && !result.is_correct

  return (
    <div style={s.page}>
      <div style={s.card} className="fade-in">
        {/* Back button */}
        {onBack && (
          <button style={s.backBtn} onClick={onBack}>← Назад к карте</button>
        )}

        {/* Header */}
        <div style={s.cardHeader}>
          <div style={s.cardIcons}>
            <div style={{ ...s.cardIcon, background: "#e0e0e0", transform: "rotate(-8deg) translate(-6px, 4px)", zIndex: 1 }}>
              <span style={s.qMark}>?</span>
            </div>
            <div style={{ ...s.cardIcon, background: "#ffdd2d", zIndex: 2 }}>
              <span style={s.qMark}>?</span>
            </div>
          </div>
          <div style={s.cardMeta}>
            <div style={s.label}>Проверь Себя</div>
            <div style={s.cardTitle}>Как правильно?</div>
          </div>
        </div>

        {/* Question */}
        <p style={s.question}>{card.text}</p>

        {/* Options */}
        <div style={s.options}>
          {card.options.map((opt, i) => {
            const isSelected = selected === i
            const correct = result?.is_correct && isSelected
            const wrong = isSelected && isWrong
            const explanation = card.explanations?.[i]

            let circleStyle = { ...s.circle }
            if (correct) {
              circleStyle = { ...s.circle, background: "#ffdd2d", border: "2px solid #ffdd2d" }
            } else if (wrong) {
              circleStyle = { ...s.circle, background: "#ffcccc", border: "2px solid #e53935" }
            }

            return (
              <div key={i}>
                <div
                  style={{ ...s.option, cursor: result?.is_correct ? "default" : "pointer" }}
                  onClick={() => handleSelect(i)}
                >
                  <div style={circleStyle}>
                    {isSelected && (
                      <div style={{ ...s.dot, background: wrong ? "#e53935" : "#333" }} />
                    )}
                  </div>
                  <span style={s.optionText}>{opt}</span>
                </div>

                {/* Подсказка под каждым вариантом — только при неправильном */}
                {isWrong && explanation && (
                  <div
                    className="hint-animate"
                    style={{ ...s.inlineHint, background: wrong ? "#fff5f5" : "#fafafa", borderColor: wrong ? "#ffcdd2" : "#ebebeb", animationDelay: `${i * 80}ms` }}
                  >
                    {explanation}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Кнопка подтвердить */}
        {!result && selected !== null && (
          <button style={s.btn} onClick={handleConfirm}>Подтвердить</button>
        )}

        {/* Кнопка попробовать ещё раз — при неправильном */}
        {isWrong && (
          <button style={{ ...s.btn, marginTop: 16 }} onClick={handleRetry}>Попробовать ещё раз</button>
        )}

        {/* Кнопка продолжить — только при правильном ответе */}
        {result?.is_correct && (
          <div style={s.correctWrap}>
            <div style={s.correctBanner}>
              <span style={{ fontSize: 20 }}>✅</span>
              <span style={s.correctText}>Грамотный подход!</span>
            </div>
            <button style={s.btn} onClick={() => onDone({ card, chosen_index: selected, ...result })}>
              Продолжить →
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

const s = {
  page:        { background: "#fff", display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "32px 16px", fontFamily: "'Inter', sans-serif", minHeight: "calc(100vh - 56px)" },
  loadingWrap: { textAlign: "center", marginTop: 100, color: "#888", fontFamily: "sans-serif" },
  card:        { background: "#fff", borderRadius: 16, padding: "28px 28px 32px", maxWidth: 680, width: "100%", boxShadow: "0 1px 4px rgba(0,0,0,0.08)", border: "1px solid #ebebeb" },
  cardHeader:  { display: "flex", alignItems: "center", gap: 16, marginBottom: 20 },
  cardIcons:   { position: "relative", width: 60, height: 60, flexShrink: 0 },
  cardIcon:    { position: "absolute", width: 44, height: 44, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", top: 8 },
  qMark:       { fontSize: 22, fontWeight: "bold", color: "#333" },
  cardMeta:    { display: "flex", flexDirection: "column", gap: 2 },
  label:       { fontSize: 13, color: "#999", fontWeight: 400 },
  cardTitle:   { fontSize: 20, fontWeight: 700, color: "#1a1a1a" },
  question:    { fontSize: 16, color: "#1a1a1a", lineHeight: 1.6, marginBottom: 20, marginTop: 0 },
  options:     { display: "flex", flexDirection: "column", gap: 0, marginBottom: 8 },
  option:      { display: "flex", alignItems: "center", gap: 14, padding: "12px 8px" },
  circle:      { width: 24, height: 24, borderRadius: "50%", border: "2px solid #ccc", background: "#fff", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", transition: "all 0.15s" },
  dot:         { width: 10, height: 10, borderRadius: "50%", background: "#333" },
  optionText:  { fontSize: 15, color: "#1a1a1a", lineHeight: 1.4 },
  inlineHint:  { marginLeft: 38, marginBottom: 10, padding: "10px 14px", borderRadius: 8, border: "1px solid #ebebeb", fontSize: 13, color: "#555", lineHeight: 1.5 },
  correctWrap: { marginTop: 16, display: "flex", flexDirection: "column", gap: 12 },
  correctBanner:{ display: "flex", alignItems: "center", gap: 10, padding: "14px 16px", background: "#e8f5e9", borderRadius: 10 },
  correctText: { fontSize: 15, fontWeight: 600, color: "#2e7d32" },
  btn:         { width: "100%", padding: "14px 0", fontSize: 15, fontWeight: 600, borderRadius: 12, background: "#ffdd2d", color: "#1a1a1a", border: "none", cursor: "pointer" },
  skeleton:    { pointerEvents: "none" },
  skLine:      { background: "#f0f0f0", borderRadius: 6, animation: "pulse 1.4s ease-in-out infinite" },
  backBtn:     { background: "none", border: "none", color: "#888", fontSize: 14, cursor: "pointer", padding: "0 0 16px", fontFamily: "Inter, sans-serif", fontWeight: 500 },
}
