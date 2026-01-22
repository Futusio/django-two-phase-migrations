"""
Тесты для SQLBuilder - безопасной генерации SQL.
"""
from unittest.mock import Mock
from django.test import TestCase
from django.db.migrations.operations import RunSQL

from bluegreen.sql import SQLBuilder
from bluegreen.utils import quote_identifier


class SQLBuilderTest(TestCase):
    """Тесты для SQLBuilder класса."""

    def setUp(self):
        """Подготовка тестовых данных."""
        # Mock модель с полями
        self.mock_model = Mock()
        self.mock_model._meta.app_label = 'testapp'
        self.mock_model._meta.db_table = 'testapp_user'
        self.mock_model._meta.fields = [
            Mock(column='id', name='id'),
            Mock(column='email', name='email'),
            Mock(column='first_name', name='first_name'),
        ]
        self.mock_model.__name__ = 'User'

    def test_build_insert_select_basic(self):
        """✅ INSERT SELECT генерируется с квотированными идентификаторами."""
        columns = ['id', 'email', 'name']
        
        operation = SQLBuilder.build_insert_select(
            source_table='old_users',
            target_table='new_users',
            columns=columns
        )
        
        self.assertIsInstance(operation, RunSQL)
        sql = operation.sql
        
        # Проверяем что идентификаторы квотированы
        self.assertIn(quote_identifier('old_users'), sql)
        self.assertIn(quote_identifier('new_users'), sql)
        self.assertIn(quote_identifier('id'), sql)
        self.assertIn(quote_identifier('email'), sql)
        self.assertIn(quote_identifier('name'), sql)
        
        # Проверяем структуру SQL
        self.assertIn('INSERT INTO', sql)
        self.assertIn('SELECT', sql)
        self.assertIn('FROM', sql)

    def test_build_insert_select_explicit_columns(self):
        """✅ INSERT SELECT использует явный список колонок (не SELECT *)."""
        columns = ['id', 'email']
        
        operation = SQLBuilder.build_insert_select(
            source_table='table1',
            target_table='table2',
            columns=columns
        )
        
        sql = operation.sql
        
        # Проверяем что НЕ используется SELECT *
        self.assertNotIn('SELECT *', sql)
        
        # Проверяем что колонки перечислены явно
        for col in columns:
            self.assertIn(quote_identifier(col), sql)

    def test_build_update_field_copy_basic(self):
        """✅ UPDATE генерируется с квотированными идентификаторами."""
        operation = SQLBuilder.build_update_field_copy(
            table='users',
            new_column='email_new',
            old_column='email_old'
        )
        
        self.assertIsInstance(operation, RunSQL)
        sql = operation.sql
        
        # Проверяем что идентификаторы квотированы
        self.assertIn(quote_identifier('users'), sql)
        self.assertIn(quote_identifier('email_new'), sql)
        self.assertIn(quote_identifier('email_old'), sql)
        
        # Проверяем структуру SQL
        self.assertIn('UPDATE', sql)
        self.assertIn('SET', sql)

    def test_build_update_field_copy_with_where(self):
        """✅ UPDATE с WHERE условием работает корректно."""
        operation = SQLBuilder.build_update_field_copy(
            table='users',
            new_column='status_new',
            old_column='status_old',
            where_clause='id > 100'
        )
        
        sql = operation.sql
        
        self.assertIn('WHERE', sql)
        self.assertIn('id > 100', sql)

    def test_build_column_list_from_model(self):
        """✅ Список колонок извлекается из модели корректно."""
        columns = SQLBuilder.build_column_list_from_model(self.mock_model)
        
        self.assertEqual(columns, ['id', 'email', 'first_name'])
        self.assertIsInstance(columns, list)

    def test_build_quoted_column_list(self):
        """✅ Список колонок квотируется и объединяется в строку."""
        columns = ['id', 'email', 'name']
        
        result = SQLBuilder.build_quoted_column_list(columns)
        
        # Проверяем что все колонки квотированы
        for col in columns:
            self.assertIn(quote_identifier(col), result)
        
        # Проверяем что используется запятая
        self.assertIn(',', result)

    def test_build_table_name(self):
        """✅ Имя таблицы формируется корректно."""
        table_name = SQLBuilder.build_table_name('myapp', 'User')
        
        self.assertEqual(table_name, 'myapp_user')
        
        # Проверяем нормализацию case
        table_name2 = SQLBuilder.build_table_name('myapp', 'PRODUCT')
        self.assertEqual(table_name2, 'myapp_product')

    def test_reverse_sql_is_noop_by_default(self):
        """✅ reverse_sql по умолчанию - noop."""
        operation = SQLBuilder.build_insert_select(
            source_table='t1',
            target_table='t2',
            columns=['id']
        )
        
        self.assertEqual(operation.reverse_sql, RunSQL.noop)

    def test_custom_reverse_sql(self):
        """✅ Можно задать кастомный reverse_sql."""
        custom_reverse = "DROP TABLE old_table;"
        
        operation = SQLBuilder.build_insert_select(
            source_table='t1',
            target_table='t2',
            columns=['id'],
            reverse_sql=custom_reverse
        )
        
        self.assertEqual(operation.reverse_sql, custom_reverse)

    def test_empty_columns_list(self):
        """✅ Пустой список колонок обрабатывается корректно."""
        operation = SQLBuilder.build_insert_select(
            source_table='t1',
            target_table='t2',
            columns=[]
        )
        
        sql = operation.sql
        
        # SQL должен быть сгенерирован, даже с пустым списком
        self.assertIn('INSERT INTO', sql)
        self.assertIn('SELECT', sql)

    def test_special_characters_in_names(self):
        """✅ Спецсимволы в именах таблиц/колонок квотируются."""
        # Имена с дефисами, пробелами и т.д. должны быть заквотированы
        operation = SQLBuilder.build_insert_select(
            source_table='table-with-dashes',
            target_table='table with spaces',
            columns=['column-1', 'column 2']
        )
        
        sql = operation.sql
        
        # Проверяем что все идентификаторы квотированы
        self.assertIn(quote_identifier('table-with-dashes'), sql)
        self.assertIn(quote_identifier('table with spaces'), sql)
        self.assertIn(quote_identifier('column-1'), sql)
        self.assertIn(quote_identifier('column 2'), sql)

