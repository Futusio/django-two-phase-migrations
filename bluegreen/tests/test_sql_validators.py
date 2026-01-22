"""
Тесты для SQLValidator - валидации схем и SQL.
"""
from unittest.mock import Mock
from django.test import TestCase

from bluegreen.sql import SQLValidator
from bluegreen.exceptions import SchemaValidationError


class SQLValidatorTest(TestCase):
    """Тесты для SQLValidator класса."""

    def setUp(self):
        """Подготовка тестовых моделей."""
        # Модель 1 (OldUser)
        self.model1 = Mock()
        self.model1._meta.fields = [
            Mock(column='id', name='id'),
            Mock(column='email', name='email'),
            Mock(column='first_name', name='first_name'),
        ]
        self.model1.__name__ = 'OldUser'
        
        # Модель 2 (NewUser) - расширенная версия
        self.model2 = Mock()
        self.model2._meta.fields = [
            Mock(column='id', name='id'),
            Mock(column='email', name='email'),
            Mock(column='first_name', name='first_name'),
            Mock(column='last_name', name='last_name'),
            Mock(column='created_at', name='created_at'),
        ]
        self.model2.__name__ = 'NewUser'
        
        # Модель 3 (Product) - несовместимая
        self.model3 = Mock()
        self.model3._meta.fields = [
            Mock(column='id', name='id'),
            Mock(column='title', name='title'),
            Mock(column='price', name='price'),
        ]
        self.model3.__name__ = 'Product'

    def test_get_common_columns_basic(self):
        """✅ Общие колонки определяются корректно."""
        common = SQLValidator.get_common_columns(self.model1, self.model2)
        
        self.assertEqual(set(common), {'id', 'email', 'first_name'})
        self.assertIsInstance(common, list)
        
        # Список должен быть отсортирован
        self.assertEqual(common, sorted(common))

    def test_get_common_columns_no_common(self):
        """✅ Для несовместимых моделей возвращается только общее (id)."""
        common = SQLValidator.get_common_columns(self.model1, self.model3)
        
        # Только id общий
        self.assertEqual(common, ['id'])

    def test_validate_schema_compatibility_valid(self):
        """✅ Совместимые схемы проходят валидацию."""
        source = ['id', 'email']
        target = ['id', 'email', 'name']
        
        is_valid, errors = SQLValidator.validate_schema_compatibility(source, target)
        
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])

    def test_validate_schema_compatibility_missing_columns(self):
        """✅ Отсутствующие колонки обнаруживаются."""
        source = ['id', 'email', 'nonexistent']
        target = ['id', 'email']
        
        is_valid, errors = SQLValidator.validate_schema_compatibility(source, target)
        
        self.assertFalse(is_valid)
        self.assertTrue(len(errors) > 0)
        self.assertIn('nonexistent', errors[0])

    def test_validate_schema_compatibility_strict_mode(self):
        """✅ Строгий режим проверяет совпадение всех колонок."""
        source = ['id', 'email']
        target = ['id', 'email', 'name']
        
        # Не строгий режим - OK
        is_valid, errors = SQLValidator.validate_schema_compatibility(
            source, target, strict=False
        )
        self.assertTrue(is_valid)
        
        # Строгий режим - ошибка (name отсутствует в source)
        is_valid, errors = SQLValidator.validate_schema_compatibility(
            source, target, strict=True
        )
        self.assertFalse(is_valid)
        self.assertTrue(len(errors) > 0)

    def test_validate_column_list_all_present(self):
        """✅ Валидация проходит если все колонки есть в модели."""
        columns = ['id', 'email', 'first_name']
        
        is_valid, missing = SQLValidator.validate_column_list(self.model1, columns)
        
        self.assertTrue(is_valid)
        self.assertEqual(missing, [])

    def test_validate_column_list_missing_columns(self):
        """✅ Отсутствующие колонки обнаруживаются."""
        columns = ['id', 'email', 'nonexistent', 'another_missing']
        
        is_valid, missing = SQLValidator.validate_column_list(self.model1, columns)
        
        self.assertFalse(is_valid)
        self.assertEqual(set(missing), {'nonexistent', 'another_missing'})

    def test_get_column_order(self):
        """✅ Порядок колонок соответствует определению модели."""
        order = SQLValidator.get_column_order(self.model2)
        
        self.assertEqual(
            order,
            ['id', 'email', 'first_name', 'last_name', 'created_at']
        )

    def test_check_safe_for_insert_select_valid(self):
        """✅ Безопасная комбинация моделей проходит проверку."""
        # model1 -> model2 безопасно (все колонки model1 есть в model2)
        try:
            SQLValidator.check_safe_for_insert_select(self.model1, self.model2)
        except SchemaValidationError:
            self.fail("check_safe_for_insert_select raised unexpected SchemaValidationError")

    def test_check_safe_for_insert_select_partially_compatible(self):
        """✅ Частично совместимые модели проходят (есть общие колонки)."""
        # model1 -> model3: только id общий, но это достаточно
        try:
            SQLValidator.check_safe_for_insert_select(self.model1, self.model3)
        except SchemaValidationError:
            self.fail("check_safe_for_insert_select raised unexpected SchemaValidationError")

    def test_check_safe_for_insert_select_no_common_columns(self):
        """✅ Модели без общих колонок вызывают ошибку."""
        # Создаем модель без общих колонок
        model_no_common = Mock()
        model_no_common._meta.fields = [
            Mock(column='totally_different', name='totally_different'),
        ]
        model_no_common.__name__ = 'NoCommon'
        
        with self.assertRaises(SchemaValidationError) as cm:
            SQLValidator.check_safe_for_insert_select(self.model1, model_no_common)
        
        self.assertIn('No common columns', str(cm.exception))

    def test_get_common_columns_same_model(self):
        """✅ Для одинаковых моделей все колонки общие."""
        common = SQLValidator.get_common_columns(self.model1, self.model1)
        
        self.assertEqual(set(common), {'id', 'email', 'first_name'})

    def test_validate_schema_compatibility_empty_lists(self):
        """✅ Пустые списки колонок обрабатываются корректно."""
        is_valid, errors = SQLValidator.validate_schema_compatibility([], [])
        
        # Пустые списки технически совместимы (нет ошибок)
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])

    def test_column_order_preserved(self):
        """✅ Порядок колонок сохраняется (важно для INSERT)."""
        order1 = SQLValidator.get_column_order(self.model1)
        order2 = SQLValidator.get_column_order(self.model1)
        
        # Порядок должен быть детерминированным
        self.assertEqual(order1, order2)

