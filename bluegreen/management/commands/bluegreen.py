import os
from itertools import chain

from django.core.management.commands.makemigrations import (
    Command as MakeMigrationsCommand,
    MigrationWriter,
    Migration
)

from ...exceptions import ImpossibleOperationError
from ...constants import IMPOSSIBLE_OPERATIONS, BLUE_SUFFIX, GREEN_SUFFIX
from ...operations import OperationSplitter


class PatchedMigrationWriter(MigrationWriter):

    """
    # Notes:
    - If we rename model it's creating a new indexes

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def blue_green(self, operation):
        """Делегирует разделение операций OperationSplitter."""
        splitter = OperationSplitter(self.migration.app_label)
        return splitter.split_operation(operation)

    def create_blue(self, operations_lst: list[tuple]) -> Migration:
        """Создает Blue-фазу миграции (создание новых объектов)."""
        operations = list(filter(None, chain.from_iterable(operations_lst)))
        migration = Migration(self.migration.name + BLUE_SUFFIX, self.migration.app_label)
        migration.dependencies = self.migration.dependencies
        migration.operations = operations
        migration.replaces = self.migration.replaces
        migration.run_before = self.migration.run_before
        migration.initial = self.migration.initial
        # migration.path = self.migration.path
        return migration

    def create_green(self, migration_blue: Migration, lst: list) -> Migration:
        """Создает Green-фазу миграции (удаление старых объектов)."""
        operations = list(filter(None, chain.from_iterable(lst)))
        migration = Migration(self.migration.name + GREEN_SUFFIX, self.migration.app_label)
        migration.dependencies = [(migration_blue.app_label, migration_blue.name), ]
        migration.operations = operations
        # migration.path = self.migration.path
        migration.replaces = self.migration.replaces
        migration.run_before = self.migration.run_before
        migration.initial = self.migration.initial
        return migration

    def split_migrations(self, impossible=False, non_interactive=False):
        """
        Разделяет миграцию на Blue и Green части.
        
        Args:
            impossible: Обнаружены невозможные операции
            non_interactive: Неинтерактивный режим (для CI/CD)
        
        Raises:
            ImpossibleOperationError: Если обнаружены невозможные операции в non_interactive режиме
        """
        if impossible:
            # Невозможные операции нельзя разделить на blue-green
            # Пользователь должен использовать обычные Django миграции
            impossible_ops = [
                op.__class__.__name__ 
                for op in self.migration.operations 
                if op.__class__ in IMPOSSIBLE_OPERATIONS
            ]
            error_msg = (
                f"Cannot split migration into blue-green phases.\n\n"
                f"Detected operations that cannot be split: {', '.join(impossible_ops)}\n"
                f"These operations require downtime and must use standard Django migrations.\n\n"
                f"Solution: Use 'python manage.py makemigrations' instead of 'bluegreen' command."
            )
            raise ImpossibleOperationError(error_msg)
        blue_list, green_list = list(), list()
        for operation in self.migration.operations:
            blue, green = self.blue_green(operation)
            blue_list.append(blue)
            green_list.append(green)
        blue = self.create_blue(blue_list)
        green = self.create_green(blue, green_list)
        a, b = MigrationWriter(migration=blue), MigrationWriter(migration=green)
        return a, b


class Command(MakeMigrationsCommand):
    help = "Create blue-green migration pairs for zero-downtime deployments"
    
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--non-interactive',
            action='store_true',
            dest='non_interactive',
            default=False,
            help='Run in non-interactive mode (fail on impossible operations instead of prompting)',
        )
    
    def handle(self, *args, **options):
        """Override handle to store non_interactive option."""
        self.non_interactive = options.get('non_interactive', False)
        return super().handle(*args, **options)

    def write_migration_files(self, changes):
        """
        Take a changes dict and write them out as migration files.
        """
        directory_created = {}
        non_interactive = getattr(self, 'non_interactive', False)
        
        for app_label, app_migrations in changes.items():
            if self.verbosity >= 1:
                self.log(self.style.MIGRATE_HEADING("Migrations for '%s':" % app_label))
            for i, migration in enumerate(app_migrations):
                writer = PatchedMigrationWriter(migration, self.include_header)
                # Проверяем типы операций (type(op)), а не сами экземпляры
                impossible = any(type(op) in IMPOSSIBLE_OPERATIONS for op in migration.operations)
                for writer in writer.split_migrations(impossible, non_interactive=non_interactive):
                    if self.verbosity >= 1:
                        try:
                            migration_string = os.path.relpath(writer.path)
                        except ValueError:
                            migration_string = writer.path
                        if migration_string.startswith(".."):
                            migration_string = writer.path
                        self.log("  %s\n" % self.style.MIGRATE_LABEL(migration_string))
                        for operation in migration.operations:
                            self.log("    - %s" % operation.describe())
                        if self.scriptable:
                            self.stdout.write(migration_string)
                    if not self.dry_run:
                        # Write the migrations file to the disk.
                        migrations_directory = os.path.dirname(writer.path)
                        if not directory_created.get(app_label):
                            os.makedirs(migrations_directory, exist_ok=True)
                            init_path = os.path.join(migrations_directory, "__init__.py")
                            if not os.path.isfile(init_path):
                                open(init_path, "w").close()
                            # We just do this once per app
                            directory_created[app_label] = True
                        migration_string = writer.as_string()
                        with open(writer.path, "w", encoding="utf-8") as fh:
                            fh.write(migration_string)
                            self.written_files.append(writer.path)
                    elif self.verbosity == 3:
                        # Alternatively, makemigrations --dry-run --verbosity 3
                        # will log the migrations rather than saving the file to
                        # the disk.
                        self.log(
                            self.style.MIGRATE_HEADING(
                                "Full migrations file '%s':" % writer.filename
                            )
                        )
                        self.log(writer.as_string())
