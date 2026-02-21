# Асинхронная обработка и воркеры

## Архитектура

```
┌─────────┐  POST /async_predict   ┌──────────┐  Kafka Queue     ┌────────────┐
│ Client  │ ─────────────────────► │ FastAPI  │ ──────────────► │ Worker     │
└─────────┘                        └──────────┘                 └─────┬──────┘
                                                                      │
    ↑                                                                 ▼
    │                                                          ┌──────────────┐
    │                                                          │ PostgreSQL   │
    │                                                          │ + ML Model   │
    │                                                          └──────────────┘
    │                                                                 │
    │                                                                 ▼
    └──────── GET /moderation_result/{task_id} ◄──────────────────────
```

## Запуск компонентов

```bash
# Терминал 1: Docker инфраструктура
docker-compose up -d

# Терминал 2: FastAPI
python3.11 main.py

# Терминал 3: Worker
python3.11 -m app.workers.moderation_worker

# Терминал 4: DLQ Monitor (опционально)
python3.11 -m app.workers.dlq_monitor
```

## Workflow

1. Клиент отправляет `POST /async_predict` с `item_id`
2. API создает запись в `moderation_results` (`status=pending`)
3. API отправляет сообщение в Kafka (`task_id` + `item_id`)
4. API возвращает `task_id`
5. Воркер получает сообщение из Kafka
6. Воркер загружает объявление из БД
7. Воркер запускает ML-модель
8. Воркер обновляет `moderation_results` (`status=completed` или `failed`)
9. Клиент опрашивает `GET /moderation_result/{task_id}`

## Retry и DLQ

- Максимум попыток: `3`
- Задержка между попытками: экспоненциальная, `5 * 2^retry_count` секунд
- Permanent ошибки: сразу в DLQ
- Temporary ошибки: retry, затем DLQ при исчерпании попыток

Сообщения с ошибками отправляются в топик `moderation_dlq`.

Пример `original_message` в DLQ:

```json
{
  "task_id": 11,
  "item_id": 100,
  "timestamp": "2026-02-16T12:00:00Z",
  "retry_count": 3
}
```

## Мониторинг

```bash
# Kafka Web Console
open http://localhost:8080

# Проверка задач в PostgreSQL
psql -d avito_moderation -c "
  SELECT id, item_id, status, is_violation, probability, created_at, processed_at
  FROM moderation_results
  ORDER BY id DESC
  LIMIT 10;
"
```
