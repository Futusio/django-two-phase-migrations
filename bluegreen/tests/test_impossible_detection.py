"""
Тесты для обнаружения impossible операций.
"""
from unittest.mock import Mock, patch
from django.test import TestCase
from django.db.migrations.operations import (
    CreateModel, AddField, AlterField, AlterModelTable,
    AlterUniqueTogether, AlterIndexTogether
)

from bluegreen.management.commands.bluegreen import PatchedMigrationWriter
from bluegreen.constants import IMPOSSIBLE_OPERATIONS
from bluegreen.exceptions import ImpossibleOperationError


class ImpossibleOperationDetectionTest(TestCase):
    """Тесты для корректного определения impossible операций."""
    
    def setUp(self):
        self.migration = Mock()
        self.migration.app_label = 'testapp'
        self.migration.name = '0001_test'
        self.migration.dependencies = []
        self.migration.replaces = []
        self.migration.run_before = []
        self.migration.initial = False
    
    def test_alter_field_detected_as_impossible(self):
        """✅ AlterField определяется как impossible операция."""
        field = Mock()
        field.clone.return_value = Mock()
        
        alter_field_op = AlterField(
            model_name='testmodel',
            name='test_field',
            field=field
        )
        self.migration.operations = [alter_field_op]
        
        writer = PatchedMigrationWriter(self.migration)
        
        # В non-interactive режиме должна выброситься ошибка
        with self.assertRaises(ImpossibleOperationError) as cm:
            writer.split_migrations(impossible=True, non_interactive=True)
        
        self.assertIn("Cannot split migration", str(cm.exception))
    
    def test_alter_model_table_detected_as_impossible(self):
        """✅ AlterModelTable определяется как impossible операция."""
        alter_table_op = AlterModelTable(
            name='testmodel',
            table='new_table_name'
        )
        self.migration.operations = [alter_table_op]
        
        writer = PatchedMigrationWriter(self.migration)
        
        with self.assertRaises(ImpossibleOperationError):
            writer.split_migrations(impossible=True, non_interactive=True)
    
    def test_alter_unique_together_detected_as_impossible(self):
        """✅ AlterUniqueTogether определяется как impossible операция."""
        alter_unique_op = AlterUniqueTogether(
            name='testmodel',
            unique_together=[('field1', 'field2')]
        )
        self.migration.operations = [alter_unique_op]
        
        writer = PatchedMigrationWriter(self.migration)
        
        with self.assertRaises(ImpossibleOperationError):
            writer.split_migrations(impossible=True, non_interactive=True)
    
    def test_alter_index_together_detected_as_impossible(self):
        """✅ AlterIndexTogether определяется как impossible операция."""
        alter_index_op = AlterIndexTogether(
            name='testmodel',
            index_together=[('field1', 'field2')]
        )
        self.migration.operations = [alter_index_op]
        
        writer = PatchedMigrationWriter(self.migration)
        
        with self.assertRaises(ImpossibleOperationError):
            writer.split_migrations(impossible=True, non_interactive=True)
    
    def test_normal_operation_not_detected_as_impossible(self):
        """✅ Обычные операции НЕ определяются как impossible."""
        field = Mock()
        field.clone.return_value = Mock()
        
        create_op = CreateModel(
            name='TestModel',
            fields=[('id', field)]
        )
        self.migration.operations = [create_op]
        
        writer = PatchedMigrationWriter(self.migration)
        
        # Не должно быть ошибки для обычной операции
        try:
            blue, green = writer.split_migrations(impossible=False, non_interactive=True)
            # Успешно разделилось
            self.assertIsNotNone(blue)
            self.assertIsNotNone(green)
        except ImpossibleOperationError:
            self.fail("CreateModel не должен считаться impossible операцией")
    
    def test_mixed_operations_with_impossible(self):
        """✅ Смешанные операции с impossible корректно определяются."""
        field = Mock()
        field.clone.return_value = Mock()
        
        create_op = CreateModel(name='Model1', fields=[('id', field)])
        alter_op = AlterField(model_name='Model2', name='field', field=field)
        add_op = AddField(model_name='Model3', name='field', field=field)
        
        self.migration.operations = [create_op, alter_op, add_op]
        
        writer = PatchedMigrationWriter(self.migration)
        
        # Должна выброситься ошибка из-за AlterField
        with self.assertRaises(ImpossibleOperationError):
            writer.split_migrations(impossible=True, non_interactive=True)
    
    def test_impossible_operations_set_contains_correct_types(self):
        """✅ IMPOSSIBLE_OPERATIONS содержит правильные типы."""
        # Проверяем что это set классов, а не экземпляров
        for op_type in IMPOSSIBLE_OPERATIONS:
            self.assertTrue(isinstance(op_type, type), 
                          f"{op_type} должен быть классом, а не экземпляром")
        
        # Проверяем что AlterField в списке
        self.assertIn(AlterField, IMPOSSIBLE_OPERATIONS)
        self.assertIn(AlterModelTable, IMPOSSIBLE_OPERATIONS)
    
    def test_type_comparison_works_correctly(self):
        """✅ Проверка type(operation) in IMPOSSIBLE_OPERATIONS работает."""
        field = Mock()
        field.clone.return_value = Mock()
        
        alter_field_instance = AlterField(
            model_name='test',
            name='field',
            field=field
        )
        
        # Проверяем что type() возвращает класс
        self.assertEqual(type(alter_field_instance), AlterField)
        
        # Проверяем что класс есть в IMPOSSIBLE_OPERATIONS
        self.assertIn(type(alter_field_instance), IMPOSSIBLE_OPERATIONS)
        
        # Проверяем что экземпляр НЕ в IMPOSSIBLE_OPERATIONS
        self.assertNotIn(alter_field_instance, IMPOSSIBLE_OPERATIONS)

