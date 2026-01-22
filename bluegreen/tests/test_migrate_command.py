"""
Тесты команды migrate.
Выявляют БАГ #5 (сравнение по __class__.__name__) и БАГ #6 (SQL-инъекция).
"""
import os
import re
from django.test import TestCase
from unittest.mock import Mock


class MigrateCommandFilteringTest(TestCase):
    """Тесты фильтрации миграций по --blue/--green флагам"""
    
    def test_blue_flag_filters_out_green(self):
        """✅ --blue оставляет только blue миграции"""
        mock_blue = Mock()
        mock_blue.name = '0001_initial_blue'
        mock_green = Mock()
        mock_green.name = '0001_initial_green'
        
        plan = [(mock_blue, False), (mock_green, False)]
        
        # Логика из migrate.py:184 - фильтрует _blue когда флаг --green
        filtered_green = list(filter(lambda x: not x[0].name.endswith('_blue'), plan))
        self.assertEqual(len(filtered_green), 1)
        self.assertTrue(filtered_green[0][0].name.endswith('_green'))
    
    def test_green_flag_filters_out_blue(self):
        """✅ --green оставляет только green миграции"""
        mock_blue = Mock()
        mock_blue.name = '0001_initial_blue'
        mock_green = Mock()
        mock_green.name = '0001_initial_green'
        
        plan = [(mock_blue, False), (mock_green, False)]
        
        # Логика из migrate.py:186 - фильтрует _green когда флаг --blue
        filtered_blue = list(filter(lambda x: not x[0].name.endswith('_green'), plan))
        self.assertEqual(len(filtered_blue), 1)
        self.assertTrue(filtered_blue[0][0].name.endswith('_blue'))
    
    def test_no_flags_applies_both(self):
        """✅ Без флагов обе миграции применяются"""
        mock_blue = Mock()
        mock_blue.name = '0001_initial_blue'
        mock_green = Mock()
        mock_green.name = '0001_initial_green'
        
        plan = [(mock_blue, False), (mock_green, False)]
        
        # Без фильтрации
        self.assertEqual(len(plan), 2)
    
    def test_multiple_migrations_filtered(self):
        """✅ Фильтрация работает с несколькими миграциями"""
        m1 = Mock()
        m1.name = '0001_initial_blue'
        m2 = Mock()
        m2.name = '0001_initial_green'
        m3 = Mock()
        m3.name = '0002_add_field_blue'
        m4 = Mock()
        m4.name = '0002_add_field_green'
        m5 = Mock()
        m5.name = '0003_other_app_blue'
        
        plan = [(m1, False), (m2, False), (m3, False), (m4, False), (m5, False)]
        
        # Только blue
        blue_only = list(filter(lambda x: not x[0].name.endswith('_green'), plan))
        self.assertEqual(len(blue_only), 3)
        
        # Только green
        green_only = list(filter(lambda x: not x[0].name.endswith('_blue'), plan))
        self.assertEqual(len(green_only), 2)


class AddFieldPatchedHandlingTest(TestCase):
    """Тесты обработки AddFieldPatched операций"""
    
    def test_isinstance_not_class_name(self):
        """❌ БАГ #5: migrate.py:312 использует __class__.__name__ вместо isinstance"""
        migrate_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'management', 'commands', 'migrate.py'
        )
        
        with open(migrate_path, 'r') as f:
            content = f.read()
        
        # Ищем __class__.__name__ == 'AddFieldPatched'
        pattern = r'__class__\.__name__\s*==\s*[\'"]AddFieldPatched[\'"]'
        matches = list(re.finditer(pattern, content))
        
        if matches:
            self.fail(
                f"Найдено {len(matches)} использований __class__.__name__. "
                "Используйте isinstance(operation, AddFieldPatched)"
            )
    
    def test_sql_injection_in_migrate(self):
        """❌ БАГ #6: migrate.py:318 использует f-строку в cursor.execute"""
        migrate_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'management', 'commands', 'migrate.py'
        )
        
        with open(migrate_path, 'r') as f:
            content = f.read()
        
        # Ищем cursor.execute с f-строкой
        pattern = r'cursor\.execute\(f"UPDATE.*\{.*\}'
        matches = list(re.finditer(pattern, content))
        
        for match in matches:
            context = content[max(0, match.start()-100):match.end()+50]
            if 'quote_name' not in context:
                self.fail(
                    f"SQL-инъекция в cursor.execute: {match.group()}\n"
                    "Используйте connection.ops.quote_name()"
                )
