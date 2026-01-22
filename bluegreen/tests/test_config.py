"""
Тесты для конфигурации и типов данных.
"""
from django.test import TestCase
from django.db.migrations.operations import CreateModel

from bluegreen.config import (
    MigrationPhase,
    ImpossibleOperationPolicy,
    SplitResult,
    BlueGreenConfig
)


class MigrationPhaseTest(TestCase):
    """Тесты для enum MigrationPhase."""
    
    def test_phase_values(self):
        """✅ Фазы имеют правильные значения."""
        self.assertEqual(MigrationPhase.BLUE.value, "blue")
        self.assertEqual(MigrationPhase.GREEN.value, "green")
        self.assertEqual(MigrationPhase.BOTH.value, "both")


class ImpossibleOperationPolicyTest(TestCase):
    """Тесты для enum ImpossibleOperationPolicy."""
    
    def test_policy_values(self):
        """✅ Политики имеют правильные значения."""
        self.assertEqual(ImpossibleOperationPolicy.ASK.value, "ask")
        self.assertEqual(ImpossibleOperationPolicy.FAIL.value, "fail")
        self.assertEqual(ImpossibleOperationPolicy.IGNORE.value, "ignore")
        self.assertEqual(ImpossibleOperationPolicy.SKIP.value, "skip")


class SplitResultTest(TestCase):
    """Тесты для dataclass SplitResult."""
    
    def test_default_initialization(self):
        """✅ SplitResult инициализируется с пустыми списками."""
        result = SplitResult()
        
        self.assertEqual(result.blue_operations, [])
        self.assertEqual(result.green_operations, [])
        self.assertFalse(result.is_impossible)
        self.assertIsNone(result.reason)
    
    def test_has_blue_operations(self):
        """✅ has_blue_operations работает корректно."""
        result = SplitResult(blue_operations=[CreateModel('Test', [])])
        
        self.assertTrue(result.has_blue_operations())
        self.assertFalse(result.has_green_operations())
    
    def test_has_green_operations(self):
        """✅ has_green_operations работает корректно."""
        from django.db.migrations.operations import DeleteModel
        
        result = SplitResult(green_operations=[DeleteModel('Test')])
        
        self.assertFalse(result.has_blue_operations())
        self.assertTrue(result.has_green_operations())
    
    def test_impossible_operation(self):
        """✅ Невозможная операция отмечается флагом."""
        result = SplitResult(is_impossible=True, reason="AlterField не поддерживается")
        
        self.assertTrue(result.is_impossible)
        self.assertEqual(result.reason, "AlterField не поддерживается")


class BlueGreenConfigTest(TestCase):
    """Тесты для dataclass BlueGreenConfig."""
    
    def test_default_configuration(self):
        """✅ BlueGreenConfig имеет правильные дефолты."""
        config = BlueGreenConfig()
        
        self.assertEqual(config.phase, MigrationPhase.BOTH)
        self.assertFalse(config.non_interactive)
        self.assertEqual(config.impossible_policy, ImpossibleOperationPolicy.ASK)
        self.assertFalse(config.dry_run)
        self.assertFalse(config.verbose)
    
    def test_custom_configuration(self):
        """✅ BlueGreenConfig принимает кастомные значения."""
        config = BlueGreenConfig(
            phase=MigrationPhase.BLUE,
            non_interactive=True,
            impossible_policy=ImpossibleOperationPolicy.FAIL,
            dry_run=True,
            verbose=True
        )
        
        self.assertEqual(config.phase, MigrationPhase.BLUE)
        self.assertTrue(config.non_interactive)
        self.assertEqual(config.impossible_policy, ImpossibleOperationPolicy.FAIL)
        self.assertTrue(config.dry_run)
        self.assertTrue(config.verbose)

