class ServiceException(Exception):
    """Базовое исключение для сервисного слоя"""
    pass


class ModelNotAvailableError(ServiceException):
    """Исключение, когда ML-модель недоступна"""
    pass


class PredictionError(ServiceException):
    """Исключение при ошибке предсказания"""
    pass


class AdNotFoundError(ServiceException):
    """Исключение, когда объявление не найдено"""
    pass


class ModerationResultNotFoundError(ServiceException):
    """Исключение, когда задача модерации не найдена"""
    pass


class InvalidCredentialsError(ServiceException):
    """Неверный логин или пароль"""
    pass


class AccountBlockedError(ServiceException):
    """Аккаунт заблокирован"""
    pass


class AuthenticationRequiredError(ServiceException):
    """Требуется авторизация"""
    pass