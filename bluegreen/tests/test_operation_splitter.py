"""
Тесты для OperationSplitter и стратегий разделения операций.
"""
from unittest.mock import Mock
from django.test import TestCase
from django.db.migrations.operations import (
    CreateModel, DeleteModel, RenameModel,
    AddField, RemoveField, RenameField,
    AddIndex, RemoveIndex, RenameIndex,
    AddConstraint, RemoveConstraint,
    AlterField
)

from bluegreen.operations import OperationSplitter
from bluegreen.operations.strategies import (
    ModelStrategy, FieldStrategy, IndexStrategy, ConstraintStrategy
)


class ModelStrategyTest(TestCase):
    """Тесты для ModelStrategy."""
    
    def setUp(self):
        self.strategy = ModelStrategy()
    
    def test_can_handle_model_operations(self):
        """✅ Стратегия обрабатывает операции с моделями."""
        self.assertTrue(self.strategy.can_handle(CreateModel('Test', [])))
        self.assertTrue(self.strategy.can_handle(DeleteModel('Test')))
        self.assertTrue(self.strategy.can_handle(RenameModel('Old', 'New')))
        self.assertFalse(self.strategy.can_handle(AddField('Model', 'field', Mock())))


class FieldStrategyTest(TestCase):
    """Тесты для FieldStrategy."""
    
    def setUp(self):
        self.strategy = FieldStrategy()
    
    def test_can_handle_field_operations(self):
        """✅ Стратегия обрабатывает операции с полями."""
        self.assertTrue(self.strategy.can_handle(AddField('Model', 'field', Mock())))
        self.assertTrue(self.strategy.can_handle(RemoveField('Model', 'field')))
        self.assertTrue(self.strategy.can_handle(RenameField('Model', 'old', 'new')))
        self.assertFalse(self.strategy.can_handle(CreateModel('Test', [])))


class IndexStrategyTest(TestCase):
    """Тесты для IndexStrategy."""
    
    def setUp(self):
        self.strategy = IndexStrategy()
    
    def test_can_handle_index_operations(self):
        """✅ Стратегия обрабатывает операции с индексами."""
        self.assertTrue(self.strategy.can_handle(AddIndex('Model', Mock())))
        self.assertTrue(self.strategy.can_handle(RemoveIndex('Model', 'index')))
        self.assertTrue(self.strategy.can_handle(RenameIndex('Model', 'old', 'new')))
        self.assertFalse(self.strategy.can_handle(CreateModel('Test', [])))


class ConstraintStrategyTest(TestCase):
    """Тесты для ConstraintStrategy."""
    
    def setUp(self):
        self.strategy = ConstraintStrategy()
    
    def test_can_handle_constraint_operations(self):
        """✅ Стратегия обрабатывает операции с ограничениями."""
        self.assertTrue(self.strategy.can_handle(AddConstraint('Model', Mock())))
        self.assertTrue(self.strategy.can_handle(RemoveConstraint('Model', 'constraint')))
        self.assertFalse(self.strategy.can_handle(CreateModel('Test', [])))


class OperationSplitterTest(TestCase):
    """Тесты для OperationSplitter."""
    
    def setUp(self):
        self.splitter = OperationSplitter('testapp')
    
    def test_split_create_model(self):
        """✅ CreateModel идет в blue фазу."""
        op = CreateModel('TestModel', [])
        blue, green = self.splitter.split_operation(op)
        
        self.assertEqual(len(blue), 1)
        self.assertEqual(blue[0], op)
        self.assertEqual(len(green), 1)
        self.assertIsNone(green[0])
    
    def test_split_delete_model(self):
        """✅ DeleteModel идет в green фазу."""
        op = DeleteModel('TestModel')
        blue, green = self.splitter.split_operation(op)
        
        self.assertEqual(len(blue), 1)
        self.assertIsNone(blue[0])
        self.assertEqual(len(green), 1)
        self.assertEqual(green[0], op)
    
    def test_split_add_field(self):
        """✅ AddField идет в blue фазу."""
        op = AddField('TestModel', 'test_field', Mock())
        blue, green = self.splitter.split_operation(op)
        
        self.assertEqual(len(blue), 1)
        self.assertEqual(blue[0], op)
        self.assertEqual(len(green), 1)
        self.assertIsNone(green[0])
    
    def test_split_remove_field(self):
        """✅ RemoveField идет в green фазу."""
        op = RemoveField('TestModel', 'test_field')
        blue, green = self.splitter.split_operation(op)
        
        self.assertEqual(len(blue), 1)
        self.assertIsNone(blue[0])
        self.assertEqual(len(green), 1)
        self.assertEqual(green[0], op)
    
    def test_split_operations_list(self):
        """✅ Список операций разделяется корректно."""
        operations = [
            CreateModel('Model1', []),
            AddField('Model1', 'field1', Mock()),
            DeleteModel('Model2'),
            RemoveField('Model1', 'field2'),
        ]
        
        blue, green = self.splitter.split_operations(operations)
        
        # CreateModel и AddField в blue
        self.assertEqual(len(blue), 2)
        # DeleteModel и RemoveField в green
        self.assertEqual(len(green), 2)
    
    def test_detect_impossible_operations(self):
        """✅ Невозможные операции обнаруживаются."""
        operations = [
            CreateModel('Model1', []),
            AlterField('Model1', 'field', Mock()),
            AddField('Model1', 'field2', Mock()),
        ]
        
        impossible = self.splitter.detect_impossible_operations(operations)
        
        # Только AlterField невозможно
        self.assertEqual(len(impossible), 1)
        self.assertIsInstance(impossible[0], AlterField)
    
    def test_split_operations_filters_none(self):
        """✅ None операции фильтруются из результата."""
        operations = [
            CreateModel('Model1', []),
            DeleteModel('Model2'),
        ]
        
        blue, green = self.splitter.split_operations(operations)
        
        # Проверяем что None отфильтрованы
        self.assertNotIn(None, blue)
        self.assertNotIn(None, green)

