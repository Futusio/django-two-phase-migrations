"""
SQLValidator - валидация схем и SQL запросов для bluegreen миграций.
"""
from typing import List, Set, Tuple, Optional
from django.db.models import Model

from ..exceptions import SchemaValidationError


class SQLValidator:
    """
    Валидатор SQL и схем для bluegreen миграций.
    
    Проверяет совместимость схем перед выполнением операций переноса данных.
    """
    
    @staticmethod
    def get_common_columns(
        model_from: type[Model],
        model_to: type[Model]
    ) -> List[str]:
        """
        Получает список общих колонок между двумя моделями.
        
        Args:
            model_from: Исходная модель
            model_to: Целевая модель
            
        Returns:
            Список имен колонок, присутствующих в обеих моделях
            
        Examples:
            >>> common = SQLValidator.get_common_columns(OldUser, NewUser)
            >>> common
            ['id', 'email', 'created_at']
        """
        columns_from = {field.column for field in model_from._meta.fields}
        columns_to = {field.column for field in model_to._meta.fields}
        
        common = columns_from & columns_to
        return sorted(list(common))
    
    @staticmethod
    def validate_schema_compatibility(
        source_columns: List[str],
        target_columns: List[str],
        strict: bool = False
    ) -> Tuple[bool, List[str]]:
        """
        Проверяет совместимость схем для INSERT INTO ... SELECT.
        
        Args:
            source_columns: Колонки исходной таблицы
            target_columns: Колонки целевой таблицы
            strict: Строгий режим (все колонки должны совпадать)
            
        Returns:
            Кортеж (совместимы?, список ошибок)
            
        Examples:
            >>> is_valid, errors = SQLValidator.validate_schema_compatibility(
            ...     ['id', 'email'], ['id', 'email', 'name']
            ... )
            >>> is_valid
            True
            >>> errors
            []
        """
        errors = []
        source_set = set(source_columns)
        target_set = set(target_columns)
        
        # Проверяем что все исходные колонки есть в целевой таблице
        missing_in_target = source_set - target_set
        if missing_in_target:
            errors.append(
                f"Columns missing in target table: {', '.join(sorted(missing_in_target))}"
            )
        
        # В строгом режиме проверяем обратное
        if strict:
            missing_in_source = target_set - source_set
            if missing_in_source:
                errors.append(
                    f"Columns missing in source table: {', '.join(sorted(missing_in_source))}"
                )
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_column_list(
        model: type[Model],
        columns: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Проверяет что все колонки существуют в модели.
        
        Args:
            model: Модель Django
            columns: Список имен колонок для проверки
            
        Returns:
            Кортеж (все найдены?, список отсутствующих колонок)
            
        Examples:
            >>> is_valid, missing = SQLValidator.validate_column_list(
            ...     User, ['id', 'email', 'nonexistent']
            ... )
            >>> is_valid
            False
            >>> missing
            ['nonexistent']
        """
        model_columns = {field.column for field in model._meta.fields}
        columns_set = set(columns)
        
        missing = columns_set - model_columns
        
        return len(missing) == 0, sorted(list(missing))
    
    @staticmethod
    def get_column_order(model: type[Model]) -> List[str]:
        """
        Получает упорядоченный список колонок модели.
        
        Важно для INSERT чтобы порядок колонок соответствовал определению модели.
        
        Args:
            model: Модель Django
            
        Returns:
            Упорядоченный список имен колонок
            
        Examples:
            >>> order = SQLValidator.get_column_order(User)
            >>> order
            ['id', 'email', 'first_name', 'last_name', 'created_at']
        """
        return [field.column for field in model._meta.fields]
    
    @staticmethod
    def check_safe_for_insert_select(
        source_model: type[Model],
        target_model: type[Model]
    ) -> None:
        """
        Комплексная проверка безопасности INSERT INTO ... SELECT.
        
        Args:
            source_model: Исходная модель (откуда копируем)
            target_model: Целевая модель (куда копируем)
            
        Raises:
            SchemaValidationError: Если схемы несовместимы
            
        Examples:
            >>> SQLValidator.check_safe_for_insert_select(OldUser, NewUser)
            # Ничего не выбрасывает если безопасно
            
            >>> SQLValidator.check_safe_for_insert_select(User, Product)
            SchemaValidationError: No common columns between models
        """
        common = SQLValidator.get_common_columns(source_model, target_model)
        
        if not common:
            raise SchemaValidationError(
                f"No common columns between {source_model.__name__} "
                f"and {target_model.__name__}"
            )
        
        # Проверяем что общих колонок достаточно (хотя бы 1)
        if len(common) < 1:
            raise SchemaValidationError(
                f"Insufficient common columns between {source_model.__name__} "
                f"and {target_model.__name__}: {len(common)}"
            )

