"""
Тесты для патченных операций (AddFieldPatched, CreateModelPatched, AddIndexPatched).
"""
from django.test import TestCase
from django.db import models
from django.db.models import Index

from bluegreen.fields import AddFieldPatched, CreateModelPatched, AddIndexPatched


class AddFieldPatchedTest(TestCase):
    """Тесты для AddFieldPatched операции"""
    
    def test_has_old_name_attribute(self):
        """✅ AddFieldPatched имеет атрибут old_name"""
        field = models.CharField(max_length=100)
        operation = AddFieldPatched(
            model_name='testmodel',
            name='new_name',
            old_name='old_name',
            field=field,
        )
        
        self.assertEqual(operation.old_name, 'old_name')
        self.assertEqual(operation.name, 'new_name')
        self.assertEqual(operation.model_name, 'testmodel')
    
    def test_deconstruct_includes_old_name(self):
        """✅ deconstruct() включает old_name в kwargs"""
        field = models.CharField(max_length=100)
        operation = AddFieldPatched(
            model_name='testmodel',
            name='new_name',
            old_name='old_name',
            field=field,
        )
        
        name, args, kwargs = operation.deconstruct()
        
        self.assertEqual(name, 'AddFieldPatched')
        self.assertIn('old_name', kwargs)
        self.assertEqual(kwargs['old_name'], 'old_name')


class CreateModelPatchedTest(TestCase):
    """Тесты для CreateModelPatched операции"""
    
    def test_has_old_name_attribute(self):
        """✅ CreateModelPatched имеет атрибут old_name"""
        fields = [
            models.CharField(max_length=100, name='field1'),
            models.IntegerField(name='field2'),
        ]
        
        operation = CreateModelPatched(
            name='NewModel',
            fields=fields,
            old_name='OldModel',
        )
        
        self.assertEqual(operation.old_name, 'OldModel')
        self.assertEqual(operation.name, 'NewModel')
    
    def test_fields_converted_to_tuples(self):
        """✅ Поля конвертируются в кортежи (name, field)"""
        field1 = models.CharField(max_length=100, name='field1')
        field2 = models.IntegerField(name='field2')
        
        operation = CreateModelPatched(
            name='NewModel',
            fields=[field1, field2],
            old_name='OldModel',
        )
        
        # Проверяем что fields - tuple из кортежей (name, field)
        self.assertIsInstance(operation.fields, tuple)
        for field_tuple in operation.fields:
            self.assertIsInstance(field_tuple, tuple)
            self.assertEqual(len(field_tuple), 2)
            # Первый элемент - имя поля (string)
            self.assertIsInstance(field_tuple[0], str)


class AddIndexPatchedTest(TestCase):
    """Тесты для AddIndexPatched операции"""
    
    def test_has_old_name_attribute(self):
        """✅ AddIndexPatched имеет атрибут old_name"""
        index = Index(fields=['field1'], name='new_idx')
        
        operation = AddIndexPatched(
            model_name='testmodel',
            index=index,
            old_name='old_idx',
        )
        
        self.assertEqual(operation.old_name, 'old_idx')
        self.assertEqual(operation.model_name, 'testmodel')
        self.assertEqual(operation.index.name, 'new_idx')

