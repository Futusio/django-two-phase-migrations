"""
Константы и конфигурация для bluegreen миграций.
"""
from django.db.migrations.operations import (
    AlterModelTable,
    AlterUniqueTogether,
    AlterIndexTogether,
    AlterModelOptions,
    AlterField,
    AlterOrderWithRespectTo,
    AlterModelManagers,
)

# Суффиксы для blue/green миграций
BLUE_SUFFIX = '_blue'
GREEN_SUFFIX = '_green'

# Невозможные операции для blue-green разделения
# Эти операции изменяют существующие объекты без возможности создания временной копии
IMPOSSIBLE_OPERATIONS = frozenset({
    AlterModelTable,
    AlterUniqueTogether,
    AlterIndexTogether,
    AlterModelOptions,
    AlterField,
    AlterOrderWithRespectTo,
    AlterModelManagers,
})

# Дефолтные настройки
DEFAULT_NON_INTERACTIVE = False  # По умолчанию интерактивный режим
DEFAULT_INCLUDE_HEADER = True    # Включать заголовок в миграции
DEFAULT_VERBOSITY = 1            # Уровень детальности вывода

# Сообщения
MSG_IMPOSSIBLE_OPERATIONS = (
    "Cannot create blue-green migrations. "
    "Detected impossible operations: {operations}. "
    "These operations cannot be split into blue/green phases. "
    "Please modify your migration or run standard Django migration."
)

MSG_MODEL_NOT_FOUND = "Model '{model}' not found in app '{app}'"
MSG_FIELD_NOT_FOUND = "Field '{field}' not found in model '{model}'"
MSG_INDEX_NOT_FOUND = "Index '{index}' not found in model '{model}'"

