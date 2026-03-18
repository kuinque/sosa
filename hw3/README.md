# Flight Booking System

Распределённая система бронирования авиабилетов из двух микросервисов, взаимодействующих по gRPC, с кешированием в Redis.

## Архитектура

```
Client (REST) → Booking Service → (gRPC) → Flight Service
                      ↓                          ↓
                 PostgreSQL               PostgreSQL + Redis
```

### Сервисы

- **Booking Service** (порт 8000) - REST API для клиентов, управление бронированиями
- **Flight Service** (порт 50051) - gRPC API для межсервисного взаимодействия, управление рейсами

### Инфраструктура

- 2x PostgreSQL (отдельная БД для каждого сервиса)
- Redis Sentinel (master + replica + sentinel) для кеширования

## Запуск

```bash
docker-compose up --build
```

Все сервисы поднимаются одной командой. Миграции БД применяются автоматически при старте.

## API Endpoints

### Поиск рейсов
```
GET /flights?origin=SVO&destination=LED&date=2026-04-01
```

### Получение рейса
```
GET /flights/{id}
```

### Создание бронирования
```
POST /bookings
{
    "user_id": "uuid",
    "flight_id": "uuid",
    "passenger_name": "Иван Иванов",
    "passenger_email": "ivan@example.com",
    "seat_count": 2
}
```

### Получение бронирования
```
GET /bookings/{id}
```

### Отмена бронирования
```
POST /bookings/{id}/cancel
```

### Список бронирований пользователя
```
GET /bookings?user_id=uuid
```

## Реализованные требования

### 1-4 балла (базовая архитектура)
- [x] gRPC-контракт Flight Service с методами SearchFlights, GetFlight, ReserveSeats, ReleaseReservation
- [x] ER-диаграмма в 3NF (см. docs/er-diagram.md)
- [x] PostgreSQL + реализация обоих сервисов с миграциями
- [x] Межсервисное взаимодействие по gRPC

### 5-7 баллов (транзакции, аутентификация, кеширование)
- [x] Транзакционная целостность с SELECT FOR UPDATE
- [x] Аутентификация gRPC через API Key в metadata
- [x] Redis кеширование с Cache-Aside стратегией и TTL

### 8-10 баллов (отказоустойчивость)
- [x] Retry с exponential backoff (100ms, 200ms, 400ms)
- [x] Redis Sentinel (master + replica + sentinel)
- [x] Circuit Breaker (CLOSED → OPEN → HALF_OPEN)

## Конфигурация

Переменные окружения:

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| GRPC_API_KEY | API ключ для gRPC аутентификации | super-secret-api-key-12345 |
| CB_FAILURE_THRESHOLD | Порог ошибок для Circuit Breaker | 5 |
| CB_RECOVERY_TIMEOUT | Таймаут восстановления (сек) | 30 |
| RETRY_MAX_ATTEMPTS | Максимум попыток retry | 3 |
| RETRY_INITIAL_DELAY_MS | Начальная задержка retry (мс) | 100 |

## Тестовые данные

При запуске автоматически создаются тестовые рейсы:
- SU1234: SVO → LED
- SU1235: SVO → LED  
- S71001: DME → LED
- SU2001: LED → SVO
- DP405: VKO → AER
- U6101: SVO → SVX
- SU1500: SVO → KZN
