import { useState } from "react"

export default function AboutScreen() {
  const [openSection, setOpenSection] = useState(null)

  const toggle = (id) => setOpenSection(openSection === id ? null : id)

  const sections = [
    {
      id: "what",
      icon: "🎯",
      title: "Что такое Kernel?",
      text: "Kernel — это умный финансовый ассистент для зумеров. Здесь ты учишься управлять личными финансами, контролировать траты и планировать бюджет. Добавляй транзакции, получай советы от AI и достигай финансовых целей.",
    },
    {
      id: "how",
      icon: "📊",
      title: "Как работает приложение?",
      text: "Ты добавляешь свои доходы и расходы, выбираешь категории (еда, транспорт, развлечения). Kernel анализирует твои траты и показывает, на что уходит больше всего денег. AI-советник подсказывает, как оптимизировать расходы и не тратить лишнего.",
    },
    {
      id: "transactions",
      icon: "💰",
      title: "Как добавлять транзакции?",
      text: "Во вкладке «Транзакции» нажми кнопку «+ Добавить». Выбери тип (доход или расход), укажи сумму, категорию, дату и комментарий. Все транзакции сохраняются и отображаются в списке. Ты можешь фильтровать их по типу.",
    },
    {
      id: "ai",
      icon: "🤖",
      title: "Как работает AI-советник?",
      text: "Во вкладке «AI-Советник» ты можешь задать любой вопрос о финансах. AI анализирует твои траты и даёт персональные рекомендации: где можно сэкономить, как планировать бюджет, когда могут закончиться деньги при текущем темпе расходов.",
    },
    {
      id: "forecast",
      icon: "🔮",
      title: "Что такое прогноз?",
      text: "На главной странице ты видишь прогноз — через сколько дней могут закончиться деньги при текущих тратах. Это помогает планировать расходы и не уйти в минус. Если прогноз показывает мало дней — пора сократить траты!",
    },
    {
      id: "achievements",
      icon: "🏆",
      title: "Достижения и геймификация",
      text: "За активность ты получаешь достижения: «7 дней без импульсивных покупок», «Первый сохранённый бюджет», «Мастер экономии» и другие. Выполняй цели и прокачивай свои финансовые навыки!",
    },
    {
      id: "tips",
      icon: "🧠",
      title: "Советы по управлению финансами",
      items: [
        "Откладывай 10-15% от каждого дохода на сбережения",
        "Веди учёт всех трат — даже мелких",
        "Планируй крупные покупки заранее",
        "Сокращай импульсивные траты — подумай дважды перед покупкой",
        "Используй категории, чтобы видеть, куда уходят деньги",
        "Слушай советы AI — они основаны на твоих реальных данных",
      ],
    },
    {
      id: "categories",
      icon: "📂",
      title: "Категории транзакций",
      text: "Расходы: Еда, Транспорт, Развлечения, Покупки, Здоровье, Образование. Доходы: Зарплата, Фриланс, Инвестиции, Подарки. Правильная категоризация помогает понять, на что уходит больше всего денег.",
    },
  ]

  return (
    <div style={s.page}>
      <div style={s.header}>
        <h1 style={s.title}>О проекте</h1>
        <p style={s.subtitle}>Всё, что нужно знать о Kernel</p>
      </div>

      <div style={s.sections}>
        {sections.map((sec) => (
          <div key={sec.id} style={s.card} onClick={() => toggle(sec.id)}>
            <div style={s.cardHeader}>
              <span style={s.cardIcon}>{sec.icon}</span>
              <span style={s.cardTitle}>{sec.title}</span>
              <span style={{
                ...s.chevron,
                transform: openSection === sec.id ? "rotate(180deg)" : "rotate(0deg)",
              }}>▾</span>
            </div>
            {openSection === sec.id && (
              <div style={s.cardBody}>
                {sec.text && <p style={s.cardText}>{sec.text}</p>}
                {sec.items && (
                  <ul style={s.tipsList}>
                    {sec.items.map((item, i) => (
                      <li key={i} style={s.tipItem}>{item}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <div style={s.footer}>
        <p style={s.footerText}>Kernel — умный финансовый ассистент. Управляй деньгами осознанно!</p>
      </div>
    </div>
  )
}

const s = {
  page: {
    maxWidth: 700,
    margin: "0 auto",
    padding: "32px 20px 60px",
  },
  header: {
    marginBottom: 28,
  },
  title: {
    fontSize: 28,
    fontWeight: 800,
    color: "#1a1a1a",
    margin: 0,
  },
  subtitle: {
    fontSize: 15,
    color: "#888",
    marginTop: 6,
  },
  sections: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  card: {
    background: "#fff",
    borderRadius: 16,
    border: "1px solid #f0f0f0",
    overflow: "hidden",
    cursor: "pointer",
    transition: "box-shadow 0.2s",
  },
  cardHeader: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "16px 20px",
  },
  cardIcon: {
    fontSize: 24,
    flexShrink: 0,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: 700,
    color: "#1a1a1a",
    flex: 1,
  },
  chevron: {
    fontSize: 18,
    color: "#bbb",
    transition: "transform 0.2s",
    flexShrink: 0,
  },
  cardBody: {
    padding: "0 20px 16px",
    borderTop: "1px solid #f5f5f5",
    paddingTop: 14,
  },
  cardText: {
    fontSize: 14,
    lineHeight: 1.6,
    color: "#555",
    margin: 0,
  },
  tipsList: {
    margin: 0,
    paddingLeft: 20,
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  tipItem: {
    fontSize: 14,
    lineHeight: 1.5,
    color: "#555",
  },
  footer: {
    marginTop: 32,
    padding: "16px 20px",
    background: "#f8f8f8",
    borderRadius: 12,
    textAlign: "center",
  },
  footerText: {
    fontSize: 13,
    color: "#999",
    margin: 0,
  },
}
