"""
Тесты разделения операций на Blue/Green фазы.
Выявляют БАГ #1 (AddIndex/RemoveIndex) и БАГ #2 (RemoveConstraint).
"""
from django.test import TestCase
from django.db import models
from django.db.migrations import Migration
from django.db.migrations.operations import (
    CreateModel, DeleteModel, AddField, RemoveField,
    AddIndex, RemoveIndex, AddConstraint, RemoveConstraint,
    AlterField, AlterModelTable
)
from django.db.models import Index, CheckConstraint, Q

from bluegreen.management.commands.bluegreen import PatchedMigrationWriter
from bluegreen.constants import IMPOSSIBLE_OPERATIONS


class OperationReturnFormatTest(TestCase):
    """Тесты проверяют что операции возвращают правильный формат кортежей"""
    
    def create_writer(self, operations):
        migration = Migration('0001_test', 'testapp')
        migration.operations = operations
        migration.dependencies = []
        return PatchedMigrationWriter(migration, include_header=False)
    
    def test_create_model_returns_tuples(self):
        """✅ CreateModel должен вернуть (operation,), (None,)"""
        operation = CreateModel(
            name='TestModel',
            fields=[('id', models.AutoField(primary_key=True))],
        )
        writer = self.create_writer([operation])
        blue, green = writer.blue_green(operation)
        
        self.assertIsInstance(blue, tuple)
        self.assertIsInstance(green, tuple)
        self.assertEqual(len(blue), 1)
        self.assertEqual(len(green), 1)
        self.assertEqual(blue[0], operation)
        self.assertIsNone(green[0])
    
    def test_delete_model_returns_tuples(self):
        """✅ DeleteModel должен вернуть (None,), (operation,)"""
        operation = DeleteModel(name='TestModel')
        writer = self.create_writer([operation])
        blue, green = writer.blue_green(operation)
        
        self.assertIsInstance(blue, tuple)
        self.assertIsInstance(green, tuple)
        self.assertEqual(len(blue), 1)
        self.assertEqual(len(green), 1)
        self.assertIsNone(blue[0])
        self.assertEqual(green[0], operation)
    
    def test_add_field_returns_tuples(self):
        """✅ AddField должен вернуть (operation,), (None,)"""
        operation = AddField(
            model_name='testmodel',
            name='email',
            field=models.EmailField(max_length=254),
        )
        writer = self.create_writer([operation])
        blue, green = writer.blue_green(operation)
        
        self.assertIsInstance(blue, tuple)
        self.assertIsInstance(green, tuple)
        self.assertEqual(len(blue), 1)
        self.assertEqual(len(green), 1)
        self.assertEqual(blue[0], operation)
        self.assertIsNone(green[0])
    
    def test_remove_field_returns_tuples(self):
        """✅ RemoveField должен вернуть (None,), (operation,)"""
        operation = RemoveField(model_name='testmodel', name='old_field')
        writer = self.create_writer([operation])
        blue, green = writer.blue_green(operation)
        
        self.assertIsInstance(blue, tuple)
        self.assertIsInstance(green, tuple)
        self.assertEqual(len(blue), 1)
        self.assertEqual(len(green), 1)
        self.assertIsNone(blue[0])
        self.assertEqual(green[0], operation)
    
    def test_add_constraint_returns_tuples(self):
        """✅ AddConstraint должен вернуть (operation,), (None,)"""
        operation = AddConstraint(
            model_name='testmodel',
            constraint=CheckConstraint(check=Q(age__gte=18), name='age_gte_18'),
        )
        writer = self.create_writer([operation])
        blue, green = writer.blue_green(operation)
        
        self.assertIsInstance(blue, tuple)
        self.assertIsInstance(green, tuple)
        self.assertEqual(len(blue), 1)
        self.assertEqual(len(green), 1)
        self.assertEqual(blue[0], operation)
        self.assertIsNone(green[0])
    
    def test_add_index_returns_tuples(self):
        """❌ БАГ #1: AddIndex возвращает operation, None вместо (operation,), (None,)"""
        operation = AddIndex(
            model_name='testmodel',
            index=Index(fields=['name'], name='test_name_idx'),
        )
        writer = self.create_writer([operation])
        blue, green = writer.blue_green(operation)
        
        self.assertIsInstance(blue, tuple, "Blue должен быть tuple")
        self.assertIsInstance(green, tuple, "Green должен быть tuple")
    
    def test_remove_index_returns_tuples(self):
        """❌ БАГ #1: RemoveIndex возвращает None, operation вместо (None,), (operation,)"""
        operation = RemoveIndex(model_name='testmodel', name='test_name_idx')
        writer = self.create_writer([operation])
        blue, green = writer.blue_green(operation)
        
        self.assertIsInstance(blue, tuple, "Blue должен быть tuple")
        self.assertIsInstance(green, tuple, "Green должен быть tuple")
    
    def test_remove_constraint_isinstance(self):
        """❌ БАГ #2: RemoveConstraint использует isinstance(RemoveConstraint) без operation"""
        operation = RemoveConstraint(model_name='testmodel', name='age_gte_18')
        writer = self.create_writer([operation])
        
        try:
            blue, green = writer.blue_green(operation)
            self.assertIsInstance(blue, tuple)
            self.assertIsInstance(green, tuple)
        except TypeError as e:
            self.fail(f"isinstance используется неправильно: {e}")


