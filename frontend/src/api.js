const BASE = import.meta.env.VITE_API_URL || "/api"
let USER_ID = localStorage.getItem("finfuture_email") || "demo-user-1"
let TOKEN = localStorage.getItem("finfuture_token") || ""

export const setUserId = (email) => {
  USER_ID = email
  localStorage.setItem("finfuture_email", email)
}

export const setToken = (token) => {
  TOKEN = token
  localStorage.setItem("finfuture_token", token)
}

export const getUserId = () => USER_ID

export const clearAuth = () => {
  TOKEN = ""
  USER_ID = "demo-user-1"
  localStorage.removeItem("finfuture_token")
  localStorage.removeItem("finfuture_email")
  localStorage.removeItem("finfuture_name")
  localStorage.removeItem("finfuture_is_admin")
}

// ─── Centralized fetch with error handling + JWT ───
async function apiFetch(url, options = {}) {
  try {
    if (TOKEN) {
      options.headers = { ...options.headers, Authorization: `Bearer ${TOKEN}` }
    }
    const res = await fetch(url, options)
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      // Pydantic v2 returns detail as an array of validation errors
      let detail = body.detail || body.error || `Ошибка сервера (${res.status})`
      if (Array.isArray(detail)) {
        detail = detail.map(e => e.msg).join(", ")
      }
      throw new Error(detail)
    }
    return await res.json()
  } catch (err) {
    if (err.name === "AbortError") {
      throw err // Не оборачиваем abort — пусть тихо пропадёт
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

// ─── Auth ───
export const registerUser = async (email, name, password) => {
  const res = await apiFetch(`${BASE}/register`, POST_JSON({ email, name, password }))
  if (res.access_token) setToken(res.access_token)
  if (res.is_admin) localStorage.setItem("finfuture_is_admin", "true")
  else localStorage.removeItem("finfuture_is_admin")
  return res
}

export const loginUser = async (email, password) => {
  const res = await apiFetch(`${BASE}/login`, POST_JSON({ email, password }))
  if (res.access_token) setToken(res.access_token)
  if (res.is_admin) localStorage.setItem("finfuture_is_admin", "true")
  else localStorage.removeItem("finfuture_is_admin")
  return res
}

export const isAdmin = () => localStorage.getItem("finfuture_is_admin") === "true"

// ─── Dashboard ───
export const getDashboard = () => apiFetch(`${BASE}/dashboard?userId=${USER_ID}`)
export const getProgress = () => apiFetch(`${BASE}/progress?userId=${USER_ID}`)

// ─── Portfolio ───
export const getPortfolio = () => apiFetch(`${BASE}/portfolio?userId=${USER_ID}`)
export const trade = (ticker, shares, action) => apiFetch(`${BASE}/trade`, POST_JSON({ userId: USER_ID, ticker, shares, action }))
export const checkPortfolio = () => apiFetch(`${BASE}/check-portfolio?userId=${USER_ID}`, { method: "POST" })
export const resetPortfolio = () => apiFetch(`${BASE}/reset-portfolio?userId=${USER_ID}`, { method: "POST" })

// ─── Stocks / Market ───
export const getStocks = () => apiFetch(`${BASE}/stocks?userId=${USER_ID}`)
export const getStockDetail = (ticker) => apiFetch(`${BASE}/stock/${ticker}?userId=${USER_ID}`)
export const getMarketEvent = () => apiFetch(`${BASE}/market-event?userId=${USER_ID}`)
export const getRecommendations = () => apiFetch(`${BASE}/recommendations?userId=${USER_ID}`)
export const marketEventAction = (eventId, action) => apiFetch(`${BASE}/market-event/action`, POST_JSON({ userId: USER_ID, eventId, action }))

// ─── Lessons V2 ───
export const getModules = () => apiFetch(`${BASE}/v2/modules?userId=${USER_ID}`)
export const getModuleLessons = (moduleId) => apiFetch(`${BASE}/v2/lessons?userId=${USER_ID}&moduleId=${moduleId}`)
export const getLessonDetail = (lessonId) => apiFetch(`${BASE}/v2/lesson/${lessonId}?userId=${USER_ID}`)
export const completeLesson = (lessonId, correctAnswers = 0, totalQuestions = 0) => apiFetch(`${BASE}/v2/complete-lesson`, POST_JSON({ userId: USER_ID, lessonId, correctAnswers, totalQuestions }))

// ─── Achievements ───
export const getAchievements = () => apiFetch(`${BASE}/achievements?userId=${USER_ID}`)
export const getDailyMissions = () => apiFetch(`${BASE}/daily-missions?userId=${USER_ID}`)

// ─── Data ───
export const getDiary = (limit = 20) => apiFetch(`${BASE}/diary?userId=${USER_ID}&limit=${limit}`)
export const getTransactions = (limit = 30) => apiFetch(`${BASE}/transactions?userId=${USER_ID}&limit=${limit}`)
export const getLevels = () => apiFetch(`${BASE}/levels`)
export const buyFreeze = () => apiFetch(`${BASE}/buy-freeze`, POST_JSON({ userId: USER_ID }))

// ─── Onboarding ───
export const getOnboardingQuestions = () => apiFetch(`${BASE}/onboarding/questions`)
export const getOnboardingStatus = () => apiFetch(`${BASE}/onboarding/status?userId=${USER_ID}`)
export const submitOnboarding = (answers) => apiFetch(`${BASE}/onboarding/submit`, POST_JSON({ userId: USER_ID, answers }))
export const getOnboardingResult = () => apiFetch(`${BASE}/onboarding/result?userId=${USER_ID}`)

// ─── Adaptive Learning (ML-powered) ───
export const getAdaptiveMastery = () => apiFetch(`${BASE}/adaptive/mastery?userId=${USER_ID}`)
export const getAdaptiveRecommendation = () => apiFetch(`${BASE}/adaptive/recommendation?userId=${USER_ID}`)
export const getAdaptiveNextQuestion = (topic) => apiFetch(`${BASE}/adaptive/next-question?topic=${topic}&userId=${USER_ID}`)
export const getAdaptiveLessonQuestions = (topic, count = 3) => apiFetch(`${BASE}/adaptive/lesson-questions?topic=${topic}&count=${count}&userId=${USER_ID}`)
export const recordAdaptiveAnswer = (topic, questionId, isCorrect, timeMs = 0, source = "lesson") => apiFetch(`${BASE}/adaptive/answer`, POST_JSON({ userId: USER_ID, topic, questionId, isCorrect, timeMs, source }))

// ─── LLM-Generated Questions & Lessons ───
export const generateQuestion = (topic = null) => apiFetch(`${BASE}/adaptive/generate-question?userId=${USER_ID}${topic ? `&topic=${topic}` : ''}`)
export const generateLesson = (weakTopic = null, strongTopic = null, signal = null) => apiFetch(`${BASE}/v2/generate-lesson?userId=${USER_ID}${weakTopic ? `&weakTopic=${weakTopic}` : ''}${strongTopic ? `&strongTopic=${strongTopic}` : ''}`, signal ? { signal } : {})

// ─── Legacy ───
export const getExperience = () => apiFetch(`${BASE}/experience?userId=${USER_ID}`)
export const postInteraction = (cardId, answer_index) => apiFetch(`${BASE}/interactions`, POST_JSON({ userId: USER_ID, cardId, answer_index }))

// ─── Transactions (FinFuture) ───
export const addTransaction = (transaction) => apiFetch(`${BASE}/transactions`, POST_JSON({ userId: USER_ID, ...transaction }))
export const deleteTransaction = (transactionId) => apiFetch(`${BASE}/transactions/${transactionId}?userId=${USER_ID}`, { method: "DELETE" })
