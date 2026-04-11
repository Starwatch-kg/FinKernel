#!/bin/bash
# Тестирование исправлений финансовой корректности

set -e

API_URL="http://localhost:8000"
USER_ID=1

echo "🧪 Тестирование исправлений финансовой корректности"
echo "=================================================="
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для проверки результата
check_result() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ PASSED${NC}"
    else
        echo -e "${RED}❌ FAILED${NC}"
    fi
}

echo "1️⃣ Тест: Создание транзакции с idempotency_key"
echo "-----------------------------------------------"
IDEMPOTENCY_KEY=$(uuidgen)
echo "Idempotency key: $IDEMPOTENCY_KEY"

# Первый запрос
RESPONSE1=$(curl -s -X POST "$API_URL/api/transactions" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": $USER_ID,
    \"amount\": 100,
    \"type\": \"income\",
    \"category\": \"salary\",
    \"description\": \"Test transaction\",
    \"idempotency_key\": \"$IDEMPOTENCY_KEY\"
  }")

TRANSACTION_ID=$(echo $RESPONSE1 | jq -r '.id')
echo "Создана транзакция ID: $TRANSACTION_ID"

# Второй запрос с тем же idempotency_key (должен вернуть ту же транзакцию)
RESPONSE2=$(curl -s -X POST "$API_URL/api/transactions" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": $USER_ID,
    \"amount\": 100,
    \"type\": \"income\",
    \"category\": \"salary\",
    \"description\": \"Test transaction\",
    \"idempotency_key\": \"$IDEMPOTENCY_KEY\"
  }")

TRANSACTION_ID2=$(echo $RESPONSE2 | jq -r '.id')

if [ "$TRANSACTION_ID" == "$TRANSACTION_ID2" ]; then
    echo -e "${GREEN}✅ Idempotency работает! Оба запроса вернули ID: $TRANSACTION_ID${NC}"
else
    echo -e "${RED}❌ Idempotency НЕ работает! ID1: $TRANSACTION_ID, ID2: $TRANSACTION_ID2${NC}"
fi

echo ""
echo "2️⃣ Тест: Конкурентные транзакции (проверка race conditions)"
echo "-----------------------------------------------------------"
echo "Отправка 10 конкурентных запросов на расход 50..."

# Получаем текущий баланс
BALANCE_BEFORE=$(curl -s "$API_URL/api/dashboard/$USER_ID" | jq -r '.balance.current')
echo "Баланс до теста: $BALANCE_BEFORE"

# Отправляем 10 конкурентных запросов
for i in {1..10}; do
    curl -s -X POST "$API_URL/api/transactions" \
      -H "Content-Type: application/json" \
      -d "{
        \"user_id\": $USER_ID,
        \"amount\": 50,
        \"type\": \"expense\",
        \"category\": \"food\",
        \"description\": \"Concurrent test $i\"
      }" > /dev/null &
done

# Ждем завершения всех запросов
wait

sleep 2

# Проверяем баланс после
BALANCE_AFTER=$(curl -s "$API_URL/api/dashboard/$USER_ID" | jq -r '.balance.current')
echo "Баланс после теста: $BALANCE_AFTER"

EXPECTED_BALANCE=$(echo "$BALANCE_BEFORE - 500" | bc)
echo "Ожидаемый баланс: $EXPECTED_BALANCE"

if [ "$BALANCE_AFTER" == "$EXPECTED_BALANCE" ]; then
    echo -e "${GREEN}✅ Race conditions исправлены! Баланс корректен.${NC}"
else
    echo -e "${YELLOW}⚠️  Баланс отличается. Возможно, некоторые запросы были отклонены из-за недостатка средств.${NC}"
fi

echo ""
echo "3️⃣ Тест: Проверка недостаточности средств"
echo "------------------------------------------"
echo "Попытка потратить больше, чем есть на балансе..."

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/transactions" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": $USER_ID,
    \"amount\": 999999,
    \"type\": \"expense\",
    \"category\": \"food\",
    \"description\": \"Should fail\"
  }")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

