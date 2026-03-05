# Marketplace API

## Запуск

```bash
docker compose up --build
```

API доступен на http://localhost:8080

## Примеры запросов

```bash
# Создать товар
curl -X POST http://localhost:8080/products \
  -H "Content-Type: application/json" \
  -d '{"name":"iPhone","price":999.99,"stock":10,"category":"electronics"}'

# Получить товар
curl http://localhost:8080/products/1

# Список товаров
curl "http://localhost:8080/products?page=0&size=10"

# Обновить товар
curl -X PUT http://localhost:8080/products/1 \
  -H "Content-Type: application/json" \
  -d '{"price":899.99}'

# Удалить (архивировать) товар
curl -X DELETE http://localhost:8080/products/1
```

## Остановка

```bash
docker compose down -v
```
