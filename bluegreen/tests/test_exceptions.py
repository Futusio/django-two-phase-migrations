"""
Тесты для кастомных исключений и обработки ошибок.
"""
from django.test import TestCase
from django.db import models
from django.db.migrations import Migration
from django.db.migrations.operations import RenameModel, RenameField, RenameIndex, AlterField

from bluegreen.management.commands.bluegreen import PatchedMigrationWriter
from bluegreen.exceptions import (
    ImpossibleOperationError,
    ModelNotFoundError,
    FieldNotFoundError,
    IndexNotFoundError,
)


class ExceptionsTest(TestCase):
    """Тесты кастомных исключений"""
    
    def test_impossible_operation_error_raised(self):
        """✅ ImpossibleOperationError выбрасывается для невозможных операций в non-interactive режиме"""
        migration = Migration('0001_test', 'testapp')
        migration.operations = [
            AlterField(
                model_name='testmodel',
                name='field',
                field=models.CharField(max_length=100),
            )
        ]
        migration.dependencies = []
        
        writer = PatchedMigrationWriter(migration, include_header=False)
        
        with self.assertRaises(ImpossibleOperationError) as cm:
            writer.split_migrations(impossible=True, non_interactive=True)
        
        self.assertIn('AlterField', str(cm.exception))
        self.assertIn('cannot be split', str(cm.exception).lower())
    
    def test_model_not_found_error(self):
        """✅ ModelNotFoundError выбрасывается для несуществующей модели"""
        migration = Migration('0001_test', 'testapp')
        migration.operations = [
            RenameModel(old_name='OldModel', new_name='NonExistentModel')
        ]
        migration.dependencies = []
        
        writer = PatchedMigrationWriter(migration, include_header=False)
        operation = migration.operations[0]
        
        with self.assertRaises(ModelNotFoundError) as cm:
            writer.blue_green(operation)
        
        self.assertIn('NonExistentModel', str(cm.exception))
        self.assertIn('not found', str(cm.exception).lower())


class ImpossibleOperationsHandlingTest(TestCase):
    """Тесты для неинтерактивного режима"""
    
    def test_non_interactive_flag_prevents_input(self):
        """✅ Флаг --non-interactive предотвращает вызов input()"""
        migration = Migration('0001_test', 'testapp')
        migration.operations = [
            AlterField(
                model_name='testmodel',
                name='field',
                field=models.CharField(max_length=100),
            )
        ]
        migration.dependencies = []
        
        writer = PatchedMigrationWriter(migration, include_header=False)
        
        # В non-interactive режиме должно выбросить исключение
        with self.assertRaises(ImpossibleOperationError):
            writer.split_migrations(impossible=True, non_interactive=True)
    
    def test_unknown_operations_handled_gracefully(self):
        """✅ Неизвестные операции обрабатываются без падения"""
        from django.db.migrations.operations import RunPython
        
        migration = Migration('0001_test', 'testapp')
        migration.operations = [
            RunPython(code=lambda apps, schema_editor: None)
        ]
        migration.dependencies = []
        
        writer = PatchedMigrationWriter(migration, include_header=False)
        
        # Неизвестные операции не должны вызывать TypeError
        blue_writer, green_writer = writer.split_migrations(impossible=False, non_interactive=True)
        
        # Blue должна содержать операцию
        self.assertEqual(len(blue_writer.migration.operations), 1)
        # Green должна быть пустой
        self.assertEqual(len(green_writer.migration.operations), 0)
    
    def test_normal_operations_work_in_both_modes(self):
        """✅ Обычные операции работают в обоих режимах"""
        from django.db.migrations.operations import CreateModel
        
        migration = Migration('0001_test', 'testapp')
        migration.operations = [
            CreateModel(
                name='TestModel',
                fields=[('id', models.AutoField(primary_key=True))],
            )
        ]
        migration.dependencies = []
        
        writer = PatchedMigrationWriter(migration, include_header=False)
        
        # Для обычных операций split работает в обоих режимах
        blue_writer, green_writer = writer.split_migrations(impossible=False, non_interactive=True)
        
        self.assertEqual(blue_writer.migration.name, '0001_test_blue')
        self.assertEqual(green_writer.migration.name, '0001_test_green')
        # Blue должен содержать CreateModel
        self.assertEqual(len(blue_writer.migration.operations), 1)
        # Green пустой для CreateModel
        self.assertEqual(len(green_writer.migration.operations), 0)

