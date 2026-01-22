"""
BlueGreenMigrationProcessor - обработчик для разделения миграций на blue/green фазы.

Этот класс инкапсулирует логику разделения миграций, изолируя её от Django команд.
"""

from pathlib import Path
from typing import Any, Callable

from django.core.management.commands.makemigrations import Migration, MigrationWriter
from django.db import connection
from django.db.migrations.loader import MigrationLoader

from bluegreen.constants import BLUE_SUFFIX, GREEN_SUFFIX, IMPOSSIBLE_OPERATIONS
from bluegreen.exceptions import ImpossibleOperationError
from bluegreen.operations import OperationSplitter


class BlueGreenMigrationProcessor:
    """
    Процессор для разделения стандартных Django миграций на blue/green пары.

    Использует паттерн Strategy для обработки различных типов операций.
    """

    def __init__(
        self,
        non_interactive: bool = False,
        verbosity: int = 1,
        dry_run: bool = False,
        include_header: bool = True,
        scriptable: bool = False,
        style: Any = None,
    ) -> None:
        """
        Инициализирует процессор.

        Args:
            non_interactive: Неинтерактивный режим (для CI/CD)
            verbosity: Уровень детализации вывода
            dry_run: Режим без записи файлов
            include_header: Включать ли заголовок в миграции
            scriptable: Режим для скриптов
            style: Django style для форматирования вывода

        """
        self.non_interactive = non_interactive
        self.verbosity = verbosity
        self.dry_run = dry_run
        self.include_header = include_header
        self.scriptable = scriptable
        self.style = style
        self.written_files: list[str] = []
        self._migration_loader: MigrationLoader | None = None

    def _get_migration_loader(self) -> MigrationLoader:
        """Ленивая инициализация MigrationLoader для проверки существования миграций."""
        if self._migration_loader is None:
            self._migration_loader = MigrationLoader(connection, ignore_no_migrations=True)
        return self._migration_loader

    def _migration_file_exists(self, app_label: str, migration_name: str) -> bool:
        """
        Проверяет, существует ли файл миграции на диске.

        Это необходимо для обработки только что созданных миграций,
        которые ещё не загружены в MigrationLoader.

        Args:
            app_label: Метка приложения
            migration_name: Имя миграции

        Returns:
            True если файл миграции существует

        """
        try:
            from django.apps import apps

            app_config = apps.get_app_config(app_label)
            # Путь к модулю приложения
            app_path = Path(app_config.path)
            migrations_dir = app_path / "migrations"
            migration_file = migrations_dir / f"{migration_name}.py"
            return migration_file.is_file()
        except (LookupError, AttributeError, OSError):
            pass

        return False

    def _fix_dependencies(self, dependencies: list, current_app_label: str, is_green: bool = False) -> list:
        """
        Корректирует dependencies, заменяя базовые имена на _blue или _green версии.

        Проверяет граф миграций И файлы на диске, добавляет правильный суффикс:
        - Blue миграции зависят от BLUE версий (чтобы выполняться вместе в --blue режиме)
        - Green миграции зависят от GREEN версий (чтобы выполняться после blue в --green режиме)
        - Vanilla миграции остаются без изменений

        Args:
            dependencies: Список зависимостей [(app_label, migration_name), ...]
            current_app_label: Метка текущего приложения
            is_green: True для green миграции, False для blue миграции

        Returns:
            Исправленный список зависимостей

        Examples:
            >>> # Blue-green миграция существует, создаем blue
            >>> self._fix_dependencies([('accounts', '0011_paycard')], 'bluegreen', is_green=False)
            [('accounts', '0011_paycard_blue')]

            >>> # Blue-green миграция существует, создаем green
            >>> self._fix_dependencies([('accounts', '0011_paycard')], 'bluegreen', is_green=True)
            [('accounts', '0011_paycard_green')]

            >>> # Vanilla миграция (без blue/green)
            >>> self._fix_dependencies([('bluegreen', '0001_initial')], 'bluegreen', is_green=False)
            [('bluegreen', '0001_initial')]

        """
        fixed_dependencies = []
        loader = self._get_migration_loader()
        target_suffix = GREEN_SUFFIX if is_green else BLUE_SUFFIX

        for dep in dependencies:
            if isinstance(dep, tuple) and len(dep) == 2:
                app_label, migration_name = dep

                # Если миграция уже имеет суффикс _blue или _green, оставляем как есть
                if migration_name.endswith((BLUE_SUFFIX, GREEN_SUFFIX)):
                    fixed_dependencies.append(dep)
                    continue

                # Проверяем, существует ли миграция с целевым суффиксом
                target_name = migration_name + target_suffix
                target_key = (app_label, target_name)

                # Проверяем в графе ИЛИ на диске (для только что созданных миграций)
                if target_key in loader.graph.nodes or self._migration_file_exists(app_label, target_name):
                    # Blue-green миграция существует → зависим от соответствующей версии
                    fixed_dependencies.append(target_key)
                else:
                    # Vanilla миграция (или целевая версия еще не создана) → оставляем как есть
                    fixed_dependencies.append(dep)
            else:
                # Для других типов зависимостей (например, SwappableTuple) оставляем как есть
                fixed_dependencies.append(dep)

        return fixed_dependencies

    def process_migration(self, migration: Migration) -> tuple[MigrationWriter, MigrationWriter]:
        """
        Разделяет одну миграцию на blue и green части.

        Args:
            migration: Django Migration объект

        Returns:
            Кортеж из (blue_writer, green_writer)

        Raises:
            ImpossibleOperationError: Если обнаружены невозможные операции в non_interactive режиме

        """
        # Проверяем наличие невозможных операций
        impossible = any(type(op) in IMPOSSIBLE_OPERATIONS for op in migration.operations)

        if impossible:
            splitter = OperationSplitter(migration.app_label)
            impossible_operations = splitter.detect_impossible_operations(migration.operations)
            raise ImpossibleOperationError(impossible_operations)

        # Разделяем операции на blue и green
        splitter = OperationSplitter(migration.app_label)
        blue_operations, green_operations = splitter.split_operations(migration.operations)

        # Создаем blue миграцию
        blue = Migration(migration.name + BLUE_SUFFIX, migration.app_label)
        # Корректируем dependencies: заменяем базовые имена на _blue версии
        blue.dependencies = self._fix_dependencies(migration.dependencies, migration.app_label, is_green=False)
        blue.operations = blue_operations
        blue.replaces = migration.replaces
        blue.run_before = migration.run_before
        blue.initial = migration.initial

        # Создаем green миграцию
        green = Migration(migration.name + GREEN_SUFFIX, migration.app_label)
        # Green зависит от своей blue миграции
        green.dependencies = [(blue.app_label, blue.name)]
        green.operations = green_operations
        green.replaces = migration.replaces
        green.run_before = migration.run_before
        green.initial = migration.initial

        return MigrationWriter(migration=blue, include_header=self.include_header), MigrationWriter(
            migration=green, include_header=self.include_header
        )

    def write_migration_pair(
        self,
        blue_writer: MigrationWriter,
        green_writer: MigrationWriter,
        directory_created: dict[str, bool],
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        """
        Записывает пару blue/green миграций на диск.

        Args:
            blue_writer: Writer для blue миграции
            green_writer: Writer для green миграции
            directory_created: Словарь для отслеживания созданных директорий
            log_callback: Функция для логирования

        """
        for writer in [blue_writer, green_writer]:
            if self.verbosity >= 1 and log_callback:
                migration_string = writer.path
                # Пытаемся получить относительный путь
                try:
                    from os.path import relpath

                    migration_string = relpath(writer.path)
                except ValueError:
                    pass
                if migration_string.startswith(".."):
                    migration_string = writer.path

                log_callback(f"  {migration_string}\n")
                for operation in writer.migration.operations:
                    log_callback(f"    - {operation.describe()}")

            if not self.dry_run:
                # Записываем миграцию на диск
                migrations_directory = Path(writer.path).parent
                app_label = writer.migration.app_label

                if not directory_created.get(app_label):
                    migrations_directory.mkdir(parents=True, exist_ok=True)
                    init_path = migrations_directory / "__init__.py"
                    if not init_path.is_file():
                        init_path.touch()
                    directory_created[app_label] = True

                migration_string = writer.as_string()
                with open(writer.path, "w", encoding="utf-8") as fh:
                    fh.write(migration_string)
                    self.written_files.append(writer.path)
            elif self.verbosity == 3 and log_callback:
                # Dry run с verbosity 3 - выводим содержимое
                log_callback(f"Full migrations file '{writer.filename}':")
                log_callback(writer.as_string())
