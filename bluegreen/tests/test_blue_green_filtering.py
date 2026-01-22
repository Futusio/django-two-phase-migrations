"""
Тесты для фильтрации миграций в режимах --blue и --green.
"""
from io import StringIO
from unittest.mock import Mock, patch, MagicMock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.db.migrations import Migration


class BlueGreenFilteringTest(TestCase):
    """Тесты фильтрации миграций для blue-green deployment"""
    
    def test_blue_mode_skips_green_migrations(self):
        """✅ --blue режим пропускает _green миграции"""
        # Создаём план миграций с разными суффиксами
        blue_migration = Mock(spec=Migration)
        blue_migration.name = '0001_initial_blue'
        blue_migration.app_label = 'testapp'
        
        green_migration = Mock(spec=Migration)
        green_migration.name = '0001_initial_green'
        green_migration.app_label = 'testapp'
        
        vanilla_migration = Mock(spec=Migration)
        vanilla_migration.name = '0002_add_field'
        vanilla_migration.app_label = 'testapp'
        
        plan = [
            (blue_migration, False),
            (green_migration, False),
            (vanilla_migration, False),
        ]
        
        # Мокаем команду migrate
        with patch('bluegreen.management.commands.migrate.Command.check'):
            with patch('bluegreen.management.commands.migrate.MigrationExecutor') as mock_executor:
                mock_executor_instance = mock_executor.return_value
                mock_executor_instance.loader.check_consistent_history = Mock()
                mock_executor_instance.loader.detect_conflicts.return_value = {}
                mock_executor_instance.loader.graph.leaf_nodes.return_value = []
                mock_executor_instance.migration_plan.return_value = plan
                mock_executor_instance._create_project_state.return_value = Mock(apps=Mock())
                mock_executor_instance.migrate.return_value = Mock(apps=Mock(), clear_delayed_apps_cache=Mock())
                mock_executor_instance.loader.unmigrated_apps = []
                
                out = StringIO()
                call_command('migrate', '--blue', verbosity=0, stdout=out, skip_checks=True)
                
                # Проверяем что migrate был вызван с отфильтрованным планом
                called_plan = mock_executor_instance.migrate.call_args[1]['plan']
                
                # Blue режим должен включать: _blue + vanilla (без _green)
                migration_names = [item[0].name for item in called_plan]
                self.assertIn('0001_initial_blue', migration_names)
                self.assertIn('0002_add_field', migration_names)
                self.assertNotIn('0001_initial_green', migration_names)
    
    def test_green_mode_skips_blue_migrations(self):
        """✅ --green режим пропускает _blue миграции"""
        blue_migration = Mock(spec=Migration)
        blue_migration.name = '0001_initial_blue'
        blue_migration.app_label = 'testapp'
        
        green_migration = Mock(spec=Migration)
        green_migration.name = '0001_initial_green'
        green_migration.app_label = 'testapp'
        
        vanilla_migration = Mock(spec=Migration)
        vanilla_migration.name = '0002_add_field'
        vanilla_migration.app_label = 'testapp'
        
        plan = [
            (blue_migration, False),
            (green_migration, False),
            (vanilla_migration, False),
        ]
        
        with patch('bluegreen.management.commands.migrate.Command.check'):
            with patch('bluegreen.management.commands.migrate.MigrationExecutor') as mock_executor:
                mock_executor_instance = mock_executor.return_value
                mock_executor_instance.loader.check_consistent_history = Mock()
                mock_executor_instance.loader.detect_conflicts.return_value = {}
                mock_executor_instance.loader.graph.leaf_nodes.return_value = []
                mock_executor_instance.migration_plan.return_value = plan
                mock_executor_instance._create_project_state.return_value = Mock(apps=Mock())
                mock_executor_instance.migrate.return_value = Mock(apps=Mock(), clear_delayed_apps_cache=Mock())
                mock_executor_instance.loader.unmigrated_apps = []
                
                out = StringIO()
                call_command('migrate', '--green', verbosity=0, stdout=out, skip_checks=True)
                
                called_plan = mock_executor_instance.migrate.call_args[1]['plan']
                
                # Green режим должен включать: _green + vanilla (без _blue)
                migration_names = [item[0].name for item in called_plan]
                self.assertIn('0001_initial_green', migration_names)
                self.assertIn('0002_add_field', migration_names)
                self.assertNotIn('0001_initial_blue', migration_names)
    
    def test_vanilla_migrations_run_in_both_modes(self):
        """✅ Обычные миграции (без суффиксов) выполняются в обоих режимах"""
        vanilla_migration_1 = Mock(spec=Migration)
        vanilla_migration_1.name = '0001_initial'
        vanilla_migration_1.app_label = 'testapp'
        
        vanilla_migration_2 = Mock(spec=Migration)
        vanilla_migration_2.name = '0002_alter_field'
        vanilla_migration_2.app_label = 'testapp'
        
        plan = [
            (vanilla_migration_1, False),
            (vanilla_migration_2, False),
        ]
        
        with patch('bluegreen.management.commands.migrate.Command.check'):
            with patch('bluegreen.management.commands.migrate.MigrationExecutor') as mock_executor:
                mock_executor_instance = mock_executor.return_value
                mock_executor_instance.loader.check_consistent_history = Mock()
                mock_executor_instance.loader.detect_conflicts.return_value = {}
                mock_executor_instance.loader.graph.leaf_nodes.return_value = []
                mock_executor_instance.migration_plan.return_value = plan
                mock_executor_instance._create_project_state.return_value = Mock(apps=Mock())
                mock_executor_instance.migrate.return_value = Mock(apps=Mock(), clear_delayed_apps_cache=Mock())
                mock_executor_instance.loader.unmigrated_apps = []
                
                # Test --blue mode
                out = StringIO()
                call_command('migrate', '--blue', verbosity=0, stdout=out, skip_checks=True)
                called_plan_blue = mock_executor_instance.migrate.call_args[1]['plan']
                self.assertEqual(len(called_plan_blue), 2)
                
                # Test --green mode
                out = StringIO()
                call_command('migrate', '--green', verbosity=0, stdout=out, skip_checks=True)
                called_plan_green = mock_executor_instance.migrate.call_args[1]['plan']
                self.assertEqual(len(called_plan_green), 2)
    
    def test_cannot_use_both_blue_and_green(self):
        """✅ Нельзя использовать --blue и --green одновременно"""
        with self.assertRaises(CommandError) as cm:
            call_command('migrate', '--blue', '--green', verbosity=0, skip_checks=True)
        
        self.assertIn('Cannot use --blue and --green', str(cm.exception))
    
    def test_no_flags_runs_all_migrations(self):
        """✅ Без флагов выполняются все миграции"""
        blue_migration = Mock(spec=Migration)
        blue_migration.name = '0001_initial_blue'
        blue_migration.app_label = 'testapp'
        
        green_migration = Mock(spec=Migration)
        green_migration.name = '0001_initial_green'
        green_migration.app_label = 'testapp'
        
        vanilla_migration = Mock(spec=Migration)
        vanilla_migration.name = '0002_add_field'
        vanilla_migration.app_label = 'testapp'
        
        plan = [
            (blue_migration, False),
            (green_migration, False),
            (vanilla_migration, False),
        ]
        
        with patch('bluegreen.management.commands.migrate.Command.check'):
            with patch('bluegreen.management.commands.migrate.MigrationExecutor') as mock_executor:
                mock_executor_instance = mock_executor.return_value
                mock_executor_instance.loader.check_consistent_history = Mock()
                mock_executor_instance.loader.detect_conflicts.return_value = {}
                mock_executor_instance.loader.graph.leaf_nodes.return_value = []
                mock_executor_instance.migration_plan.return_value = plan
                mock_executor_instance._create_project_state.return_value = Mock(apps=Mock())
                mock_executor_instance.migrate.return_value = Mock(apps=Mock(), clear_delayed_apps_cache=Mock())
                mock_executor_instance.loader.unmigrated_apps = []
                
                out = StringIO()
                call_command('migrate', verbosity=0, stdout=out, skip_checks=True)
                
                called_plan = mock_executor_instance.migrate.call_args[1]['plan']
                
                # Без флагов должны выполниться ВСЕ миграции
                self.assertEqual(len(called_plan), 3)
                migration_names = [item[0].name for item in called_plan]
                self.assertIn('0001_initial_blue', migration_names)
                self.assertIn('0001_initial_green', migration_names)
                self.assertIn('0002_add_field', migration_names)
    
    def test_blue_mode_logs_filtered_migrations(self):
        """✅ Blue режим логирует количество отфильтрованных green миграций"""
        blue_migration = Mock(spec=Migration)
        blue_migration.name = '0001_initial_blue'
        blue_migration.app_label = 'testapp'
        
        green_migration = Mock(spec=Migration)
        green_migration.name = '0001_initial_green'
        green_migration.app_label = 'testapp'
        
        plan = [(blue_migration, False), (green_migration, False)]
        
        with patch('bluegreen.management.commands.migrate.Command.check'):
            with patch('bluegreen.management.commands.migrate.MigrationExecutor') as mock_executor:
                mock_executor_instance = mock_executor.return_value
                mock_executor_instance.loader.check_consistent_history = Mock()
                mock_executor_instance.loader.detect_conflicts.return_value = {}
                mock_executor_instance.loader.graph.leaf_nodes.return_value = []
                mock_executor_instance.migration_plan.return_value = plan
                mock_executor_instance._create_project_state.return_value = Mock(apps=Mock())
                mock_executor_instance.migrate.return_value = Mock(apps=Mock(), clear_delayed_apps_cache=Mock())
                mock_executor_instance.loader.unmigrated_apps = []
                
                out = StringIO()
                call_command('migrate', '--blue', verbosity=1, stdout=out, skip_checks=True)
                
                output = out.getvalue()
                self.assertIn('skipping 1 green migration', output)

