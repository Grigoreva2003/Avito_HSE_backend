# Backend разработка
Курс по Backend'у от магистерской программы НИУ ВШЭ в сотрудничестве с Авито

## Автор
Григорьева Василиса, студентка магистратуры НИУ ВШЭ ФКН х Авито "Машинное обучение в цифровом продукте"

## Описание проекта
Сервис модерации объявлений с использованием ML-модели (LogisticRegression) для предсказания нарушений. 

## Навигация

- [Быстрый старт](#быстрый-старт)
- [Конфигурация](#конфигурация-)
- [API и авторизация](#api)
- [Примеры использования](#примеры-использования)
- [Наблюдаемость](#наблюдаемость-prometheus-grafana-sentry)
- [Документация по компонентам](#документация-по-компонентам)

## Документация по компонентам

- Тесты и сценарии запуска: [`tests/README.md`](tests/README.md)
- Асинхронная обработка, retry, DLQ: [`app/workers/README.md`](app/workers/README.md)
- Миграции и схема БД: [`db/README.md`](db/README.md)

### Архитектура
Проект построен по принципу **многослойной микросервисной архитектуры**:

- **HTTP Layer** (routers/) - обработка HTTP запросов, валидация, обработка ошибок
- **Service Layer** (services/) - бизнес-логика модерации
- **ML Layer** (ml/) - работа с ML-моделью
- **Message Queue** (Kafka/Redpanda) - асинхронная обработка через очереди
- **Workers** (app/workers/) - фоновые обработчики задач модерации
- **Data Layer** (repositories/) - работа с PostgreSQL
- **Dead Letter Queue** - обработка ошибок и retry механизм

### Структура проекта
```
├── main.py                         # Точка входа FastAPI
├── config.py                       # Настройки приложения
├── database.py                     # Подключение к PostgreSQL
├── docker-compose.yml              # PostgreSQL + Redis + Redpanda + Prometheus + Grafana
├── prometheus.yml                  # Конфиг scrape для Prometheus
├── pytest.ini                      # Маркеры тестов (integration)
├── ml/                             # ML слой
│   ├── __init__.py
│   └── model_manager.py            # ModelManager - работа с ML-моделью
├── models/                         # Pydantic модели
│   ├── ads.py                      # Модели запросов/ответов модерации
│   └── auth.py                     # Модели запросов/ответов авторизации
├── routers/                        # HTTP слой
│   └── ads.py                      # Эндпоинты API
├── services/                       # Бизнес-логика
│   ├── exceptions.py               # Доменные исключения
│   ├── moderation.py               # Синхронная модерация
│   ├── async_moderation.py         # Асинхронная модерация
│   └── auth.py                     # JWT авторизация
├── repositories/                   # Data Access Layer
│   ├── __init__.py
│   ├── accounts.py                 # CRUD для аккаунтов
│   ├── sellers.py                  # CRUD для продавцов
│   ├── ads.py                      # CRUD для объявлений
│   ├── moderation_results.py       # CRUD для результатов модерации
│   └── prediction_cache.py         # Кэш предсказаний (Redis)
├── app/                            # Клиенты и воркеры
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── kafka.py                # Kafka Producer
│   │   └── redis.py                # Redis client
│   ├── observability/
│   │   ├── __init__.py
│   │   └── prometheus_middleware.py # HTTP метрики и middleware
│   ├── metrics.py                  # Бизнес-метрики сервиса
│   └── workers/
│       ├── __init__.py
│       ├── moderation_worker.py    # Kafka Consumer (воркер)
│       └── dlq_monitor.py          # DLQ Monitor
├── db/                             # SQL миграции и конфиг
│   ├── migrations/
│   │   ├── V001__initial_schema.sql
│   │   ├── V002__seed_data.sql
│   │   ├── V003__moderation_results.sql
│   │   ├── V004__add_is_closed_to_ads.sql
│   │   └── V005__create_account_table.sql
│   ├── README.md
│   └── migrations.yml
├── tests/
│   ├── conftest.py                 # Общие фикстуры
│   ├── unit/                       # API и бизнес-логика (с моками)
│   └── integration/                # Интеграционные тесты
│       ├── postgresql/             # Тесты репозиториев PostgreSQL
│       └── test_prediction_cache_integration.py
└── requirements.txt                # Зависимости Python
```

## Быстрый старт

### 1. Создайте и активируйте виртуальное окружение
```bash
python3 -m venv venv
source venv/bin/activate  # для macOS/Linux
```

### 2. Установите и настройте PostgreSQL

```bash
# Установите PostgreSQL 15 (macOS)
brew install postgresql@15

# Запустите сервис PostgreSQL
brew services start postgresql@15

# Добавьте PostgreSQL в PATH
export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"
```

### 3. Создайте файл с переменными окружения

```bash
# Создайте .env файл в корне проекта
cat > .env << 'EOF'
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=
DB_DATABASE=avito_moderation
DB_POOL_MIN_SIZE=10
DB_POOL_MAX_SIZE=20

APP_NAME=Avito Moderation Service
APP_VERSION=1.0.0
APP_HOST=0.0.0.0
APP_PORT=8003
APP_DEBUG=False
APP_LOG_LEVEL=INFO

ML_MODEL_PATH=model.pkl
ML_MODEL_VERSION=1.0.0

JWT_SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_COOKIE_NAME=access_token

SENTRY_ENABLED=false
SENTRY_DSN=
SENTRY_TRACES_SAMPLE_RATE=1.0
SENTRY_ENVIRONMENT=development
EOF
```

**Важно:** 
- Замените `DB_USER=postgres` на ваше имя пользователя (выполните `whoami` в терминале)
- Для локальной разработки на macOS обычно пароль не требуется (оставьте `DB_PASSWORD=` пустым)
- Для production установите сильный пароль
- Файл `.env` не должен попадать в git


### 4. Установите зависимости Python

```bash
pip install -r requirements.txt
```

### 5. Запустите инфраструктуру в Docker/Podman (PostgreSQL + Redis + Kafka + Prometheus + Grafana)

```bash
# Запустить все сервисы
docker-compose up -d

# Проверить статус
docker-compose ps
```

**Сервисы:**
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- Kafka (Redpanda): `localhost:9092`
- Web Console: http://localhost:8080
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (login: `admin`, password: `admin`)

Если нужен только Redis (например, для проверки кэша):
```bash
docker-compose up -d redis
```

### 6. Запустите приложение

```bash
python3.11 main.py
```

Сервис будет доступен по адресу: `http://localhost:8003`

При первом запуске:
- Устанавливается подключение к PostgreSQL
- **ModelManager** автоматически инициализируется
- Обучается модель на синтетических данных
- Модель сохраняется в `model.pkl`
- **Kafka Producer** подключается к Redpanda
- При последующих запусках модель загружается из файла

### 7. Запустите воркер для асинхронной обработки (опционально)

```bash
# В отдельном терминале
python3.11 -m app.workers.moderation_worker
```

Воркер обрабатывает задачи модерации из Kafka очереди.

## Конфигурация 🔧

Все настройки приложения вынесены в файл `.env` и загружаются через `config.py` с использованием **Pydantic Settings**.

### Структура конфигурации

| Группа           | Префикс    | Описание                                    |
|------------------|------------|---------------------------------------------|
| DatabaseSettings | `DB_*`     | Параметры подключения к PostgreSQL          |
| AppSettings      | `APP_*`    | Настройки приложения (порт, хост, логи)     |
| MLSettings       | `ML_*`     | Настройки ML-модели (путь к файлу модели)   |
| RedisSettings    | `REDIS_*`  | Настройки Redis-кэша                        |
| KafkaSettings    | `KAFKA_*`  | Настройки Kafka/Redpanda                    |
| JWTSettings      | `JWT_*`    | Настройки JWT и cookie авторизации          |
| SentrySettings   | `SENTRY_*` | Настройки Sentry (ошибки и трассировка)     |

**Примечание для macOS:** PostgreSQL по умолчанию использует имя текущего пользователя системы. Узнайте его командой `whoami` и используйте в `DB_USER`. Пароль обычно не требуется для локальной разработки (оставьте `DB_PASSWORD` пустым).

### Пример использования в коде

```python
from config import get_settings

settings = get_settings()

# Доступ к настройкам БД
print(settings.database.host)          # localhost
print(settings.database.url)           # postgresql://user:pass@host:port/db
print(settings.database.async_url)     # postgresql+asyncpg://...

# Доступ к настройкам приложения
print(settings.app.port)               # 8003
print(settings.app.log_level)          # INFO
print(settings.app.debug)              # False

# Доступ к настройкам модели
print(settings.ml.model_path)          # model.pkl
```
## База данных

Подробная документация по схеме, миграциям, применению и проверке данных
вынесена в [`db/README.md`](db/README.md).

### Репозитории

Для работы с БД используются репозитории:

- **SellerRepository** (`repositories/sellers.py`) - CRUD операции для продавцов
- **AdRepository** (`repositories/ads.py`) - CRUD операции для объявлений

Пример использования:

```python
from repositories import SellerRepository, AdRepository

# Получить продавца
seller_repo = SellerRepository()
seller = await seller_repo.get_by_id(1)

# Получить объявление со связанными данными
ad_repo = AdRepository()
ad = await ad_repo.get_by_id(100, include_seller=True)
print(ad.seller_is_verified)  # True
```

## API

### Авторизация

Перед вызовом ручек модерации нужно пройти логин: сервис выдает JWT и кладет его
в httpOnly cookie `access_token`. Проверка выполняется dependency
`get_current_account`, которая возвращает модель аккаунта.

#### POST /login
Авторизация пользователя по `login` и `password`.

**Запрос:**
```json
{
  "login": "demo-user",
  "password": "demo-password"
}
```

**Ответ (200 OK):**
```json
{
  "account_id": 1,
  "message": "Login successful"
}
```

**Коды ответов:**
- `200` - Успешная авторизация, cookie с JWT установлена
- `401` - Неверный логин/пароль
- `403` - Аккаунт заблокирован
- `422` - Ошибка валидации
- `500` - Внутренняя ошибка

Ручка `/login` публичная. Ручки предсказаний защищены и требуют cookie с JWT:
`/predict`, `/simple_predict`, `/async_predict`, `/moderation_result/{task_id}`, `/close`.

### Синхронные эндпоинты

#### POST /predict
Синхронное предсказание нарушений (с полными данными).

**Запрос:**
```json
{
  "seller_id": 1,
  "is_verified_seller": true,
  "item_id": 100,
  "name": "Название товара",
  "description": "Подробное описание товара",
  "category": 5,
  "images_qty": 3
}
```

**Ответ (200 OK):**
```json
{
  "is_violation": false,
  "probability": 0.12
}
```

**Коды ответов:**
- `200` - Успешное предсказание
- `401` - Требуется авторизация
- `422` - Ошибка валидации входных данных
- `503` - ML-модель недоступна
- `500` - Внутренняя ошибка сервера

#### POST /simple_predict
Синхронное предсказание (только по item_id, данные берутся из БД).

**Запрос:**
```json
{
  "item_id": 100
}
```

**Ответ (200 OK):**
```json
{
  "is_violation": false,
  "probability": 0.12
}
```

**Коды ответов:**
- `200` - Успешное предсказание
- `401` - Требуется авторизация
- `404` - Объявление не найдено
- `422` - Ошибка валидации входных данных
- `503` - ML-модель недоступна
- `500` - Внутренняя ошибка сервера

### Асинхронные эндпоинты (через Kafka)

#### POST /async_predict
Отправить задачу на асинхронную модерацию.

**Запрос:**
```json
{
  "item_id": 100
}
```

**Ответ (200 OK):**
```json
{
  "task_id": 1,
  "status": "pending",
  "message": "Moderation request accepted"
}
```

**Коды ответов:**
- `200` - Задача принята
- `401` - Требуется авторизация
- `404` - Объявление не найдено
- `422` - Ошибка валидации
- `500` - Внутренняя ошибка

#### POST /close
Закрыть объявление по `item_id`.

Метод выполняет soft-close:
- помечает объявление как `is_closed = TRUE` в PostgreSQL,
- удаляет связанные записи `moderation_results` из PostgreSQL,
- очищает кэш предсказания по `item_id` и кэш async-результатов по `task_id` из Redis.

**Запрос:**
```json
{
  "item_id": 100
}
```

**Ответ (200 OK):**
```json
{
  "item_id": 100,
  "status": "closed",
  "message": "Ad successfully closed"
}
```

**Коды ответов:**
- `200` - Объявление успешно закрыто
- `401` - Требуется авторизация
- `404` - Объявление не найдено
- `422` - Ошибка валидации
- `500` - Внутренняя ошибка

#### GET /moderation_result/{task_id}
Получить результат асинхронной модерации (polling).

**Ответ (pending):**
```json
{
  "task_id": 1,
  "status": "pending",
  "is_violation": null,
  "probability": null
}
```

**Ответ (completed):**
```json
{
  "task_id": 1,
  "status": "completed",
  "is_violation": false,
  "probability": 0.23
}
```

**Ответ (failed):**
```json
{
  "task_id": 1,
  "status": "failed",
  "is_violation": null,
  "probability": null,
  "error_message": "ML-модель недоступна"
}
```

**Коды ответов:**
- `200` - Результат получен
- `401` - Требуется авторизация
- `404` - Задача не найдена
- `500` - Внутренняя ошибка

## Асинхронная обработка и тестирование

Подробная документация вынесена в компонентные файлы:

- Воркеры, retry и DLQ: [`app/workers/README.md`](app/workers/README.md)
- Запуск и структура тестов: [`tests/README.md`](tests/README.md)

## Примеры использования

### Логин и использование cookie JWT

```bash
# 1. Логин (cookie сохранится в файл cookies.txt)
curl -X POST http://localhost:8003/login \
  -H "Content-Type: application/json" \
  -d '{"login":"demo-user","password":"demo-password"}' \
  -c cookies.txt

# 2. Вызов защищенной ручки с этой cookie
curl -X POST http://localhost:8003/simple_predict \
  -H "Content-Type: application/json" \
  -d '{"item_id": 100}' \
  -b cookies.txt
```

### Синхронная модерация

```bash
# Полные данные
curl -X POST http://localhost:8003/predict \
  -H "Content-Type: application/json" \
  -d '{
    "seller_id": 1,
    "is_verified_seller": true,
    "item_id": 100,
    "name": "iPhone 15",
    "description": "Новый телефон",
    "category": 1,
    "images_qty": 5
  }'

# Только item_id
curl -X POST http://localhost:8003/simple_predict \
  -H "Content-Type: application/json" \
  -d '{"item_id": 100}'
```

### Асинхронная модерация

```bash
# 1. Отправить задачу
curl -X POST http://localhost:8003/async_predict \
  -H "Content-Type: application/json" \
  -d '{"item_id": 100}'

# Ответ: {"task_id": 1, "status": "pending", ...}

# 2. Проверить статус (polling)
curl http://localhost:8003/moderation_result/1

# Пока обрабатывается: {"status": "pending", ...}
# После обработки: {"status": "completed", "is_violation": false, ...}
```

## Наблюдаемость (Prometheus, Grafana, Sentry)

### Метрики Prometheus и дашборды Grafana

В сервис добавлена базовая и бизнес-инструментация:

- HTTP-метрики через кастомный middleware:
  - `http_requests_total{method, endpoint, status}`
  - `http_request_duration_seconds{method, endpoint}`
- Метрики ML и БД:
  - `predictions_total{result}`
  - `prediction_duration_seconds`
  - `prediction_errors_total{error_type}`
  - `model_prediction_probability`
  - `db_query_duration_seconds{query_type}`

Эндпоинт экспорта метрик: `GET /metrics`

### Error tracking в Sentry

Sentry подключен для сбора исключений в HTTP-обработчиках и бизнес-логике.

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Укажите настройки в `.env`:
```env
SENTRY_ENABLED=true
SENTRY_DSN=https://<key>@o<org>.ingest.sentry.io/<project_id>
SENTRY_TRACES_SAMPLE_RATE=1.0
SENTRY_ENVIRONMENT=development
```

3. Перезапустите сервис и спровоцируйте ошибку (например, запрос к несуществующему `item_id`):
```bash
curl -X POST http://localhost:8003/simple_predict \
  -H "Content-Type: application/json" \
  -d '{"item_id": 999999}'
```

Исключения (`ModelNotAvailableError`, `PredictionError`, `AdNotFoundError`,
`ModerationResultNotFoundError` и неожиданные ошибки) отправляются в Sentry через
`sentry_sdk.capture_exception(...)`.

### Скриншот Sentry с исключением
Пример проблемы с локальным self-hosted запуском Sentry через Podman:
![Sentry fail](imgs/sentry_error.png)

### Настройка Prometheus

Файл `prometheus.yml` в корне проекта:

```yaml
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: "moderation-service"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["host.docker.internal:8003"]
```

Если приложение запущено в Docker, используйте `targets: ["<app_service_name>:<port>"]`.

### Минимальный дашборд Grafana (6 панелей)

Запросы для тестирования выполнялись через `curl`.

![Grafana dashboard](imgs/graphana_dash.png)

Мониторинг Kafka/DLQ и диагностические сценарии по воркерам вынесены в:
[`app/workers/README.md`](app/workers/README.md)
