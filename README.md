# Backend разработка
Курс по Backend'у от магистерской программы НИУ ВШЭ в сотрудничестве с Авито

## Автор
Григорьева Василиса, студентка магистратуры НИУ ВШЭ ФКН х Авито "Машинное обучение в цифровом продукте"

## Описание проекта
Сервис модерации объявлений с использованием ML-модели (LogisticRegression) для предсказания нарушений.


### Структура проекта
```
├── main.py              # Точка входа FastAPI с lifespan для загрузки модели
├── model.py             # Работа с ML-моделью (обучение, загрузка, предсказание)
├── models/              # Pydantic модели
│   └── ads.py          # AdRequest и PredictResponse
├── routers/             # API эндпоинты
│   └── ads.py          # POST /predict
├── services/            # Бизнес-логика
├── repositories/        # Работа с данными
├── tests/               # Unit-тесты
│   └── test_ads.py     # Тесты для /predict
└── requirements.txt     # Зависимости
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

При первом запуске автоматически:
- Обучится модель на синтетических данных
- Модель сохранится в файл `model.pkl`
- При последующих запусках модель загрузится из файла

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
- Подготовленные признаки для модели
- Результат предсказания (is_violation, probability)

Пример:
```
INFO - Запрос на предсказание: seller_id=1, item_id=100, is_verified=True...
INFO - Результат предсказания для seller_id=1, item_id=100: is_violation=False, probability=0.1234
```