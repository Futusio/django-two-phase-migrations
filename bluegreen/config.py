"""
Конфигурация и типы данных для bluegreen миграций.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from django.db.migrations.operations.base import Operation


class MigrationPhase(str, Enum):
    """Фазы bluegreen миграции."""
    BLUE = "blue"
    GREEN = "green"
    BOTH = "both"


class ImpossibleOperationPolicy(str, Enum):
    """Политики обработки невозможных операций."""
    ASK = "ask"  # Спрашивать пользователя (интерактивный режим)
    FAIL = "fail"  # Выбросить ошибку
    IGNORE = "ignore"  # Игнорировать и применить как есть
    SKIP = "skip"  # Пропустить операцию


@dataclass
class SplitResult:
    """
    Результат разделения операции на blue/green фазы.
    
    Attributes:
        blue_operations: Операции для blue фазы
        green_operations: Операции для green фазы
        is_impossible: Флаг невозможности разделения
        reason: Причина невозможности (если is_impossible=True)
    """
    blue_operations: List[Operation] = field(default_factory=list)
    green_operations: List[Operation] = field(default_factory=list)
    is_impossible: bool = False
    reason: Optional[str] = None
    
    def has_blue_operations(self) -> bool:
        """Есть ли операции в blue фазе."""
        return len(self.blue_operations) > 0
    
    def has_green_operations(self) -> bool:
        """Есть ли операции в green фазе."""
        return len(self.green_operations) > 0


@dataclass
class BlueGreenConfig:
    """
    Конфигурация для bluegreen команд.
    
    Attributes:
        phase: Какую фазу применять (blue/green/both)
        non_interactive: Неинтерактивный режим (для CI/CD)
        impossible_policy: Политика обработки невозможных операций
        dry_run: Режим сухого прогона (не применять миграции)
        verbose: Подробный вывод
    """
    phase: MigrationPhase = MigrationPhase.BOTH
    non_interactive: bool = False
    impossible_policy: ImpossibleOperationPolicy = ImpossibleOperationPolicy.ASK
    dry_run: bool = False
    verbose: bool = False

