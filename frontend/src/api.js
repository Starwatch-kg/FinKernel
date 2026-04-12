/*
Fixed API client for frontend.
Syncs with backend main_secure.py API contract.
*/

const BASE = import.meta.env.VITE_API_URL || "/api"
let TOKEN = localStorage.getItem("finfuture_token") || ""

export const setToken = (token) => {
  TOKEN = token
  localStorage.setItem("finfuture_token", token)
}

export const getToken = () => TOKEN

export const clearAuth = () => {
  TOKEN = ""
  localStorage.removeItem("finfuture_token")
  localStorage.removeItem("finfuture_email")
  localStorage.removeItem("finfuture_name")
  localStorage.removeItem("finfuture_is_admin")
}

// ─── Centralized fetch with error handling + JWT ───
async function apiFetch(url, options = {}) {
  try {
    // CRITICAL: Always send JWT token in Authorization header
    if (TOKEN) {
      options.headers = { ...options.headers, Authorization: `Bearer ${TOKEN}` }
    }

    const res = await fetch(url, options)

    if (!res.ok) {
      const body = await res.json().catch(() => ({}))

      // Handle different error formats from backend
      let detail = body.message || body.detail || body.error || `Ошибка сервера (${res.status})`

      // Backend validation errors: { message: "Invalid request data", details: [{msg: "..."}, ...] }
      if (body.details && Array.isArray(body.details)) {
        const msgs = body.details.map(e => {
          let msg = e.msg || e.message || ""
          // Strip Pydantic prefix "Value error, "
          msg = msg.replace(/^Value error,\s*/i, "")
          return msg
        }).filter(Boolean)
        if (msgs.length) detail = msgs.join(". ")
      }

      // Pydantic v2 returns detail as an array of validation errors
      if (Array.isArray(detail)) {
        detail = detail.map(e => e.msg || e.message).join(", ")
      }

      throw new Error(detail)
    }

    return await res.json()
  } catch (err) {
    if (err.name === "AbortError") {
      throw err
    }
    if (err.name === "TypeError" && err.message === "Failed to fetch") {
      throw new Error("Сервер недоступен. Проверьте соединение с интернетом.")
    }
    throw err
  }
}

const POST_JSON = (body) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
})

const DELETE = () => ({
  method: "DELETE",
})

// ─── Auth ───
// FIXED: Use correct paths /api/auth/register and /api/auth/login
export const registerUser = async (email, name, password) => {
  const res = await apiFetch(`${BASE}/auth/register`, POST_JSON({ email, name, password }))

  // FIXED: Backend returns { access_token, refresh_token, is_admin }
  if (res.access_token) {
    setToken(res.access_token)
    localStorage.setItem("finfuture_email", email)
    localStorage.setItem("finfuture_name", name)

    if (res.is_admin) {
      localStorage.setItem("finfuture_is_admin", "true")
    } else {
      localStorage.removeItem("finfuture_is_admin")
    }
  }

  return res
}

export const loginUser = async (email, password) => {
  const res = await apiFetch(`${BASE}/auth/login`, POST_JSON({ email, password }))

  // FIXED: Backend returns { access_token, refresh_token, is_admin }
  if (res.access_token) {
    setToken(res.access_token)
    localStorage.setItem("finfuture_email", email)

    if (res.is_admin) {
      localStorage.setItem("finfuture_is_admin", "true")
    } else {
      localStorage.removeItem("finfuture_is_admin")
    }
  }

  return res
}

export const isAdmin = () => localStorage.getItem("finfuture_is_admin") === "true"

// ─── Dashboard ───
// FIXED: No userId parameter - backend extracts from JWT
export const getDashboard = () => apiFetch(`${BASE}/dashboard`)

// ─── Transactions ───
// FIXED: No userId parameter - backend extracts from JWT
export const getTransactions = (limit = 30) => apiFetch(`${BASE}/transactions?limit=${limit}`)

function parseTransactionAmount(amount) {
  if (typeof amount === "number") return amount
  const normalized = String(amount || "")
    .replace(/\s+/g, "")
    .replace(",", ".")
    .trim()
  return parseFloat(normalized)
}

// FIXED: Map frontend fields to backend fields
export const addTransaction = (transaction) => {
  // Map frontend fields to backend expected format
  const backendTransaction = {
    amount: parseTransactionAmount(transaction.amount),
    type: transaction.type, // "income" or "expense"
    category: mapCategoryToBackend(transaction.category), // Map Russian to English
    description: transaction.comment || transaction.description || "",
  }

  return apiFetch(`${BASE}/transactions`, POST_JSON(backendTransaction))
}

// FIXED: No userId parameter - backend extracts from JWT
export const deleteTransaction = (transactionId) =>
  apiFetch(`${BASE}/transactions/${transactionId}`, DELETE())

// ─── Category Mapping ───
// Map Russian categories from frontend to English categories for backend
const CATEGORY_MAP_TO_BACKEND = {
  // Expenses
  "Еда": "food",
  "Транспорт": "transport",
  "Развлечения": "entertainment",
  "Покупки": "other",
  "Здоровье": "other",
  "Образование": "education",
  "Другое": "other",
  // Income
  "Зарплата": "salary",
  "Фриланс": "salary",
  "Инвестиции": "other",
  "Подарок": "other",
  "💰 Зарплата": "salary",
  "💼 Фриланс": "salary",
  "📈 Инвестиции": "other",
  "🎁 Подарок": "other",
}

