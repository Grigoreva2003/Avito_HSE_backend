# Тестирование

В проекте используется разделение тестов:

- `tests/unit` — API и бизнес-логика с моками (без реальных хранилищ)
- `tests/integration` — интеграционные тесты
- `tests/integration/postgresql` — интеграционные тесты репозиториев PostgreSQL

Маркер интеграционных тестов: `@pytest.mark.integration`.

## Запуск

### Все тесты
```bash
pytest tests/ -v
```

### Только unit-тесты
```bash
pytest -m "not integration" -v
```

### Только integration-тесты
```bash
pytest -m integration -v
```

### Только PostgreSQL integration-тесты
```bash
pytest tests/integration/postgresql -m integration -v
```

### Только Redis integration-тесты
```bash
# Поднимите Redis (или весь docker-compose)
docker-compose up -d redis

# Тесты работы кэша в Redis
pytest tests/integration/test_prediction_cache_integration.py -m integration -v
```

## Примечания

- Для integration-тестов PostgreSQL должна быть доступна БД и применены миграции.
- Для Redis integration-тестов должен быть поднят Redis (`localhost:6379` по умолчанию).
