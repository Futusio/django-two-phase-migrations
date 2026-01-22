"""
Базовый класс для стратегий разделения операций.
"""
from abc import ABC, abstractmethod
from typing import Tuple, Optional
from django.db.migrations.operations.base import Operation


class OperationStrategy(ABC):
    """
    Базовая стратегия для разделения миграционной операции на blue/green фазы.
    
    Каждая стратегия отвечает за определенный тип операций (модели, поля, индексы и т.д.)
    """
    
    @abstractmethod
    def can_handle(self, operation: Operation) -> bool:
        """
        Проверяет, может ли стратегия обработать данную операцию.
        
        Args:
            operation: Операция миграции Django
            
        Returns:
            True если стратегия может обработать операцию
        """
        pass
    
    @abstractmethod
    def split(
        self,
        operation: Operation,
        app_label: str
    ) -> Tuple[Tuple[Operation, ...], Tuple[Optional[Operation], ...]]:
        """
        Разделяет операцию на blue и green фазы.
        
        Args:
            operation: Операция для разделения
            app_label: Метка приложения Django
            
        Returns:
            Кортеж из двух кортежей: (blue_operations, green_operations)
            None в кортеже означает отсутствие операции в данной фазе
            
        Examples:
            >>> strategy.split(CreateModel(...), 'myapp')
            ((CreateModel(...),), (None,))
            
            >>> strategy.split(DeleteModel(...), 'myapp')
            ((None,), (DeleteModel(...),))
        """
        pass