class MigrationGenerationTest(TestCase):
    """Тесты создания blue/green миграций"""
    
    def create_writer(self, operations):
        migration = Migration('0001_test', 'testapp')
        migration.operations = operations
        migration.dependencies = []
        return PatchedMigrationWriter(migration, include_header=False)
    
    def test_create_blue_migration(self):
        """✅ Blue миграция создается с правильными параметрами"""
        migration = Migration('0001_test', 'testapp')
        migration.operations = [
            CreateModel(
                name='TestModel',
                fields=[('id', models.AutoField(primary_key=True))],
            )
        ]
        migration.dependencies = [('other_app', '0001_initial')]
        
        writer = PatchedMigrationWriter(migration, include_header=False)
        blue_migration = writer.create_blue([(CreateModel(name='TestModel', fields=[]),)])
        
        self.assertEqual(blue_migration.name, '0001_test_blue')
        self.assertEqual(blue_migration.app_label, 'testapp')
        self.assertEqual(blue_migration.dependencies, [('other_app', '0001_initial')])
        self.assertEqual(len(blue_migration.operations), 1)
    
    def test_create_green_migration(self):
        """✅ Green миграция зависит от Blue"""
        migration = Migration('0001_test', 'testapp')
        migration.dependencies = []
        
        writer = PatchedMigrationWriter(migration, include_header=False)
        blue_migration = Migration('0001_test_blue', 'testapp')
        green_migration = writer.create_green(blue_migration, [(DeleteModel(name='OldModel'),)])
        
        self.assertEqual(green_migration.name, '0001_test_green')
        self.assertEqual(green_migration.app_label, 'testapp')
        self.assertEqual(green_migration.dependencies, [('testapp', '0001_test_blue')])
        self.assertEqual(len(green_migration.operations), 1)
    
    def test_green_depends_on_blue(self):
        """✅ Green миграция зависит от соответствующей Blue"""
        migration = Migration('0001_test', 'testapp')
        migration.operations = []
        migration.dependencies = []
        
        writer = PatchedMigrationWriter(migration, include_header=False)
        blue_writer, green_writer = writer.split_migrations(impossible=False)
        
        blue_dependency = ('testapp', '0001_test_blue')
        self.assertIn(blue_dependency, green_writer.migration.dependencies)
    
    def test_blue_preserves_dependencies(self):
        """✅ Blue миграция сохраняет исходные зависимости"""
        original_deps = [
            ('other_app', '0001_initial'),
            ('another_app', '0005_migration'),
        ]
        
        migration = Migration('0001_test', 'testapp')
        migration.operations = []
        migration.dependencies = original_deps
        
        writer = PatchedMigrationWriter(migration, include_header=False)
        blue_writer, green_writer = writer.split_migrations(impossible=False)
        
        self.assertEqual(blue_writer.migration.dependencies, original_deps)