function mapCategoryToBackend(category) {
  // Remove emoji if present
  const cleanCategory = category.replace(/[\u{1F300}-\u{1F9FF}]/gu, "").trim()
  return CATEGORY_MAP_TO_BACKEND[cleanCategory] || CATEGORY_MAP_TO_BACKEND[category] || "other"
}

// ─── AI Prediction ───
// FIXED: No userId parameter
export const triggerPrediction = () => apiFetch(`${BASE}/predict`, { method: "POST" })
export const getPrediction = () => apiFetch(`${BASE}/predict`)

// ─── Portfolio & Trading ───
// NOTE: These endpoints don't exist in main_secure.py yet
// They exist in main.py (old version)
// For now, these will return 404 until backend is updated

export const getPortfolio = () => apiFetch(`${BASE}/portfolio`)
export const getStocks = () => apiFetch(`${BASE}/stocks`)
export const getStockDetail = (ticker) => apiFetch(`${BASE}/stock/${ticker}`)
export const getRecommendations = () => apiFetch(`${BASE}/recommendations`)

export const trade = (ticker, shares, action) =>
  apiFetch(`${BASE}/trade`, POST_JSON({ ticker, shares, action }))

export const checkPortfolio = () => apiFetch(`${BASE}/check-portfolio`, { method: "POST" })
export const resetPortfolio = () => apiFetch(`${BASE}/reset-portfolio`, { method: "POST" })

// ─── Market Events ───
export const getMarketEvent = () => apiFetch(`${BASE}/market-event`)
export const marketEventAction = (eventId, action) =>
  apiFetch(`${BASE}/market-event/action`, POST_JSON({ eventId, action }))

// ─── Learning (V2) ───
export const getModules = () => apiFetch(`${BASE}/v2/modules`)
export const getModuleLessons = (moduleId) => apiFetch(`${BASE}/v2/lessons?moduleId=${moduleId}`)
export const getLessonDetail = (lessonId) => apiFetch(`${BASE}/v2/lesson/${lessonId}`)
export const completeLesson = (lessonId, correctAnswers = 0, totalQuestions = 0) =>
  apiFetch(`${BASE}/v2/complete-lesson`, POST_JSON({ lessonId, correctAnswers, totalQuestions }))

// ─── Achievements ───
export const getAchievements = () => apiFetch(`${BASE}/achievements`)
export const getDailyMissions = () => apiFetch(`${BASE}/daily-missions`)

// ─── Onboarding ───
export const getOnboardingQuestions = () => apiFetch(`${BASE}/onboarding/questions`)
export const submitOnboarding = (answers) =>
  apiFetch(`${BASE}/onboarding/submit`, POST_JSON({
    userId: localStorage.getItem("finfuture_email") || "1",
    answers
  }))
export const getOnboardingStatus = () =>
  apiFetch(`${BASE}/onboarding/status?userId=${localStorage.getItem("finfuture_email") || "1"}`)

// ─── Data ───
export const getDiary = (limit = 20) => apiFetch(`${BASE}/diary?limit=${limit}`)
export const getLevels = () => apiFetch(`${BASE}/levels`)
export const buyFreeze = () => apiFetch(`${BASE}/buy-freeze`, { method: "POST" })
export const getProgress = () => apiFetch(`${BASE}/progress`)

// ─── Adaptive Learning ───
export const getAdaptiveMastery = () => apiFetch(`${BASE}/adaptive/mastery`)
export const getAdaptiveRecommendation = () => apiFetch(`${BASE}/adaptive/recommendation`)
export const getAdaptiveNextQuestion = (topic) => apiFetch(`${BASE}/adaptive/next-question?topic=${topic}`)
export const getAdaptiveLessonQuestions = (topic, count = 3) =>
  apiFetch(`${BASE}/adaptive/lesson-questions?topic=${topic}&count=${count}`)
export const recordAdaptiveAnswer = (topic, questionId, isCorrect, timeMs = 0, source = "lesson") =>
  apiFetch(`${BASE}/adaptive/answer`, POST_JSON({ topic, questionId, isCorrect, timeMs, source }))

// ─── LLM-Generated ───
export const generateQuestion = (topic = null) =>
  apiFetch(`${BASE}/adaptive/generate-question${topic ? `?topic=${topic}` : ''}`)
export const generateLesson = (weakTopic = null, strongTopic = null, signal = null) => {
  let url = `${BASE}/v2/generate-lesson`
  const params = []
  if (weakTopic) params.push(`weakTopic=${weakTopic}`)
  if (strongTopic) params.push(`strongTopic=${strongTopic}`)
  if (params.length) url += `?${params.join('&')}`
  return apiFetch(url, signal ? { signal } : {})
}

// ─── Legacy ───
export const getExperience = () => apiFetch(`${BASE}/experience`)
export const postInteraction = (cardId, answer_index) =>
  apiFetch(`${BASE}/interactions`, POST_JSON({ cardId, answer_index }))
