"""
Модуль для работы с ML-моделью модерации объявлений.
"""
import numpy as np
from sklearn.linear_model import LogisticRegression
import pickle
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def train_model() -> LogisticRegression:
    """
    Обучает простую модель на синтетических данных.

    Признаки:
        - is_verified_seller (0.0 или 1.0)
        - images_qty (нормализовано: /10)
        - description_length (нормализовано: /1000)
        - category (нормализовано: /100)

    Returns:
        LogisticRegression: Обученная модель
    """
    logger.info("Начинается обучение модели на синтетических данных...")

    np.random.seed(42)
    # Признаки: [is_verified_seller, images_qty, description_length, category]
    X = np.random.rand(1000, 4)
    # Целевая переменная: 1 = нарушение, 0 = нет нарушения
    y = (X[:, 0] < 0.3) & (X[:, 1] < 0.2)
    y = y.astype(int)

    model = LogisticRegression(random_state=42)
    model.fit(X, y)

    logger.info(f"Модель обучена. Accuracy на обучающей выборке: {model.score(X, y):.4f}")
    return model


def save_model(model: LogisticRegression, path: str = "model.pkl") -> None:
    """
    Сохраняет модель в файл.

    Args:
        model: Обученная модель
        path: Путь для сохранения модели
    """
    try:
        with open(path, "wb") as f:
            pickle.dump(model, f)
        logger.info(f"Модель успешно сохранена в {path}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении модели: {e}")
        raise


def load_model(path: str = "model.pkl") -> LogisticRegression:
    """
    Загружает модель из файла.

    Args:
        path: Путь к файлу с моделью

    Returns:
        LogisticRegression: Загруженная модель

    Raises:
        FileNotFoundError: Если файл модели не найден
    """
    try:
        with open(path, "rb") as f:
            model = pickle.load(f)
        logger.info(f"Модель успешно загружена из {path}")
        return model
    except FileNotFoundError:
        logger.warning(f"Файл модели {path} не найден")
        raise
    except Exception as e:
        logger.error(f"Ошибка при загрузке модели: {e}")
        raise


def get_or_create_model(path: str = "model.pkl") -> LogisticRegression:
    """
    Загружает модель из файла, либо обучает новую, если файл не существует.

    Args:
        path: Путь к файлу с моделью

    Returns:
        LogisticRegression: Готовая к использованию модель
    """
    model_path = Path(path)

    if model_path.exists():
        logger.info(f"Файл модели найден: {path}")
        return load_model(path)
    else:
        logger.info(f"Файл модели не найден. Обучаем новую модель...")
        model = train_model()
        save_model(model, path)
        return model


def prepare_features(
    is_verified_seller: bool,
    images_qty: int,
    description: str,
    category: int
) -> np.ndarray:
    """
    Преобразует входные данные в признаки для модели.

    Args:
        is_verified_seller: Подтвержденный ли продавец
        images_qty: Количество изображений
        description: Описание товара
        category: Категория товара

    Returns:
        np.ndarray: Массив признаков shape (1, 4)
    """
    features = np.array([[
        1.0 if is_verified_seller else 0.0,
        min(images_qty / 10.0, 1.0),  # images_qty нормализовано (макс 10)
        min(len(description) / 1000.0, 1.0),  # description_length нормализовано (макс 1000)
        category / 100.0  # category нормализовано
    ]])

    return features
