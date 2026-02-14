# Backend разработка
Курс по Backend'у от магистерской программы НИУ ВШЭ в сотрудничестве с Авито

## Автор
Григорьева Василиса, студентка магистратуры НИУ ВШЭ ФКН х Авито "Машинное обучение в цифровом продукте"

## Описание проекта
Сервис модерации объявлений с использованием ML-модели (LogisticRegression) для предсказания нарушений.

### Архитектура
Проект построен по принципу **многослойной архитектуры** с четким разделением ответственности:

- **HTTP Layer** (routers/) - обработка HTTP запросов, валидация, обработка ошибок
- **Service Layer** (services/) - бизнес-логика модерации
- **ML Layer** (ml/) - работа с ML-моделью (ModelManager - синглтон)

### Структура проекта
```
├── main.py                   # Точка входа FastAPI
├── ml/                       # ML слой
│   ├── __init__.py
│   └── model_manager.py      # инкапсулирует работу с моделью
├── models/                   # Pydantic модели
│   └── ads.py                # AdRequest и PredictResponse
├── routers/                  # HTTP слой
│   └── ads.py                # POST /predict - валидация, вызов сервиса, обработка ошибок
├── services/                 # Бизнес-логика
│   ├── exceptions.py         # Доменные исключения (ModelNotAvailableError, PredictionError)
│   └── moderation.py         # ModerationService - логика предсказания нарушений
├── repositories/             # Работа с данными
├── tests/                    # Unit-тесты
│   ├── conftest.py           # Общие фикстуры (app_client, make_payload)
│   └── test_ads.py           # Тесты для /predict
└── requirements.txt          # Зависимости
```

## Установка и запуск

### 1. Создайте и активируйте виртуальное окружение
```bash
python3 -m venv venv
source venv/bin/activate  # для macOS/Linux
```

### 2. Установите зависимости
```bash
pip install -r requirements.txt
```

### 3. Запустите приложение
```bash
python3 main.py
```

Сервис будет доступен по адресу: `http://localhost:8003`

При первом запуске:
- **ModelManager** (синглтон) автоматически инициализируется
- Обучается модель на синтетических данных
- Модель сохраняется в `model.pkl`
- При последующих запусках модель загружается из файла

## API

### POST /predict
Предсказание нарушений в объявлении.

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
- `422` - Ошибка валидации входных данных
- `503` - ML-модель недоступна
- `500` - Внутренняя ошибка сервера

## Тестирование

### Запуск всех тестов
```bash
pytest tests/ -v
```

### Запуск всех внутри однго модуля
```bash
pytest tests/test_ads.py -v
```

### Запуск конкретного класса тестов
```bash
pytest tests/test_ads.py::TestSuccessfulPredictionViolation -v
```

### Запуск с выводом логов
```bash
pytest tests/test_ads.py -v -s
```


## Логирование
Все запросы и предсказания логируются с уровнем INFO:
- Входные параметры запроса
- Результат предсказания (is_violation, probability)
- Ошибки (на уровне роутера и сервиса)

Пример:
```
INFO - Запрос на предсказание: seller_id=1, item_id=100, is_verified=True...
INFO - Результат предсказания для seller_id=1, item_id=100: is_violation=False, probability=0.1234
```

## Принципы проектирования

**Роутер не знает о модели:**
```python
# Роутер просто создает сервис и вызывает метод
moderation_service = ModerationService()
return moderation_service.predict_violation(ad_data)
```

**Сервис получает модель через синглтон:**
```python
# Сервис обращается к ModelManager
self._model_manager = get_model_manager()
is_violation, probability = self._model_manager.predict(...)
```