"""
Тесты безопасности SQL.
Выявляют БАГ #4 (SQL-инъекции в bluegreen.py).
"""
import os
import re
from django.test import TestCase


class SQLInjectionTest(TestCase):
    """Проверка что SQL генерируется без f-строк"""
    
    def test_no_bare_f_strings_in_sql(self):
        """
        БАГ #4: SQL формируется через f-строки без quote_name() или quote_identifier()
        
        Опасные места:
        - bluegreen.py:~65  f"INSERT INTO {old_table}..."
        - bluegreen.py:~90  f"UPDATE {table} SET..."
        """
        bluegreen_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'management', 'commands', 'bluegreen.py'
        )
        
        with open(bluegreen_path, 'r') as f:
            content = f.read()
        
        # Ищем опасные паттерны
        dangerous_patterns = [
            (r'f["\']INSERT INTO \{[^}]+\}', 'INSERT с f-строкой'),
            (r'f["\']UPDATE \{[^}]+\} SET', 'UPDATE с f-строкой'),
        ]
        
        issues = []
        for pattern, description in dangerous_patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            for match in matches:
                context = content[max(0, match.start()-50):match.end()+50]
                # Проверяем наличие quote_name ИЛИ quote_identifier
                if 'quote_name' not in context and 'quote_identifier' not in context:
                    issues.append(f"{description}: {match.group()}")
        
        if issues:
            self.fail("SQL-инъекции без quote_name/quote_identifier:\n" + "\n".join(issues))
