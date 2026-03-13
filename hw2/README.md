# Marketplace API — Домашнее задание №2 (10 баллов)

## Запуск

```bash
# Удалить старые данные (если есть проблемы с паролем)
docker compose down -v

# Запустить
docker compose up --build
```

API доступен на `http://localhost:8080`
Swagger UI: `http://localhost:8080/docs`

---

## Демонстрация по пунктам

### Пункт 1-2: OpenAPI CRUD для Product

#### Регистрация и получение токена (нужно для всех запросов)

```bash
# Регистрация пользователя (роль USER по умолчанию)
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Регистрация продавца
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "seller@example.com", "password": "password123", "role": "SELLER"}'

# Регистрация администратора
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "password123", "role": "ADMIN"}'

# Логин (получение токенов)
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "seller@example.com", "password": "password123"}'
```

Сохраните `access_token` из ответа для дальнейших запросов.

#### Создание товара (POST /products)

```bash
# Только SELLER или ADMIN
TOKEN="ваш_access_token"

curl -X POST http://localhost:8080/products \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "iPhone 15",
    "description": "Смартфон Apple",
    "price": 99999.99,
    "stock": 50,
    "category": "Electronics"
  }'
```

#### Получение товара по ID (GET /products/{id})

```bash
curl http://localhost:8080/products/1 \
  -H "Authorization: Bearer $TOKEN"
```

#### Список товаров с пагинацией и фильтрацией (GET /products)

```bash
# Все товары
curl "http://localhost:8080/products?page=0&size=20" \
  -H "Authorization: Bearer $TOKEN"

# Фильтр по статусу
curl "http://localhost:8080/products?status=ACTIVE" \
  -H "Authorization: Bearer $TOKEN"

# Фильтр по категории
curl "http://localhost:8080/products?category=Electronics" \
  -H "Authorization: Bearer $TOKEN"
```

#### Обновление товара (PUT /products/{id})

```bash
# SELLER может обновлять только свои товары, ADMIN — любые
curl -X PUT http://localhost:8080/products/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"price": 89999.99, "stock": 45}'
```

#### Мягкое удаление (DELETE /products/{id})

```bash
curl -X DELETE http://localhost:8080/products/1 \
  -H "Authorization: Bearer $TOKEN"
```

---

### Пункт 3: Кодогенерация

Генерация моделей из OpenAPI выполняется автоматически при сборке Docker-образа:

```bash
# Скрипт generate.sh
datamodel-codegen \
    --input openapi/marketplace.yaml \
    --output app/generated/models.py \
    --input-file-type openapi \
    --output-model-type pydantic_v2.BaseModel
```

---

### Пункт 4: PostgreSQL + Flyway миграции

```bash
# Подключение к PostgreSQL
docker compose exec postgres psql -U postgres -d marketplace

# Список таблиц
\dt

# Проверка индекса на status
\di idx_products_status

# Проверка данных
SELECT id, name, price, stock, status, seller_id FROM products;
SELECT * FROM users;
SELECT * FROM orders;
```

---

### Пункт 5: Обработка ошибок

#### PRODUCT_NOT_FOUND (404)

```bash
curl http://localhost:8080/products/99999 \
  -H "Authorization: Bearer $TOKEN"
```

Ответ:
```json
{"error_code": "PRODUCT_NOT_FOUND", "message": "Product not found: 99999"}
```

#### ACCESS_DENIED (403)

```bash
# USER пытается создать товар
USER_TOKEN="токен_пользователя_с_ролью_USER"

curl -X POST http://localhost:8080/products \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d '{"name": "Test", "price": 100, "stock": 10, "category": "Test"}'
```

Ответ:
```json
{"error_code": "ACCESS_DENIED", "message": "Access denied. Required roles: SELLER, ADMIN"}
```

#### TOKEN_EXPIRED (401)

```bash
curl http://localhost:8080/products \
  -H "Authorization: Bearer expired_token"
```

Ответ:
```json
{"error_code": "TOKEN_EXPIRED", "message": "Access token has expired"}
```

---

### Пункт 6: Валидация входных данных

| Поле | Ограничение |
|------|-------------|
| name | minLength: 1, maxLength: 255 |
| description | maxLength: 4000 |
| price | minimum: 0.01 |
| stock | minimum: 0 |
| category | minLength: 1, maxLength: 100 |
| items | minItems: 1, maxItems: 50 |
| quantity | minimum: 1, maximum: 999 |
| promo_code | pattern: ^[A-Z0-9_]{4,20}$ |
| password | minLength: 8 |

---

### Пункт 7: Бизнес-логика заказов

#### Подготовка данных