class OperationFilteringTest(TestCase):
    """Тесты фильтрации None операций"""
    
    def test_none_operations_filtered_in_blue(self):
        """✅ None операции фильтруются из blue списка"""
        from itertools import chain
        
        operations_list = [
            (CreateModel(name='Model1', fields=[]),),
            (None,),
            (CreateModel(name='Model2', fields=[]),),
        ]
        
        filtered = list(filter(None, chain.from_iterable(operations_list)))
        
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(op is not None for op in filtered))
    
    def test_none_operations_filtered_in_green(self):
        """✅ None операции фильтруются из green списка"""
        from itertools import chain
        
        operations_list = [
            (None,),
            (DeleteModel(name='Model1'),),
            (None,),
            (DeleteModel(name='Model2'),),
        ]
        
        filtered = list(filter(None, chain.from_iterable(operations_list)))
        
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(op is not None for op in filtered))


class EdgeCasesTest(TestCase):
    """Тесты граничных случаев"""
    
    def create_writer(self, operations):
        migration = Migration('0001_test', 'testapp')
        migration.operations = operations
        migration.dependencies = []
        return PatchedMigrationWriter(migration, include_header=False)
    
    def test_empty_migration(self):
        """✅ Пустая миграция создает пустые blue/green"""
        migration = Migration('0001_test', 'testapp')
        migration.operations = []
        migration.dependencies = []
        
        writer = PatchedMigrationWriter(migration, include_header=False)
        blue_writer, green_writer = writer.split_migrations(impossible=False)
        
        self.assertEqual(len(blue_writer.migration.operations), 0)
        self.assertEqual(len(green_writer.migration.operations), 0)
    
    def test_multiple_operations_same_type(self):
        """✅ Несколько операций одного типа корректно разделяются"""
        migration = Migration('0001_test', 'testapp')
        migration.operations = [
            CreateModel(name='Model1', fields=[('id', models.AutoField(primary_key=True))]),
            CreateModel(name='Model2', fields=[('id', models.AutoField(primary_key=True))]),
            CreateModel(name='Model3', fields=[('id', models.AutoField(primary_key=True))]),
        ]
        migration.dependencies = []
        
        writer = PatchedMigrationWriter(migration, include_header=False)
        blue_writer, green_writer = writer.split_migrations(impossible=False)
        
        # Все CreateModel в Blue
        self.assertEqual(len(blue_writer.migration.operations), 3)
        # Green пустой
        self.assertEqual(len(green_writer.migration.operations), 0)
    
    def test_mixed_operations(self):
        """✅ Смешанные операции корректно распределяются"""
        migration = Migration('0001_test', 'testapp')
        migration.operations = [
            CreateModel(name='NewModel', fields=[('id', models.AutoField(primary_key=True))]),
            AddField(model_name='existing', name='new_field', field=models.CharField(max_length=100)),
            RemoveField(model_name='existing', name='old_field'),
            DeleteModel(name='OldModel'),
        ]
        migration.dependencies = []
        
        writer = PatchedMigrationWriter(migration, include_header=False)
        blue_writer, green_writer = writer.split_migrations(impossible=False)
        
        # Blue: CreateModel, AddField
        blue_ops = [op.__class__.__name__ for op in blue_writer.migration.operations]
        self.assertIn('CreateModel', blue_ops)
        self.assertIn('AddField', blue_ops)
        
        # Green: RemoveField, DeleteModel
        green_ops = [op.__class__.__name__ for op in green_writer.migration.operations]
        self.assertIn('RemoveField', green_ops)
        self.assertIn('DeleteModel', green_ops)


class ImpossibleOperationsTest(TestCase):
    """Тесты обнаружения невозможных операций"""
    
    def test_impossible_operations_detected(self):
        """✅ Невозможные операции корректно определяются"""
        self.assertIn(AlterField, IMPOSSIBLE_OPERATIONS)
        self.assertIn(AlterModelTable, IMPOSSIBLE_OPERATIONS)
    
    def test_normal_operations_not_impossible(self):
        """✅ Обычные операции НЕ в списке невозможных"""
        self.assertNotIn(CreateModel, IMPOSSIBLE_OPERATIONS)
        self.assertNotIn(AddField, IMPOSSIBLE_OPERATIONS)
        self.assertNotIn(AddIndex, IMPOSSIBLE_OPERATIONS)
        self.assertNotIn(AddConstraint, IMPOSSIBLE_OPERATIONS)
