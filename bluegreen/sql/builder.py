"""
SQLBuilder - безопасная генерация SQL для bluegreen миграций.
"""
from typing import List, Optional
from django.db.models import Model
from django.db.migrations.operations import RunSQL

from ..utils import quote_identifier


class SQLBuilder:
    """
    Построитель SQL запросов для bluegreen миграций.
    
    Все методы автоматически квотируют идентификаторы для защиты от SQL-инъекций.
    """
    
    @staticmethod
    def build_insert_select(
        source_table: str,
        target_table: str,
        columns: List[str],
        reverse_sql: Optional[str] = None
    ) -> RunSQL:
        """
        Генерирует INSERT INTO ... SELECT с явным списком колонок.
        
        Args:
            source_table: Исходная таблица (откуда копируем)
            target_table: Целевая таблица (куда копируем)
            columns: Список имен колонок для копирования
            reverse_sql: SQL для отката (опционально)
            
        Returns:
            RunSQL операция с квотированными идентификаторами
            
        Examples:
            >>> builder = SQLBuilder()
            >>> op = builder.build_insert_select(
            ...     'old_users', 'new_users', ['id', 'email', 'name']
            ... )
            >>> # Генерирует: INSERT INTO "old_users" (id, email, name) 
            >>> #             SELECT id, email, name FROM "new_users"
        """
        # Квотируем таблицы
        source_quoted = quote_identifier(source_table)
        target_quoted = quote_identifier(target_table)
        
        # Квотируем колонки
        columns_quoted = [quote_identifier(col) for col in columns]
        columns_list = ', '.join(columns_quoted)
        
        # Формируем SQL
        sql = (
            f"INSERT INTO {source_quoted} ({columns_list}) "
            f"SELECT {columns_list} FROM {target_quoted}"
        )
        
        return RunSQL(sql, reverse_sql=reverse_sql or RunSQL.noop)
    
    @staticmethod
    def build_update_field_copy(
        table: str,
        new_column: str,
        old_column: str,
        where_clause: Optional[str] = None,
        reverse_sql: Optional[str] = None
    ) -> RunSQL:
        """
        Генерирует UPDATE для копирования значений из одной колонки в другую.
        
        Args:
            table: Имя таблицы
            new_column: Новая колонка (куда копируем)
            old_column: Старая колонка (откуда копируем)
            where_clause: Дополнительное условие WHERE (опционально)
            reverse_sql: SQL для отката (опционально)
            
        Returns:
            RunSQL операция с квотированными идентификаторами
            
        Examples:
            >>> builder = SQLBuilder()
            >>> op = builder.build_update_field_copy(
            ...     'users', 'email_new', 'email_old'
            ... )
            >>> # Генерирует: UPDATE "users" SET "email_new" = "email_old"
        """
        table_quoted = quote_identifier(table)
        new_col_quoted = quote_identifier(new_column)
        old_col_quoted = quote_identifier(old_column)
        
        sql = f"UPDATE {table_quoted} SET {new_col_quoted} = {old_col_quoted}"
        
        if where_clause:
            sql += f" WHERE {where_clause}"
        
        return RunSQL(sql, reverse_sql=reverse_sql or RunSQL.noop)
    
    @staticmethod
    def build_column_list_from_model(model: type[Model]) -> List[str]:
        """
        Получает список имен колонок из модели.
        
        Args:
            model: Класс модели Django
            
        Returns:
            Список имен колонок (column names, не field names)
            
        Examples:
            >>> columns = SQLBuilder.build_column_list_from_model(User)
            >>> columns
            ['id', 'email', 'first_name', 'last_name', 'created_at']
        """
        return [field.column for field in model._meta.fields]
    
    @staticmethod
    def build_quoted_column_list(columns: List[str]) -> str:
        """
        Квотирует список колонок и объединяет в строку.
        
        Args:
            columns: Список имен колонок
            
        Returns:
            Строка с квотированными колонками через запятую
            
        Examples:
            >>> SQLBuilder.build_quoted_column_list(['id', 'email', 'name'])
            '"id", "email", "name"'  # для PostgreSQL
        """
        return ', '.join(quote_identifier(col) for col in columns)
    
    @staticmethod
    def build_table_name(app_label: str, model_name: str) -> str:
        """
        Формирует имя таблицы из app_label и model_name.
        
        Args:
            app_label: Название приложения
            model_name: Название модели (lower case)
            
        Returns:
            Имя таблицы в формате app_model
            
        Examples:
            >>> SQLBuilder.build_table_name('myapp', 'user')
            'myapp_user'
        """
        return f"{app_label}_{model_name.lower()}"