```bash
# Логин под продавцом
SELLER_TOKEN=$(curl -s -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "seller@example.com", "password": "password123"}' | jq -r '.access_token')

# Создать товары
curl -X POST http://localhost:8080/products \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SELLER_TOKEN" \
  -d '{"name": "Laptop", "price": 50000, "stock": 10, "category": "Electronics"}'

curl -X POST http://localhost:8080/products \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SELLER_TOKEN" \
  -d '{"name": "Mouse", "price": 2000, "stock": 100, "category": "Electronics"}'

# Создать промокод (SELLER или ADMIN)
curl -X POST http://localhost:8080/promo-codes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SELLER_TOKEN" \
  -d '{
    "code": "SAVE10",
    "discount_type": "PERCENTAGE",
    "discount_value": 10,
    "min_order_amount": 1000,
    "max_uses": 100,
    "valid_from": "2024-01-01T00:00:00Z",
    "valid_until": "2030-12-31T23:59:59Z"
  }'
```

#### Создание заказа (POST /orders)

```bash
# Логин под пользователем
USER_TOKEN=$(curl -s -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}' | jq -r '.access_token')

# Создать заказ
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d '{
    "items": [
      {"product_id": 1, "quantity": 2},
      {"product_id": 2, "quantity": 5}
    ]
  }'

# Создать заказ с промокодом
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d '{
    "items": [{"product_id": 1, "quantity": 1}],
    "promo_code": "SAVE10"
  }'
```

#### Получение заказа (GET /orders/{id})

```bash
curl http://localhost:8080/orders/1 \
  -H "Authorization: Bearer $USER_TOKEN"
```

#### Обновление заказа (PUT /orders/{id})

```bash
curl -X PUT http://localhost:8080/orders/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d '{"items": [{"product_id": 2, "quantity": 10}]}'
```

#### Отмена заказа (POST /orders/{id}/cancel)

```bash
curl -X POST http://localhost:8080/orders/1/cancel \
  -H "Authorization: Bearer $USER_TOKEN"
```

#### Проверка бизнес-ошибок

```bash
# ORDER_HAS_ACTIVE — у пользователя уже есть активный заказ
# INSUFFICIENT_STOCK — недостаточно товара
# PRODUCT_INACTIVE — товар неактивен
# ORDER_LIMIT_EXCEEDED — слишком частое создание
# PROMO_CODE_INVALID — невалидный промокод
# ORDER_OWNERSHIP_VIOLATION — чужой заказ
```

---

### Пункт 8: Логирование API

Все запросы логируются в JSON-формате:

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "endpoint": "/orders",
  "status_code": 201,
  "duration_ms": 45.23,
  "user_id": 1,
  "timestamp": "2026-03-11T12:00:00Z",
  "request_body": {"items": [{"product_id": 1, "quantity": 2}]}
}
```

#### Проверка логов

```bash
docker compose logs app | grep request_id
```

#### X-Request-Id в ответе

```bash
curl -i http://localhost:8080/products \
  -H "Authorization: Bearer $TOKEN"
```

В заголовках ответа будет `X-Request-Id`.

#### Маскирование паролей

```bash
# В логах пароль будет замаскирован
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret"}'

# В логах: "request_body": {"email": "user@example.com", "password": "***MASKED***"}
```

---

### Пункт 9: JWT-авторизация

#### Регистрация (POST /auth/register)

```bash
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "newuser@example.com", "password": "password123"}'
```

Ответ:
```json
{"id": 1, "email": "newuser@example.com", "role": "USER"}
```

#### Логин (POST /auth/login)

```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "newuser@example.com", "password": "password123"}'
```

Ответ:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "abc123...",
  "token_type": "bearer"
}
```

#### Обновление токена (POST /auth/refresh)

```bash
curl -X POST http://localhost:8080/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "abc123..."}'
```

#### Ошибки авторизации

| Код | HTTP | Когда |
|-----|------|-------|
| TOKEN_INVALID | 401 | Невалидный access token |
| TOKEN_EXPIRED | 401 | Истёкший access token |
| REFRESH_TOKEN_INVALID | 401 | Невалидный refresh token |

---

### Пункт 10: Ролевая модель доступа

#### Роли: USER, SELLER, ADMIN

#### Матрица доступа

| Операция | USER | SELLER | ADMIN |
|----------|------|--------|-------|
| GET /products | ✅ Все | ✅ Все | ✅ Все |
| GET /products/{id} | ✅ Любой | ✅ Любой | ✅ Любой |
| POST /products | ❌ | ✅ Свои | ✅ Любые |
| PUT /products/{id} | ❌ | ✅ Свои | ✅ Любые |
| DELETE /products/{id} | ❌ | ✅ Свои | ✅ Любые |
| POST /orders | ✅ | ❌ | ✅ |
| GET /orders/{id} | ✅ Свои | ❌ | ✅ Любые |
| PUT /orders/{id} | ✅ Свои | ❌ | ✅ Любые |
| POST /orders/{id}/cancel | ✅ Свои | ❌ | ✅ Любые |
| POST /promo-codes | ❌ | ✅ | ✅ |

#### Демонстрация ролевой модели

