# HW1 — Микросервис на Flask + Docker

Простой REST-микросервис для управления списком items.

## API

| Метод    | Путь              | Описание                  |
|----------|-------------------|---------------------------|
| `GET`    | `/health`         | Проверка работоспособности |

## Запуск через Docker

```bash
docker build -t hw1 .
docker run -p 8080:8080 hw1
```

Сервис будет доступен на `http://localhost:8080`.

## Примеры запросов

```bash
# Health-check
curl http://localhost:8080/health
```

## Запуск без Docker

```bash
pip install -r requirements.txt
python app.py
```
