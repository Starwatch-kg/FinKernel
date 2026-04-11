# 🚨 КРИТИЧЕСКИЕ ПРОБЛЕМЫ FRONTEND-BACKEND ИНТЕГРАЦИИ

**Дата анализа:** 2026-04-11  
**Статус:** ❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ ОБНАРУЖЕНЫ

---

## 🔴 КРИТИЧЕСКАЯ ПРОБЛЕМА #1: userId в Query Parameters

### Проблема
Фронтенд отправляет `userId` в query parameters для ВСЕХ запросов:

**Frontend (api.js):**
```javascript
// Строка 80
export const getDashboard = () => apiFetch(`${BASE}/dashboard?userId=${USER_ID}`)

// Строка 84
export const getPortfolio = () => apiFetch(`${BASE}/portfolio?userId=${USER_ID}`)

// Строка 85
export const trade = (ticker, shares, action) => 
  apiFetch(`${BASE}/trade`, POST_JSON({ userId: USER_ID, ticker, shares, action }))

// Строка 108
export const getTransactions = (limit = 30) => 
  apiFetch(`${BASE}/transactions?userId=${USER_ID}&limit=${limit}`)

// Строка 134
export const addTransaction = (transaction) => 
  apiFetch(`${BASE}/transactions`, POST_JSON({ userId: USER_ID, ...transaction }))
```

### Почему это критично
1. **IDOR уязвимость** - Пользователь может изменить `userId` в запросе и получить доступ к чужим данным
2. **Игнорирование JWT** - Бекенд использует JWT для аутентификации, но фронтенд передает userId отдельно
3. **Несоответствие API контракту** - Бекенд ожидает userId из JWT, фронтенд передает в параметрах

### Backend ожидает (main_secure.py):
```python
@app.get("/api/dashboard")
async def get_dashboard(
    request: Request,
    user: UserContext = Depends(get_current_user)  # userId из JWT!
):
    # user.user_id извлекается из токена, НЕ из query params
```

---

## 🔴 КРИТИЧЕСКАЯ ПРОБЛЕМА #2: Неправильные API Endpoints

### Проблема
Фронтенд использует endpoints, которых НЕ СУЩЕСТВУЕТ на бекенде:

**Frontend вызывает:**
```javascript
// api.js:80 - НЕ СУЩЕСТВУЕТ
getDashboard = () => apiFetch(`${BASE}/dashboard?userId=${USER_ID}`)

// api.js:84 - НЕ СУЩЕСТВУЕТ  
getPortfolio = () => apiFetch(`${BASE}/portfolio?userId=${USER_ID}`)

// api.js:85 - НЕ СУЩЕСТВУЕТ
trade = () => apiFetch(`${BASE}/trade`, ...)

// api.js:108 - НЕ СУЩЕСТВУЕТ
getTransactions = () => apiFetch(`${BASE}/transactions?userId=${USER_ID}`)
```

**Backend имеет:**
```python
# main_secure.py:449
@app.get("/api/dashboard")  # ✅ Правильный путь

# main_secure.py:392
@app.get("/api/transactions")  # ✅ Правильный путь

# НО НЕТ:
# /api/portfolio - НЕ СУЩЕСТВУЕТ
# /api/trade - НЕ СУЩЕСТВУЕТ
```

### Результат
- **404 ошибки** на всех запросах портфолио и трейдинга
- Фронтенд не может получить данные
- Пользователи не могут торговать акциями

---

## 🔴 КРИТИЧЕСКАЯ ПРОБЛЕМА #3: Неправильный формат Auth Response

### Проблема
Фронтенд ожидает `res.ok`, но бекенд возвращает другой формат:

**Frontend (AuthScreen.jsx:20):**
```javascript
const res = await loginUser(email, password)
if (!res.ok) return setError(res.error || "Ошибка входа")  // ❌ res.ok не существует
```

**Backend возвращает (main_secure.py:275):**
```python
return {
    "access_token": access_token,
    "refresh_token": refresh_token,
    "token_type": "Bearer",
    "expires_in": 900,
    "is_admin": is_admin
}
# НЕТ поля "ok"!
```

### Результат
- Аутентификация всегда считается неудачной
- Пользователи не могут войти в систему
- Токены не сохраняются

---

## 🔴 КРИТИЧЕСКАЯ ПРОБЛЕМА #4: Неправильные API Paths

### Проблема
Фронтенд использует `/api/register` и `/api/login`, но бекенд имеет `/api/auth/register` и `/api/auth/login`:

**Frontend (api.js:62, 69):**
```javascript
export const registerUser = async (email, name, password) => {
  const res = await apiFetch(`${BASE}/register`, ...)  // ❌ Неправильный путь
}

export const loginUser = async (email, password) => {
  const res = await apiFetch(`${BASE}/login`, ...)  // ❌ Неправильный путь
}
```

