"""
Тесты для валидации схем и безопасности SQL.
"""
import re
from django.test import TestCase


class SchemaValidationTest(TestCase):
    """Тесты валидации схем перед INSERT INTO SELECT"""
    
    def test_insert_select_uses_explicit_columns(self):
        """✅ INSERT INTO SELECT использует явный список колонок"""
        import os
        from bluegreen.management.commands.bluegreen import PatchedMigrationWriter
        
        bluegreen_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'management', 'commands', 'bluegreen.py'
        )
        
        with open(bluegreen_path, 'r') as f:
            content = f.read()
        
        # Ищем паттерн INSERT INTO с явными колонками
        # Должен быть: INSERT INTO table (col1, col2) SELECT col1, col2 FROM
        # Не должно быть: INSERT INTO table SELECT * FROM
        
        # Проверяем что нет SELECT *
        select_star_pattern = r'INSERT INTO.*SELECT \* FROM'
        matches = re.finditer(select_star_pattern, content, re.IGNORECASE)
        
        issues = []
        for match in matches:
            # Проверяем что это не в комментарии
            start = max(0, match.start() - 100)
            context = content[start:match.end()]
            if '#' not in context.split('\n')[-1]:
                issues.append(match.group())
        
        if issues:
            self.fail(
                f"Найдены небезопасные INSERT SELECT без явных колонок:\n" +
                "\n".join(f"  - {issue}" for issue in issues)
            )
    
    def test_insert_select_uses_sqlbuilder(self):
        """✅ INSERT SELECT использует SQLBuilder для генерации SQL"""
        import os
        
        # После рефакторинга логика SQL генерации перенесена в strategies.py
        strategies_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'operations', 'strategies.py'
        )
        
        with open(strategies_path, 'r') as f:
            content = f.read()
        
        # Проверяем что используется SQLBuilder в strategies
        patterns_to_find = [
            'SQLBuilder',  # Импорт или использование SQLBuilder
            'build_column_list_from_model', # Метод SQLBuilder
            'build_insert_select',  # Метод SQLBuilder для INSERT SELECT
        ]
        
        for pattern in patterns_to_find:
            if pattern not in content:
                self.fail(
                    f"Не найден SQLBuilder в strategies.py: отсутствует '{pattern}' в коде.\n"
                    f"INSERT INTO SELECT должен генерироваться через SQLBuilder."
                )


class TransactionSafetyTest(TestCase):
    """Тесты для транзакций"""
    
    def test_migrate_uses_transaction_for_data_migration(self):
        """✅ migrate.py использует транзакции для переноса данных"""
        import os
        
        migrate_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'management', 'commands', 'migrate.py'
        )
        
        with open(migrate_path, 'r') as f:
            content = f.read()
        
        # Проверяем что есть transaction.atomic
        if 'transaction.atomic' not in content:
            self.fail(
                "migrate.py не использует transaction.atomic() для переноса данных.\n"
                "Критические операции должны быть обернуты в транзакции."
            )
        
        # Проверяем что transaction импортирован
        if 'from django.db import' in content and 'transaction' not in content[:1000]:
            self.fail("transaction не импортирован из django.db")
    
    def test_sql_builder_uses_quote_identifier(self):
        """✅ SQLBuilder использует quote_identifier для безопасности SQL"""
        import os
        
        # После рефакторинга вся логика SQL в sql/builder.py
        sqlbuilder_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'sql', 'builder.py'
        )
        
        with open(sqlbuilder_path, 'r') as f:
            content = f.read()
        
        # SQLBuilder должен использовать quote_identifier
        if 'quote_identifier' not in content:
            self.fail(
                "quote_identifier не используется в SQLBuilder.\n"
                "Для защиты от SQL-инъекций нужно квотировать идентификаторы."
            )


class SQLReversibilityTest(TestCase):
    """Тесты для обратимости SQL операций"""
    
    def test_sqlbuilder_generates_reversible_sql(self):
        """✅ SQLBuilder генерирует RunSQL с reverse_sql для отката"""
        from bluegreen.sql import SQLBuilder
        from django.db.migrations.operations import RunSQL
        
        # Проверяем что SQLBuilder.build_insert_select генерирует RunSQL с reverse_sql
        columns = ['id', 'name']
        operation = SQLBuilder.build_insert_select(
            source_table='old_table',
            target_table='new_table',
            columns=columns
        )
        
        self.assertIsInstance(operation, RunSQL)
        # Проверяем что reverse_sql установлен (по умолчанию RunSQL.noop)
        self.assertIsNotNone(operation.reverse_sql)
        self.assertEqual(operation.reverse_sql, RunSQL.noop)
        
        # Проверяем что можно задать кастомный reverse_sql
        custom_reverse = "DELETE FROM old_table;"
        operation_custom = SQLBuilder.build_insert_select(
            source_table='old_table',
            target_table='new_table',
            columns=columns,
            reverse_sql=custom_reverse
        )
        self.assertEqual(operation_custom.reverse_sql, custom_reverse)

