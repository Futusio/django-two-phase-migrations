"""
Исключения для bluegreen миграций.
"""


class BlueGreenMigrationError(Exception):
    """Базовое исключение для всех ошибок bluegreen миграций."""
    pass


class ImpossibleOperationError(BlueGreenMigrationError):
    """
    Операция не может быть выполнена в формате blue-green.
    
    Например: AlterField, AlterModelTable и другие операции,
    которые изменяют существующие объекты без возможности разделения.
    """
    pass


class SchemaValidationError(BlueGreenMigrationError):
    """
    Ошибка валидации схемы при переносе данных.
    
    Возникает когда схемы source и target таблиц не совместимы
    для INSERT INTO ... SELECT.
    """
    pass


class ModelNotFoundError(BlueGreenMigrationError):
    """Модель не найдена в app config."""
    pass


class FieldNotFoundError(BlueGreenMigrationError):
    """Поле не найдено в модели."""
    pass


class IndexNotFoundError(BlueGreenMigrationError):
    """Индекс не найден в модели."""
    pass


class SQLExecutionError(BlueGreenMigrationError):
    """Ошибка выполнения SQL запроса."""
    pass