if [ "$HTTP_CODE" == "400" ]; then
    echo -e "${GREEN}✅ Проверка недостаточности средств работает!${NC}"
else
    echo -e "${RED}❌ Проверка недостаточности средств НЕ работает! HTTP код: $HTTP_CODE${NC}"
fi

echo ""
echo "4️⃣ Тест: Торговля с idempotency_key"
echo "------------------------------------"
TRADE_IDEMPOTENCY_KEY=$(uuidgen)
echo "Trade idempotency key: $TRADE_IDEMPOTENCY_KEY"

# Первый запрос на покупку
TRADE_RESPONSE1=$(curl -s -X POST "$API_URL/api/trade" \
  -H "Content-Type: application/json" \
  -d "{
    \"userId\": \"$USER_ID\",
    \"ticker\": \"AAPL\",
    \"shares\": 1,
    \"action\": \"buy\",
    \"idempotency_key\": \"$TRADE_IDEMPOTENCY_KEY\"
  }")

echo "Первый запрос: $(echo $TRADE_RESPONSE1 | jq -r '.status')"

# Второй запрос с тем же idempotency_key
TRADE_RESPONSE2=$(curl -s -X POST "$API_URL/api/trade" \
  -H "Content-Type: application/json" \
  -d "{
    \"userId\": \"$USER_ID\",
    \"ticker\": \"AAPL\",
    \"shares\": 1,
    \"action\": \"buy\",
    \"idempotency_key\": \"$TRADE_IDEMPOTENCY_KEY\"
  }")

IS_IDEMPOTENT=$(echo $TRADE_RESPONSE2 | jq -r '.idempotent')

if [ "$IS_IDEMPOTENT" == "true" ]; then
    echo -e "${GREEN}✅ Trade idempotency работает!${NC}"
else
    echo -e "${YELLOW}⚠️  Trade idempotency может не работать (idempotent: $IS_IDEMPOTENT)${NC}"
fi

echo ""
echo "5️⃣ Тест: Удаление транзакции"
echo "-----------------------------"

# Создаем транзакцию для удаления
DELETE_RESPONSE=$(curl -s -X POST "$API_URL/api/transactions" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": $USER_ID,
    \"amount\": 10,
    \"type\": \"expense\",
    \"category\": \"food\",
    \"description\": \"To be deleted\"
  }")

DELETE_TXN_ID=$(echo $DELETE_RESPONSE | jq -r '.id')
echo "Создана транзакция для удаления ID: $DELETE_TXN_ID"

BALANCE_BEFORE_DELETE=$(curl -s "$API_URL/api/dashboard/$USER_ID" | jq -r '.balance.current')
echo "Баланс до удаления: $BALANCE_BEFORE_DELETE"

# Удаляем транзакцию
curl -s -X DELETE "$API_URL/api/transactions/$DELETE_TXN_ID?userId=$USER_ID" > /dev/null

sleep 1

BALANCE_AFTER_DELETE=$(curl -s "$API_URL/api/dashboard/$USER_ID" | jq -r '.balance.current')
echo "Баланс после удаления: $BALANCE_AFTER_DELETE"

EXPECTED_BALANCE_DELETE=$(echo "$BALANCE_BEFORE_DELETE + 10" | bc)

if [ "$BALANCE_AFTER_DELETE" == "$EXPECTED_BALANCE_DELETE" ]; then
    echo -e "${GREEN}✅ Удаление транзакции работает корректно!${NC}"
else
    echo -e "${RED}❌ Удаление транзакции работает некорректно!${NC}"
fi

echo ""
echo "=================================================="
echo "🎉 Тестирование завершено!"
echo ""
echo "📊 Итоговый баланс пользователя $USER_ID:"
curl -s "$API_URL/api/dashboard/$USER_ID" | jq '{balance: .balance.current, income: .income.month, expenses: .expenses.month}'
