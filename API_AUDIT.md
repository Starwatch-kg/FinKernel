# ОТЧЕТ ПО АУДИТУ API - FinKernel

## КРИТИЧЕСКИЕ НЕСООТВЕТСТВИЯ ФРОНТ-БЭК

### ❌ ОТСУТСТВУЮЩИЕ ЭНДПОИНТЫ В БЭКЕНДЕ

Фронтенд вызывает, но бэкенд НЕ реализует:

1. **POST /api/trade** - Торговля акциями
2. **POST /api/reset-portfolio** - Сброс портфолио
3. **GET /api/stocks** - Список акций
4. **GET /api/stock/{ticker}** - Детали акции
5. **GET /api/market-event** - Рыночные события
6. **GET /api/recommendations** - Рекомендации
7. **POST /api/market-event/action** - Действие на событие
8. **GET /api/daily-missions** - Ежедневные миссии
9. **POST /api/buy-freeze** - Покупка заморозки
10. **GET /api/adaptive/mastery** - Адаптивное обучение (все эндпоинты)
11. **GET /api/adaptive/recommendation**
12. **GET /api/adaptive/next-question**
13. **GET /api/adaptive/lesson-questions**
14. **POST /api/adaptive/answer**
15. **GET /api/adaptive/generate-question**
16. **POST /api/v2/generate-lesson**
17. **GET /api/experience**
18. **POST /api/interactions**

### ⚠️ НЕСООТВЕТСТВИЯ В ФОРМАТАХ ДАННЫХ

1. **POST /api/transactions**
   - Фронт отправляет: `{ userId, ...transaction }`
   - Бэк ожидает: `userId` как query param + body
   - **ИСПРАВИТЬ**: Принимать userId из body

2. **POST /api/v2/complete-lesson**
   - Фронт отправляет: `{ userId, lessonId, correctAnswers, totalQuestions }`
   - Бэк ожидает: query params
   - **ИСПРАВИТЬ**: Принимать из body

3. **POST /api/onboarding/submit**
   - Фронт отправляет: `{ userId, answers }`
   - Бэк ожидает: query param + body
   - **ИСПРАВИТЬ**: Принимать userId из body

### ✅ РЕАЛИЗОВАННЫЕ ЭНДПОИНТЫ (OK)

- POST /api/register ✓
- POST /api/login ✓
- GET /api/dashboard ✓
- GET /api/progress ✓
- GET /api/portfolio ✓ (заглушка)
- POST /api/check-portfolio ✓
- GET /api/transactions ✓
- DELETE /api/transactions/{id} ✓
- GET /api/v2/modules ✓
- GET /api/v2/lessons ✓
- GET /api/v2/lesson/{id} ✓
- GET /api/achievements ✓
- GET /api/onboarding/status ✓
- GET /api/onboarding/questions ✓
- GET /api/onboarding/result ✓
- GET /api/diary ✓
- GET /api/levels ✓

## РЕКОМЕНДАЦИИ

### Вариант 1: Минимальный (Быстрый релиз)
Добавить заглушки для всех отсутствующих эндпоинтов, возвращающие пустые данные.

### Вариант 2: Полный (Качественный продукт)
Реализовать все функции или удалить неиспользуемые вызовы из фронтенда.

### Вариант 3: Гибридный (Рекомендуемый)
- Исправить форматы данных в существующих эндпоинтах
- Добавить заглушки для неиспользуемых функций (stocks, adaptive learning)
- Удалить из фронтенда вызовы к legacy эндпоинтам