```bash
# 1. USER не может создавать товары
USER_TOKEN=$(curl -s -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}' | jq -r '.access_token')

curl -X POST http://localhost:8080/products \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d '{"name": "Test", "price": 100, "stock": 10, "category": "Test"}'
# Ответ: {"error_code": "ACCESS_DENIED", ...}

# 2. SELLER не может создавать заказы
SELLER_TOKEN=$(curl -s -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "seller@example.com", "password": "password123"}' | jq -r '.access_token')

curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SELLER_TOKEN" \
  -d '{"items": [{"product_id": 1, "quantity": 1}]}'
# Ответ: {"error_code": "ACCESS_DENIED", ...}

# 3. SELLER может изменять только свои товары
# Создать товар под одним продавцом
curl -X POST http://localhost:8080/products \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SELLER_TOKEN" \
  -d '{"name": "Seller1 Product", "price": 100, "stock": 10, "category": "Test"}'

# Зарегистрировать другого продавца
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "seller2@example.com", "password": "password123", "role": "SELLER"}'

SELLER2_TOKEN=$(curl -s -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "seller2@example.com", "password": "password123"}' | jq -r '.access_token')

# Попытка изменить чужой товар
curl -X PUT http://localhost:8080/products/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SELLER2_TOKEN" \
  -d '{"price": 200}'
# Ответ: {"error_code": "ACCESS_DENIED", "message": "You can only modify your own products"}

# 4. ADMIN может всё
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "password123"}' | jq -r '.access_token')

# ADMIN изменяет чужой товар
curl -X PUT http://localhost:8080/products/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"price": 200}'
# Успешно
```

#### Проверка seller_id в товарах

```bash
docker compose exec postgres psql -U postgres -d marketplace \
  -c "SELECT id, name, seller_id FROM products;"
```

#### Роль в JWT токене

```bash
# Декодировать токен (payload)
echo $TOKEN | cut -d'.' -f2 | base64 -d 2>/dev/null | jq
# {"sub": "1", "role": "SELLER", "exp": 1234567890, "type": "access"}
```

---

## Проверка данных в БД

```bash
# Все таблицы
docker compose exec postgres psql -U postgres -d marketplace -c "\dt"

# Пользователи
docker compose exec postgres psql -U postgres -d marketplace \
  -c "SELECT id, email, role, created_at FROM users;"

# Refresh токены
docker compose exec postgres psql -U postgres -d marketplace \
  -c "SELECT id, user_id, expires_at FROM refresh_tokens;"

# Товары с seller_id
docker compose exec postgres psql -U postgres -d marketplace \
  -c "SELECT id, name, price, stock, status, seller_id FROM products;"

# Заказы
docker compose exec postgres psql -U postgres -d marketplace \
  -c "SELECT * FROM orders;"

# Промокоды
docker compose exec postgres psql -U postgres -d marketplace \
  -c "SELECT * FROM promo_codes;"
```

---

## Структура проекта

```
hw2/
├── app/
│   ├── generated/           # Сгенерированные модели
│   │   └── models.py
│   ├── middleware/
│   │   └── logging.py       # JSON-логирование (пункт 8)
│   ├── routers/
│   │   ├── auth.py          # JWT авторизация (пункт 9)
│   │   ├── orders.py        # Бизнес-логика заказов (пункт 7)
│   │   ├── products.py      # CRUD товаров (пункты 1-4)
│   │   └── promo_codes.py   # Промокоды
│   ├── auth.py              # JWT утилиты
│   ├── config.py            # Конфигурация
│   ├── database.py          # Подключение к БД
│   ├── exceptions.py        # ApiException (пункт 5)
│   ├── models.py            # SQLAlchemy модели
│   └── main.py              # FastAPI приложение
├── migrations/
│   ├── V1__create_products_table.sql
│   ├── V2__create_orders_tables.sql
│   └── V3__create_users_and_auth.sql  # Пользователи и роли (пункты 9-10)
├── openapi/
│   └── marketplace.yaml     # OpenAPI спецификация с security
├── docker-compose.yml
├── Dockerfile
├── generate.sh
└── requirements.txt
```

---

## Чек-лист на 10 баллов

- [x] **Пункт 1**: OpenAPI CRUD для Product (5 эндпоинтов)
- [x] **Пункт 2**: Схемы данных (ProductCreate, ProductUpdate, ProductResponse)
- [x] **Пункт 3**: Кодогенерация из OpenAPI (datamodel-codegen)
- [x] **Пункт 4**: PostgreSQL + Flyway + индекс на status + триггер updated_at
- [x] **Пункт 5**: Обработка ошибок (ApiError формат, error codes)
- [x] **Пункт 6**: Валидация входных данных (constraints в OpenAPI)
- [x] **Пункт 7**: Бизнес-логика заказов (state machine, stock, promo codes)
- [x] **Пункт 8**: JSON-логирование (request_id, X-Request-Id, маскирование паролей)
- [x] **Пункт 9**: JWT-авторизация (register, login, refresh, access/refresh tokens)
- [x] **Пункт 10**: Ролевая модель (USER, SELLER, ADMIN, seller_id в products)
