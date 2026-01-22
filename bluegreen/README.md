# Blue-Green Deployment Guide

## Обзор

Blue-Green deployment стратегия для Django миграций позволяет обновлять базу данных без простоя (zero-downtime).

## Использование

### 1. Создание blue-green миграций

```bash
# Создать пару blue/green миграций
python manage.py bluegreen <app_name>

# Это создаст:
# - 0001_initial_blue.py
# - 0001_initial_green.py
```

### 2. Deployment процесс

#### Blue Environment (активное окружение)

```bash
# Запустить blue миграции
python manage.py migrate --blue
```

**Что выполняется:**
- ✅ Миграции с суффиксом `_blue`
- ✅ Обычные миграции без суффиксов (vanilla)
- ❌ Миграции с суффиксом `_green` пропускаются

#### Green Environment (новое окружение)

```bash
# Запустить green миграции
python manage.py migrate --green
```

**Что выполняется:**
- ✅ Миграции с суффиксом `_green`
- ✅ Обычные миграции без суффиксов (vanilla)
- ❌ Миграции с суффиксом `_blue` пропускаются

### 3. Обработка "неразделимых" миграций

Некоторые операции невозможно разделить на blue/green (например, `AlterField`). Для таких случаев:

```bash
# Использовать обычные Django миграции
python manage.py makemigrations
```

Обычные миграции **автоматически выполняются в обоих окружениях** (`--blue` и `--green`).

## Типичный CI/CD пайплайн

### Шаг 1: Blue deployment (без downtime)

```yaml
# Blue server deployment
- name: Run Blue migrations
  run: python manage.py migrate --blue
  
- name: Deploy blue app
  run: deploy_app.sh blue
```

### Шаг 2: Switch traffic to Blue

```yaml
- name: Switch load balancer to Blue
  run: switch_traffic.sh blue
```

### Шаг 3: Green cleanup

```yaml
# Green server cleanup
- name: Run Green migrations
  run: python manage.py migrate --green
```

## Примеры

### Пример 1: Rename Field (разделимая операция)

```python
# models.py
class Product:
    # old_name -> new_name
    new_name = models.CharField(max_length=100)
```

```bash
# Создать blue-green миграции
python manage.py bluegreen catalog

# Blue окружение: добавляет new_name, копирует данные
python manage.py migrate --blue

# Green окружение: удаляет old_name
python manage.py migrate --green
```

### Пример 2: Alter Field (неразделимая операция)

```python
# models.py
class Product:
    name = models.CharField(max_length=200)  # было 100
```

```bash
# Использовать обычные миграции
python manage.py makemigrations

# Миграция выполнится в ОБОИХ окружениях
python manage.py migrate --blue   # выполнит обычную миграцию
python manage.py migrate --green  # выполнит обычную миграцию
```

## Правила фильтрации

| Режим        | `_blue` миграции | `_green` миграции | Vanilla миграции |
|-------------|------------------|-------------------|------------------|
| `--blue`    | ✅ Выполняются   | ❌ Пропускаются   | ✅ Выполняются   |
| `--green`   | ❌ Пропускаются  | ✅ Выполняются    | ✅ Выполняются   |
| Без флагов  | ✅ Выполняются   | ✅ Выполняются    | ✅ Выполняются   |

## Проверка

```bash
# Посмотреть план миграций для blue окружения
python manage.py migrate --blue --plan

# Посмотреть план миграций для green окружения
python manage.py migrate --green --plan
```

## Ограничения

- ❌ Нельзя использовать `--blue` и `--green` одновременно
- ⚠️ Некоторые операции (AlterField, AlterUnique) невозможно разделить

## Troubleshooting

### Ошибка: "Cannot use --blue and --green flags together"

```bash
# Неправильно
python manage.py migrate --blue --green

# Правильно
python manage.py migrate --blue
# ИЛИ
python manage.py migrate --green
```

### Ошибка: "Cannot split migration into blue-green phases"

Используйте обычные Django миграции:

```bash
python manage.py makemigrations
python manage.py migrate  # без флагов
```

