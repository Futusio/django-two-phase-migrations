"""
Вспомогательные функции для тестов bluegreen.
"""

from django.core.management.commands.makemigrations import Migration, MigrationWriter

from bluegreen.processors import BlueGreenMigrationProcessor


def process_migration_for_test(
    migration: Migration, non_interactive: bool = False
) -> tuple[MigrationWriter, MigrationWriter]:
    """
    Обрабатывает миграцию для тестов, разделяя её на blue/green.

    Args:
        migration: Django Migration объект
        non_interactive: Неинтерактивный режим

    Returns:
        Кортеж из (blue_writer, green_writer)

    """
    processor = BlueGreenMigrationProcessor(
        non_interactive=non_interactive,
        verbosity=0,
        dry_run=True,
        include_header=False,
        scriptable=False,
        style=None,
    )
    return processor.process_migration(migration)
