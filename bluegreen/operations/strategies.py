"""
Конкретные стратегии для разных типов операций миграций.
"""
from typing import Tuple, Optional
from django.db.migrations.operations.base import Operation
from django.db.migrations.operations import (
    CreateModel, DeleteModel, RenameModel,
    AddField, RemoveField, RenameField,
    AddIndex, RemoveIndex, RenameIndex,
    AddConstraint, RemoveConstraint
)

from .base import OperationStrategy
from ..fields import CreateModelPatched, AddFieldPatched, AddIndexPatched
from ..utils import get_model_safely, get_field_by_name, get_index_by_name
from ..sql import SQLBuilder


class ModelStrategy(OperationStrategy):
    """Стратегия для операций с моделями (Create/Delete/Rename)."""
    
    def can_handle(self, operation: Operation) -> bool:
        """Проверяет, является ли операция моделью."""
        return isinstance(operation, (CreateModel, DeleteModel, RenameModel))
    
    def split(
        self,
        operation: Operation,
        app_label: str
    ) -> Tuple[Tuple[Operation, ...], Tuple[Optional[Operation], ...]]:
        """Разделяет операции с моделями на blue/green."""
        if isinstance(operation, CreateModel):
            # Blue: создаем модель, Green: ничего
            return (operation,), (None,)
        
        elif isinstance(operation, DeleteModel):
            # Blue: ничего, Green: удаляем модель
            return (None,), (operation,)
        
        elif isinstance(operation, RenameModel):
            # Blue: создаем новую + копируем данные, Green: удаляем старую
            model = get_model_safely(app_label, operation.new_name)
            
            add_operation = CreateModelPatched(
                name=model.__name__,
                fields=model._meta.fields,
                old_name=operation.old_name
            )
            drop_operation = DeleteModel(name=operation.old_name)
            old_table = f"{model._meta.app_label}_{operation.old_name_lower}"
            
            # Используем SQLBuilder для безопасной генерации SQL
            columns = SQLBuilder.build_column_list_from_model(model)
            run_sql = SQLBuilder.build_insert_select(
                source_table=old_table,
                target_table=model._meta.db_table,
                columns=columns
            )
            
            return (add_operation, run_sql), (drop_operation,)
        
        return (operation,), (None,)


class FieldStrategy(OperationStrategy):
    """Стратегия для операций с полями (Add/Remove/Rename)."""
    
    def can_handle(self, operation: Operation) -> bool:
        """Проверяет, является ли операция полем."""
        return isinstance(operation, (AddField, RemoveField, RenameField))
    
    def split(
        self,
        operation: Operation,
        app_label: str
    ) -> Tuple[Tuple[Operation, ...], Tuple[Optional[Operation], ...]]:
        """Разделяет операции с полями на blue/green."""
        if isinstance(operation, AddField):
            # Blue: добавляем поле, Green: ничего
            return (operation,), (None,)
        
        elif isinstance(operation, RemoveField):
            # Blue: ничего, Green: удаляем поле
            return (None,), (operation,)
        
        elif isinstance(operation, RenameField):
            # Blue: добавляем новое + копируем данные, Green: удаляем старое
            model = get_model_safely(app_label, operation.model_name)
            field = get_field_by_name(model, operation.new_name)
            
            add_operation = AddFieldPatched(
                model_name=model.__name__.lower(),
                name=operation.new_name,
                old_name=operation.old_name,
                field=field.clone(),
                preserve_default=True
            )
            drop_operation = RemoveField(
                model_name=model.__name__.lower(),
                name=operation.old_name,
            )
            
            # Используем SQLBuilder для UPDATE
            run_sql = SQLBuilder.build_update_field_copy(
                table=model._meta.db_table,
                new_column=operation.new_name,
                old_column=operation.old_name
            )
            
            return (add_operation, run_sql), (drop_operation,)
        
        return (operation,), (None,)


class IndexStrategy(OperationStrategy):
    """Стратегия для операций с индексами (Add/Remove/Rename)."""
    
    def can_handle(self, operation: Operation) -> bool:
        """Проверяет, является ли операция индексом."""
        return isinstance(operation, (AddIndex, RemoveIndex, RenameIndex))
    
    def split(
        self,
        operation: Operation,
        app_label: str
    ) -> Tuple[Tuple[Operation, ...], Tuple[Optional[Operation], ...]]:
        """Разделяет операции с индексами на blue/green."""
        if isinstance(operation, AddIndex):
            # Blue: добавляем индекс, Green: ничего
            return (operation,), (None,)
        
        elif isinstance(operation, RemoveIndex):
            # Blue: ничего, Green: удаляем индекс
            return (None,), (operation,)
        
        elif isinstance(operation, RenameIndex):
            # Blue: создаем новый индекс, Green: удаляем старый
            model = get_model_safely(app_label, operation.model_name)
            index = get_index_by_name(model, operation.new_name)
            
            add_operation = AddIndexPatched(
                model_name=model.__name__.lower(),
                index=index.clone(),
                old_name=operation.old_name
            )
            drop_operation = RemoveIndex(
                model_name=model.__name__.lower(),
                name=operation.old_name,
            )
            
            return (add_operation,), (drop_operation,)
        
        return (operation,), (None,)


class ConstraintStrategy(OperationStrategy):
    """Стратегия для операций с ограничениями (Add/Remove)."""
    
    def can_handle(self, operation: Operation) -> bool:
        """Проверяет, является ли операция ограничением."""
        return isinstance(operation, (AddConstraint, RemoveConstraint))
    
    def split(
        self,
        operation: Operation,
        app_label: str
    ) -> Tuple[Tuple[Operation, ...], Tuple[Optional[Operation], ...]]:
        """Разделяет операции с ограничениями на blue/green."""
        if isinstance(operation, AddConstraint):
            # Blue: добавляем constraint, Green: ничего
            return (operation,), (None,)
        
        elif isinstance(operation, RemoveConstraint):
            # Blue: ничего, Green: удаляем constraint
            return (None,), (operation,)
        
        return (operation,), (None,)

