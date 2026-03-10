# Marketplace API

## Запуск

```bash
docker compose up --build
```

API доступен на http://localhost:8080

Swagger UI: http://localhost:8080/docs

## Примеры запросов

### Регистрация и авторизация

```bash
# Регистрация
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"password123"}'

# Логин (получить токены)
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"password123"}'

# Обновить access token
curl -X POST http://localhost:8080/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"YOUR_REFRESH_TOKEN"}'
```

### Товары (Products)

```bash
# Создать товар (нужен токен SELLER или ADMIN)
curl -X POST http://localhost:8080/products \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{"name":"iPhone","price":999.99,"stock":10,"category":"electronics"}'

# Получить товар (без авторизации)
curl http://localhost:8080/products/1

# Список товаров с фильтрацией
curl "http://localhost:8080/products?page=0&size=10&status=ACTIVE"

# Обновить товар
curl -X PUT http://localhost:8080/products/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{"price":899.99}'

# Удалить (архивировать) товар
curl -X DELETE http://localhost:8080/products/1 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Заказы (Orders)

```bash
# Создать заказ (USER или ADMIN)
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{"items":[{"product_id":1,"quantity":2}]}'

# Создать заказ с промокодом
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{"items":[{"product_id":1,"quantity":2}],"promo_code":"SALE10"}'

# Получить заказ
curl http://localhost:8080/orders/1 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Обновить заказ
curl -X PUT http://localhost:8080/orders/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{"items":[{"product_id":1,"quantity":3}]}'

# Отменить заказ
curl -X POST http://localhost:8080/orders/1/cancel \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Промокоды (SELLER или ADMIN)

```bash
curl -X POST http://localhost:8080/promo-codes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "code":"SALE10",
    "discount_type":"PERCENTAGE",
    "discount_value":10,
    "min_order_amount":100,
    "max_uses":100,
    "valid_from":"2024-01-01T00:00:00Z",
    "valid_until":"2025-12-31T23:59:59Z"
  }'
```

## Просмотр БД

```bash
docker compose exec postgres psql -U postgres -d marketplace

# Примеры запросов
SELECT * FROM products;
SELECT * FROM orders;
SELECT * FROM order_items;
SELECT * FROM promo_codes;
SELECT * FROM users;
```

## Остановка

```bash
docker compose down -v
```

## Реализованные баллы

| Балл | Требование | Статус |
|------|------------|--------|
| 1 | OpenAPI-спецификация CRUD | ✅ |
| 2 | Схемы данных в OpenAPI | ✅ |
| 3 | Кодогенерация из OpenAPI | ✅ |
| 4 | PostgreSQL + Flyway + индекс + soft delete | ✅ |
| 5 | Контрактная обработка ошибок | ✅ |
| 6 | Контрактная валидация | ✅ |
| 7 | Бизнес-логика заказов (state machine, промокоды, rate limit) | ✅ |
| 8 | JSON-логирование API | ✅ |
| 9 | JWT-авторизация (access + refresh tokens) | ✅ |
| 10 | Ролевая модель (USER, SELLER, ADMIN) | ✅ |
