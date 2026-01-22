"""
MigrationPlanFilter - фильтр для blue/green миграций в команде migrate.

Этот класс инкапсулирует логику фильтрации плана миграций,
изолируя её от Django команд.
"""

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from django.db.migrations.executor import MigrationExecutor, MigrationPlan


class MigrationPlanFilter:
    """
    Фильтр для плана миграций в blue/green режиме.

    Используется для фильтрации миграций по суффиксам _blue/_green.
    """

    def __init__(self, blue_mode: bool = False, green_mode: bool = False, verbosity: int = 1, stdout=None) -> None:  # noqa: ANN001
        """
        Инициализирует фильтр.

        Args:
            blue_mode: Режим blue deployment (пропускать _green)
            green_mode: Режим green deployment (пропускать _blue)
            verbosity: Уровень детализации вывода
            stdout: Поток вывода для логирования

        """
        self.blue_mode = blue_mode
        self.green_mode = green_mode
        self.verbosity = verbosity
        self.stdout = stdout

    def filter_plan(self, plan: "MigrationPlan") -> "MigrationPlan":
        """
        Фильтрует план миграций в зависимости от режима.

        Args:
            plan: Исходный план миграций от MigrationExecutor

        Returns:
            Отфильтрованный план миграций

        """
        if self.blue_mode:
            # Blue environment: run _blue migrations + vanilla migrations (without suffix)
            original_count = len(plan)
            filtered_plan = [item for item in plan if not item[0].name.endswith("_green")]
            if self.verbosity >= 1 and original_count != len(filtered_plan) and self.stdout:
                filtered_count = original_count - len(filtered_plan)
                self.stdout.write(f"Blue deployment mode: skipping {filtered_count} green migration(s)\n")
            return filtered_plan
        elif self.green_mode:
            # Green environment: run _green migrations + vanilla migrations (without suffix)
            original_count = len(plan)
            filtered_plan = [item for item in plan if not item[0].name.endswith("_blue")]
            if self.verbosity >= 1 and original_count != len(filtered_plan) and self.stdout:
                filtered_count = original_count - len(filtered_plan)
                self.stdout.write(f"Green deployment mode: skipping {filtered_count} blue migration(s)\n")
            return filtered_plan
        else:
            # Стандартный режим - без фильтрации
            return plan

    def wrap_executor(self, executor: "MigrationExecutor") -> None:
        """
        Оборачивает метод migration_plan у executor для применения фильтра.

        Использует monkey-patching для минимального вмешательства в Django.

        Args:
            executor: MigrationExecutor для обертывания

        """
        original_migration_plan = executor.migration_plan

        def filtered_migration_plan(targets, clean_start=False):  # noqa: ANN001, ANN202
            """Обертка для migration_plan с фильтрацией."""
            plan = original_migration_plan(targets, clean_start)
            return self.filter_plan(plan)

        executor.migration_plan = filtered_migration_plan
