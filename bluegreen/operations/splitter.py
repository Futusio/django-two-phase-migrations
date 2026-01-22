"""
OperationSplitter - центральный класс для разделения операций на blue/green фазы.
"""
from typing import List, Tuple, Optional
from django.db.migrations.operations.base import Operation

from .base import OperationStrategy
from .strategies import (
    ModelStrategy,
    FieldStrategy,
    IndexStrategy,
    ConstraintStrategy,
)
from ..constants import IMPOSSIBLE_OPERATIONS


class OperationSplitter:
    """
    Разделяет список операций миграции на blue и green фазы.
    
    Использует набор стратегий для обработки различных типов операций.
    """
    
    def __init__(self, app_label: str):
        """
        Инициализирует splitter для конкретного приложения.
        
        Args:
            app_label: Метка Django приложения
        """
        self.app_label = app_label
        self.strategies: List[OperationStrategy] = [
            ModelStrategy(),
            FieldStrategy(),
            IndexStrategy(),
            ConstraintStrategy(),
        ]
    
    def split_operation(
        self,
        operation: Operation
    ) -> Tuple[Tuple[Operation, ...], Tuple[Optional[Operation], ...]]:
        """
        Разделяет одну операцию на blue/green фазы.
        
        Args:
            operation: Операция для разделения
            
        Returns:
            Кортеж (blue_operations, green_operations)
            
        Examples:
            >>> splitter = OperationSplitter('myapp')
            >>> blue, green = splitter.split_operation(CreateModel(...))
            >>> blue
            (CreateModel(...),)
            >>> green
            (None,)
        """
        # Проверяем невозможные операции
        if type(operation) in IMPOSSIBLE_OPERATIONS:
            # Возвращаем как есть для дальнейшей обработки
            return (operation,), (None,)
        
        # Ищем подходящую стратегию
        for strategy in self.strategies:
            if strategy.can_handle(operation):
                return strategy.split(operation, self.app_label)
        
        # Неизвестная операция - в blue фазу
        return (operation,), (None,)
    
    def split_operations(
        self,
        operations: List[Operation]
    ) -> Tuple[List[Operation], List[Operation]]:
        """
        Разделяет список операций на blue и green списки.
        
        Args:
            operations: Список операций миграции
            
        Returns:
            Кортеж (blue_list, green_list) с отфильтрованными None
            
        Examples:
            >>> splitter = OperationSplitter('myapp')
            >>> operations = [CreateModel(...), DeleteModel(...)]
            >>> blue, green = splitter.split_operations(operations)
            >>> len(blue)  # CreateModel в blue
            1
            >>> len(green)  # DeleteModel в green
            1
        """
        blue_ops = []
        green_ops = []
        
        for operation in operations:
            blue, green = self.split_operation(operation)
            blue_ops.extend(op for op in blue if op is not None)
            green_ops.extend(op for op in green if op is not None)
        
        return blue_ops, green_ops
    
    def detect_impossible_operations(
        self,
        operations: List[Operation]
    ) -> List[Operation]:
        """
        Находит операции, которые невозможно разделить на blue/green.
        
        Args:
            operations: Список операций для проверки
            
        Returns:
            Список невозможных операций
            
        Examples:
            >>> splitter = OperationSplitter('myapp')
            >>> ops = [CreateModel(...), AlterField(...)]
            >>> impossible = splitter.detect_impossible_operations(ops)
            >>> len(impossible)
            1  # AlterField невозможно разделить
        """
        return [
            op for op in operations
            if type(op) in IMPOSSIBLE_OPERATIONS
        ]

