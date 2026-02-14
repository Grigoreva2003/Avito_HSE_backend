import logging
import numpy as np
from pathlib import Path
from typing import Optional
from sklearn.linear_model import LogisticRegression
from threading import Lock

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Синглтон для управления ML-моделью.
    
    Инкапсулирует:
    - Загрузку/сохранение модели
    - Обучение модели
    - Нормализацию признаков
    - Предсказание
    """
    
    _instance: Optional['ModelManager'] = None
    _lock: Lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Инициализация выполняется только один раз"""
        if self._initialized:
            return
        
        self._model: Optional[LogisticRegression] = None
        self._model_path: str = "model.pkl"
        self._initialized = True
        logger.info("ModelManager инициализирован")
    
    def load_model(self, path: Optional[str] = None) -> None:
        """
        Загружает модель из файла или обучает новую.
        
        Args:
            path: Путь к файлу модели (по умолчанию "model.pkl")
        """
        if path:
            self._model_path = path
        
        model_path = Path(self._model_path)
        
        if model_path.exists():
            logger.info(f"Загрузка модели из {self._model_path}")
            self._model = self._load_from_file(self._model_path)
            logger.info("Модель успешно загружена")
        else:
            logger.info(f"Файл модели не найден. Обучаем новую модель...")
            self._model = self._train_model()
            self._save_to_file(self._model, self._model_path)
            logger.info(f"Модель обучена и сохранена в {self._model_path}")
    
    def is_available(self) -> bool:
        """Проверка доступности модели"""
        return self._model is not None
    
    def predict(
        self,
        is_verified_seller: bool,
        images_qty: int,
        description: str,
        category: int
    ) -> tuple[bool, float]:
        """
        Выполняет предсказание нарушения.
        
        Args:
            is_verified_seller: Подтвержденный ли продавец
            images_qty: Количество изображений
            description: Описание товара
            category: Категория товара
            
        Returns:
            tuple[bool, float]: (is_violation, probability)
            
        Raises:
            RuntimeError: Если модель не загружена
        """
        if not self.is_available():
            raise RuntimeError("Модель не загружена")
        
        # Подготовка признаков
        features = self._prepare_features(
            is_verified_seller=is_verified_seller,
            images_qty=images_qty,
            description=description,
            category=category
        )
        
        # Предсказание
        prediction = self._model.predict(features)[0]
        probability = self._model.predict_proba(features)[0][1]
        
        return bool(prediction), float(probability)
    
    def _prepare_features(
        self,
        is_verified_seller: bool,
        images_qty: int,
        description: str,
        category: int
    ) -> np.ndarray:
        """
        Преобразует входные данные в признаки для модели (PRIVATE).
        
        Args:
            is_verified_seller: Подтвержденный ли продавец
            images_qty: Количество изображений
            description: Описание товара
            category: Категория товара
            
        Returns:
            np.ndarray: Массив признаков shape (1, 4)
        """
        features = np.array([[
            1.0 if is_verified_seller else 0.0,  # is_verified_seller
            min(images_qty / 10.0, 1.0),  # images_qty нормализовано (макс 10)
            min(len(description) / 1000.0, 1.0),  # description_length нормализовано (макс 1000)
            category / 100.0  # category нормализовано
        ]])
        
        return features
    
    def _train_model(self) -> LogisticRegression:
        """
        Обучает модель на синтетических данных (PRIVATE).
        
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
        
        logger.info(f"Модель обучена. Accuracy: {model.score(X, y):.4f}")
        return model
    
    def _save_to_file(self, model: LogisticRegression, path: str) -> None:
        """Сохраняет модель в файл (PRIVATE)"""
        import pickle
        try:
            with open(path, "wb") as f:
                pickle.dump(model, f)
            logger.info(f"Модель сохранена в {path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении модели: {e}")
            raise
    
    def _load_from_file(self, path: str) -> LogisticRegression:
        """Загружает модель из файла (PRIVATE)"""
        import pickle
        try:
            with open(path, "rb") as f:
                model = pickle.load(f)
            return model
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели: {e}")
            raise
    
    def unload(self) -> None:
        """Выгружает модель из памяти"""
        self._model = None
        logger.info("Модель выгружена из памяти")


# Глобальная функция для получения экземпляра
def get_model_manager() -> ModelManager:
    """Получить экземпляр ModelManager (синглтон)"""
    return ModelManager()
