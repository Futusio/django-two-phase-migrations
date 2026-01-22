"""
Вспомогательные утилиты для bluegreen миграций.
"""
from typing import Optional
from django.apps import apps
from django.db import connection
from django.db.models import Model, Field, Index

from .exceptions import ModelNotFoundError, FieldNotFoundError, IndexNotFoundError
from .constants import MSG_MODEL_NOT_FOUND, MSG_FIELD_NOT_FOUND, MSG_INDEX_NOT_FOUND


def get_model_safely(app_label: str, model_name: str) -> type[Model]:
    """
    Безопасно получает модель из app config.
    
    Args:
        app_label: Название приложения
        model_name: Название модели
        
    Returns:
        Класс модели
        
    Raises:
        ModelNotFoundError: Если модель не найдена
        
    Examples:
        >>> model = get_model_safely('myapp', 'MyModel')
        >>> model._meta.db_table
        'myapp_mymodel'
    """
    try:
        return apps.get_app_config(app_label).get_model(model_name)
    except LookupError as e:
        raise ModelNotFoundError(
            MSG_MODEL_NOT_FOUND.format(model=model_name, app=app_label)
        ) from e


def get_field_by_name(model: type[Model], field_name: str) -> Field:
    """
    Получает поле модели по имени.
    
    Args:
        model: Класс модели
        field_name: Имя поля
        
    Returns:
        Объект поля
        
    Raises:
        FieldNotFoundError: Если поле не найдено
        
    Examples:
        >>> field = get_field_by_name(MyModel, 'email')
        >>> field.get_internal_type()
        'EmailField'
    """
    fields = [f for f in model._meta.fields if f.name == field_name]
    if not fields:
        raise FieldNotFoundError(
            MSG_FIELD_NOT_FOUND.format(field=field_name, model=model.__name__)
        )
    return fields[0]


def get_index_by_name(model: type[Model], index_name: str) -> Index:
    """
    Получает индекс модели по имени.
    
    Args:
        model: Класс модели
        index_name: Имя индекса
        
    Returns:
        Объект индекса
        
    Raises:
        IndexNotFoundError: Если индекс не найден
        
    Examples:
        >>> index = get_index_by_name(MyModel, 'mymodel_email_idx')
        >>> index.fields
        ['email']
    """
    indexes = [idx for idx in model._meta.indexes if idx.name == index_name]
    if not indexes:
        raise IndexNotFoundError(
            MSG_INDEX_NOT_FOUND.format(index=index_name, model=model.__name__)
        )
    return indexes[0]


def quote_identifier(identifier: str) -> str:
    """
    Безопасно квотирует SQL идентификатор.
    
    Обертка над connection.ops.quote_name() для защиты от SQL-инъекций.
    
    Args:
        identifier: Имя таблицы, колонки или другого SQL идентификатора
        
    Returns:
        Квотированный идентификатор (например: "table_name" для PostgreSQL)
        
    Examples:
        >>> quote_identifier('my_table')
        '"my_table"'  # PostgreSQL
        >>> quote_identifier('my_field')
        '`my_field`'  # MySQL
    """
    return connection.ops.quote_name(identifier)


def quote_identifiers(*identifiers: str) -> tuple[str, ...]:
    """
    Квотирует несколько идентификаторов за раз.
    
    Args:
        *identifiers: Произвольное количество идентификаторов
        
    Returns:
        Кортеж квотированных идентификаторов
        
    Examples:
        >>> table, col1, col2 = quote_identifiers('users', 'email', 'name')
        >>> f"SELECT {col1}, {col2} FROM {table}"
        'SELECT "email", "name" FROM "users"'
    """
    return tuple(quote_identifier(ident) for ident in identifiers)


def format_operation_name(operation) -> str:
    """
    Форматирует название операции для вывода.
    
    Args:
        operation: Django migration operation
        
    Returns:
        Читаемое название операции
        
    Examples:
        >>> format_operation_name(CreateModel(name='User', fields=[]))
        'CreateModel: User'
        >>> format_operation_name(AddField(model_name='user', name='email'))
        'AddField: user.email'
    """
    op_name = operation.__class__.__name__
    
    if hasattr(operation, 'name') and hasattr(operation, 'model_name'):
        # Field operations
        return f"{op_name}: {operation.model_name}.{operation.name}"
    elif hasattr(operation, 'name'):
        # Model operations
        return f"{op_name}: {operation.name}"
    elif hasattr(operation, 'model_name'):
        # Other model-related operations
        return f"{op_name}: {operation.model_name}"
    else:
        return op_name

