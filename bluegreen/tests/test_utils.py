"""
Тесты для вспомогательных утилит (utils.py).
"""
from django.test import TestCase
from django.db import models

from bluegreen.utils import (
    get_model_safely,
    get_field_by_name,
    get_index_by_name,
    quote_identifier,
    quote_identifiers,
    format_operation_name,
)
from bluegreen.exceptions import ModelNotFoundError, FieldNotFoundError, IndexNotFoundError
from bluegreen.models import BGTestModel  # Используем существующую тестовую модель


class GetModelSafelyTest(TestCase):
    """Тесты для get_model_safely()"""
    
    def test_get_existing_model(self):
        """✅ Получение существующей модели"""
        model = get_model_safely('bluegreen', 'BGTestModel')
        self.assertEqual(model, BGTestModel)
        self.assertEqual(model._meta.db_table, 'bluegreen_bgtestmodel')
    
    def test_get_nonexistent_model_raises_error(self):
        """✅ ModelNotFoundError для несуществующей модели"""
        with self.assertRaises(ModelNotFoundError) as cm:
            get_model_safely('bluegreen', 'NonExistentModel')
        
        self.assertIn('NonExistentModel', str(cm.exception))
        self.assertIn('bluegreen', str(cm.exception))


class GetFieldByNameTest(TestCase):
    """Тесты для get_field_by_name()"""
    
    def test_get_existing_field(self):
        """✅ Получение существующего поля"""
        field = get_field_by_name(BGTestModel, 'chat')
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.name, 'chat')
    
    def test_get_nonexistent_field_raises_error(self):
        """✅ FieldNotFoundError для несуществующего поля"""
        with self.assertRaises(FieldNotFoundError) as cm:
            get_field_by_name(BGTestModel, 'nonexistent_field')
        
        self.assertIn('nonexistent_field', str(cm.exception))
        self.assertIn('BGTestModel', str(cm.exception))


class GetIndexByNameTest(TestCase):
    """Тесты для get_index_by_name()"""
    
    def test_get_nonexistent_index_raises_error(self):
        """✅ IndexNotFoundError для несуществующего индекса"""
        with self.assertRaises(IndexNotFoundError) as cm:
            get_index_by_name(BGTestModel, 'nonexistent_index')
        
        self.assertIn('nonexistent_index', str(cm.exception))
        self.assertIn('BGTestModel', str(cm.exception))


class QuoteIdentifierTest(TestCase):
    """Тесты для quote_identifier()"""
    
    def test_quote_single_identifier(self):
        """✅ Квотирование одного идентификатора"""
        quoted = quote_identifier('my_table')
        # Результат зависит от БД, но не должен быть пустым и должен содержать имя
        self.assertIn('my_table', quoted)
        self.assertTrue(len(quoted) >= len('my_table'))
    
    def test_quote_multiple_identifiers(self):
        """✅ Квотирование нескольких идентификаторов"""
        table, col1, col2 = quote_identifiers('users', 'email', 'name')
        
        self.assertIn('users', table)
        self.assertIn('email', col1)
        self.assertIn('name', col2)
    
    def test_quote_identifiers_returns_tuple(self):
        """✅ quote_identifiers возвращает кортеж"""
        result = quote_identifiers('a', 'b', 'c')
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)


class FormatOperationNameTest(TestCase):
    """Тесты для format_operation_name()"""
    
    def test_format_create_model(self):
        """✅ Форматирование CreateModel"""
        from django.db.migrations.operations import CreateModel
        
        op = CreateModel(
            name='TestModel',
            fields=[('id', models.AutoField(primary_key=True))],
        )
        
        formatted = format_operation_name(op)
        self.assertIn('CreateModel', formatted)
        self.assertIn('TestModel', formatted)
    
    def test_format_add_field(self):
        """✅ Форматирование AddField"""
        from django.db.migrations.operations import AddField
        
        op = AddField(
            model_name='testmodel',
            name='email',
            field=models.EmailField(),
        )
        
        formatted = format_operation_name(op)
        self.assertIn('AddField', formatted)
        self.assertIn('testmodel', formatted)
        self.assertIn('email', formatted)
    
    def test_format_unknown_operation(self):
        """✅ Форматирование неизвестной операции"""
        from django.db.migrations.operations import RunPython
        
        op = RunPython(code=lambda apps, schema_editor: None)
        
        formatted = format_operation_name(op)
        self.assertEqual(formatted, 'RunPython')