**Backend (main_secure.py:229, 275):**
```python
@app.post("/api/auth/register", ...)  # ✅ Правильный путь

@app.post("/api/auth/login", ...)  # ✅ Правильный путь
```

### Результат
- **404 ошибки** на регистрацию и вход
- Пользователи не могут создать аккаунт
- Пользователи не могут войти

---

## 🔴 КРИТИЧЕСКАЯ ПРОБЛЕМА #5: Неправильная структура Transaction Request

### Проблема
Фронтенд отправляет неправильные поля для транзакций:

**Frontend (TransactionsScreen.jsx:87):**
```javascript
addTransaction({
  amount: "100",
  category: "Еда",  // ❌ Русский текст
  type: "expense",
  comment: "...",   // ❌ Неправильное поле
  date: "2026-04-11"  // ❌ Неправильное поле
})
```

**Backend ожидает (main_secure.py:194):**
```python
class TransactionCreateRequest(BaseModel):
    amount: float = Field(gt=0, le=1_000_000)
    type: str = Field(pattern="^(income|expense)$")
    category: str  # ✅ Но должна быть английская категория
    description: Optional[str] = Field(None, max_length=500)  # ❌ Не "comment"
    # НЕТ поля "date"
```

### Результат
- **422 Validation Error** на все транзакции
- Пользователи не могут добавить транзакции
- Категории не распознаются

---

## 🔴 КРИТИЧЕСКАЯ ПРОБЛЕМА #6: USER_ID хранится как email

### Проблема
Фронтенд использует email как userId:

**Frontend (api.js:2, 5-7):**
```javascript
let USER_ID = localStorage.getItem("finfuture_email") || "demo-user-1"

export const setUserId = (email) => {
  USER_ID = email  // ❌ Сохраняет EMAIL как userId
  localStorage.setItem("finfuture_email", email)
}
```

**Backend ожидает (main_secure.py):**
```python
user.user_id  # ✅ Это INTEGER, не email!
```

### Результат
- Несоответствие типов данных
- Запросы с email вместо числового ID
- Ошибки при поиске пользователей

---

## 📊 СВОДНАЯ ТАБЛИЦА ПРОБЛЕМ

| # | Проблема | Критичность | Влияние |
|---|----------|-------------|---------|
| 1 | userId в query params | 🔴 CRITICAL | IDOR уязвимость |
| 2 | Неправильные endpoints | 🔴 CRITICAL | 404 на все запросы |
| 3 | Неправильный формат auth | 🔴 CRITICAL | Невозможно войти |
| 4 | Неправильные API paths | 🔴 CRITICAL | 404 на auth |
| 5 | Неправильная структура данных | 🔴 CRITICAL | 422 на транзакции |
| 6 | Email вместо userId | 🔴 CRITICAL | Ошибки типов |

---

## 🎯 ПОЧЕМУ ФРОНТЕНД И БЕКЕНД НЕ РАБОТАЮТ ВМЕСТЕ

### 1. Разные API контракты
- Фронтенд: `/api/dashboard?userId=123`
- Бекенд: `/api/dashboard` (userId из JWT)

### 2. Разные форматы данных
- Фронтенд: `{ comment: "...", date: "..." }`
- Бекенд: `{ description: "...", timestamp: "..." }`

### 3. Разные пути endpoints
- Фронтенд: `/api/login`
- Бекенд: `/api/auth/login`

### 4. Разные типы идентификаторов
- Фронтенд: userId = email (string)
- Бекенд: user_id = integer

### 5. Отсутствующие endpoints
- Фронтенд вызывает `/api/portfolio`, `/api/trade`
- Бекенд не имеет этих endpoints

---

## ✅ ЧТО НУЖНО ИСПРАВИТЬ

### Приоритет 1 (Критично)
1. ✅ Убрать userId из всех query parameters
2. ✅ Исправить API paths (добавить `/auth/` префикс)
3. ✅ Исправить формат auth response
4. ✅ Добавить отсутствующие endpoints на бекенде
5. ✅ Исправить структуру данных транзакций

### Приоритет 2 (Важно)
6. ✅ Использовать числовой userId вместо email
7. ✅ Синхронизировать категории (русский ↔ английский)
8. ✅ Добавить маппинг полей (comment → description)

---

## 🚀 РЕКОМЕНДАЦИИ

1. **Создать API спецификацию** (OpenAPI/Swagger)
2. **Использовать TypeScript** на фронтенде для type safety
3. **Добавить API тесты** для проверки контрактов
4. **Централизовать маппинг данных** в одном месте
5. **Использовать code generation** из OpenAPI спецификации

---

**Вывод:** Фронтенд и бекенд используют **ПОЛНОСТЬЮ РАЗНЫЕ API контракты**. Система не может работать в текущем состоянии.

**Требуется:** Полная синхронизация API между фронтендом и бекендом.
