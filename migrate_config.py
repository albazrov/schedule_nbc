#!/usr/bin/env python3
"""
Миграционный скрипт для переход на новую двухуровневую систему конфигурации.

Этот скрипт помогает пользователям, которые работали со старой версией проекта,
перейти на новую структуру с разделением config_defaults.json и config_secret.json.

Использование:
    python3 migrate_config.py [--old-config CONFIG_PATH] [--dry-run]

Опции:
    --old-config CONFIG_PATH  : Путь к старому config.json (по умолчанию ./config.json)
    --dry-run                 : Показать что будет сделано без реальных изменений
"""

import json
import os
import sys
import argparse
import shutil
from pathlib import Path


def print_header(text):
    """Выводит заголовок"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_success(text):
    """Выводит сообщение об успехе"""
    print(f"✅ {text}")


def print_warning(text):
    """Выводит предупреждение"""
    print(f"⚠️  {text}")


def print_error(text):
    """Выводит сообщение об ошибке"""
    print(f"❌ {text}")


def print_info(text):
    """Выводит информационное сообщение"""
    print(f"ℹ️  {text}")


def load_old_config(config_path):
    """Загружает старый конфиг"""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print_error(f"Файл {config_path} не найден")
        return None
    except json.JSONDecodeError as e:
        print_error(f"Ошибка парсинга JSON в {config_path}: {e}")
        return None


def extract_defaults(old_config):
    """Извлекает публичные параметры из старого конфига"""
    
    defaults = {
        "templates": {
            "template_16_9": {
                "name": "template_16_9",
                "description": "Шаблон 16:9 (1920x1080) для расписаний",
                "file": "templates/default_16_9.png",
                "format": "16:9",
                "base_width": 1920,
                "base_height": 1080,
                "figma_css": old_config.get("figma_css", {}),
                "text_colors": {
                    "date": [0, 0, 0, 204],
                    "event": [0, 0, 0, 255]
                },
                "ai_prompt_template": "Проверь расписание на опечатки и переформатируй даты в формат 'дд имя_месяца' (например '07 сентября'). Ответь только исправленный текст построчно, без пояснений:\n{text}",
                "output_filename_pattern": "расписание_16_9_({scale})"
            },
            "template_1_1": {
                "name": "template_1_1",
                "description": "Шаблон 1:1 (1080x1080) для расписаний",
                "file": "templates/default_1_1.png",
                "format": "1:1",
                "base_width": 1080,
                "base_height": 1080,
                "figma_css": {
                    "container_left": 60,
                    "container_top": 150,
                    "font_date_size": 40,
                    "font_event_size": 36,
                    "row_height": 100,
                    "event_column_offset": 250
                },
                "text_colors": {
                    "date": [0, 0, 0, 204],
                    "event": [0, 0, 0, 255]
                },
                "ai_prompt_template": "Проверь расписание на опечатки и переформатируй даты в формат 'дд имя_месяца' (например '07 сентября'). Ответь только исправленный текст построчно, без пояснений:\n{text}",
                "output_filename_pattern": "расписание_1_1_({scale})"
            }
        },
        "files": old_config.get("files", {
            "font_regular": "Kraskario.ttf",
            "font_italic": "Kraskario_italic.ttf",
            "excel_name": "data.xlsx",
            "output_name": "schedule_output.png"
        }),
        "settings": old_config.get("settings", {
            "force_scale": None,
            "default_template": "template_16_9"
        }),
        "ai_settings": old_config.get("ai_settings", {
            "enabled": False,
            "model": "gpt-4o-mini",
            "timeout": 10
        })
    }
    
    return defaults


def extract_secrets(old_config):
    """Извлекает приватные параметры из старого конфига"""
    
    secrets = {
        "telegram_bot": old_config.get("telegram_bot", {
            "token": "REPLACE_WITH_TELEGRAM_BOT_TOKEN",
            "admin_id": 0,
            "allowed_users": []
        }),
        "openai_api": old_config.get("openai_api", {
            "api_key": "REPLACE_WITH_OPENAI_API_KEY"
        }),
        "environments": {
            "production": {
                "shm_dir": "/dev/shm/schedule_nbc/prod",
                "log_level": "INFO"
            },
            "test": {
                "shm_dir": "/dev/shm/schedule_nbc/test",
                "log_level": "DEBUG"
            }
        }
    }
    
    # Пытаемся извлечь окружения если они были в старом конфиге
    if "shm_dir" in old_config:
        secrets["environments"]["production"]["shm_dir"] = old_config["shm_dir"]

    return secrets


def build_example_template(secrets):
    """
    Строит config_secret.json.example из структуры приватного конфига,
    заменяя ВСЕ чувствительные значения на плейсхолдеры.

    Этот файл принудительно трекается git-ом (`!config_secret.json.example`
    в .gitignore) и уходит в GitHub, поэтому реальные токены, ID и ключи
    в него попадать не должны — сохраняется только форма структуры.
    """
    return {
        "_WARNING": (
            "⚠️ ЭТО ШАБЛОН — НЕ ВПИСЫВАЙТЕ СЮДА РЕАЛЬНЫЕ ТОКЕНЫ! "
            "ЭТОТ ФАЙЛ ХРАНИТСЯ В GITHUB. / TEMPLATE ONLY — NEVER PUT REAL "
            "SECRETS HERE, THIS FILE IS COMMITTED TO GITHUB."
        ),
        "_HOWTO": (
            "cp config_secret.json.example config_secret.json && "
            "chmod 600 config_secret.json — заполняйте ТОЛЬКО config_secret.json, "
            "он в .gitignore. / Fill in config_secret.json only; it is gitignored."
        ),
        "_CHECK": (
            "Файл проверяется скриптом scripts/check_secrets.py (pre-commit хук + CI). "
            "Коммит с реальным токеном будет заблокирован. / Validated by "
            "scripts/check_secrets.py in the pre-commit hook and CI."
        ),
        "_LEAKED": (
            "Если реальный токен всё же попал в git — сначала отзовите его "
            "(@BotFather /revoke, OpenAI dashboard), удаления коммита недостаточно. / "
            "If a real token leaked, revoke it first; deleting the commit is not enough."
        ),
        "telegram_bot": {
            "token": "REPLACE_WITH_TELEGRAM_BOT_TOKEN",
            "admin_id": 0,
            "allowed_users": []
        },
        "openai_api": {
            "api_key": "REPLACE_WITH_OPENAI_API_KEY"
        },
        # Пути к RAM-диску секретом не являются — переносим как есть
        "environments": secrets.get("environments", {})
    }

def save_config_file(filename, data, script_dir, dry_run=False):
    """Сохраняет файл конфигурации"""
    filepath = os.path.join(script_dir, filename)
    
    if dry_run:
        print_info(f"[DRY-RUN] Будет создан файл: {filepath}")
        print_info(f"[DRY-RUN] Содержимое ({len(json.dumps(data))} байт):")
        return True
    
    try:
        if "secret" in filename:
            # Приватный конфиг: атомарная запись с правами 0600,
            # установленными с момента создания файла — без окна,
            # в котором секреты доступны для чтения другим пользователям,
            # и с сохранением 0600 даже если файл уже существовал.
            _write_secret_atomically(filepath, data)
            print_success(f"Создан {filename} (права: 0o600)")
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print_success(f"Создан {filename}")
        
        return True
    except Exception as e:
        print_error(f"Не удалось сохранить {filename}: {e}")
        return False

def migrate_config(old_config_path, script_dir, dry_run=False):
    """Главная функция миграции"""
    
    print_header("МИГРАЦИЯ КОНФИГУРАЦИИ")
    
    # 1. Загружаем старый конфиг
    print_info("Этап 1: Загрузка старой конфигурации...")
    old_config = load_old_config(old_config_path)
    if not old_config:
        return False
    print_success("Старая конфигурация загружена")
    
    # 2. Проверяем что новые файлы еще не созданы
    print_info("Этап 2: Проверка существующих файлов...")
    
    defaults_path = os.path.join(script_dir, "config_defaults.json")
    secrets_path = os.path.join(script_dir, "config_secret.json")
    
    if os.path.exists(defaults_path):
        print_warning(f"Файл {defaults_path} уже существует")
        if not dry_run:
            backup_path = defaults_path + ".backup"
            shutil.copy2(defaults_path, backup_path)
            print_info(f"Создана резервная копия: {backup_path}")
    
    if os.path.exists(secrets_path):
        print_warning(f"Файл {secrets_path} уже существует")
        if not dry_run:
            print_error("Отмена! Не хотелось бы перезаписать существующий приватный конфиг")
            print_info("Если вы уверены, удалите вручную: rm config_secret.json")
            return False
    
    # 3. Извлекаем публичные параметры
    print_info("Этап 3: Извлечение публичных параметров...")
    defaults = extract_defaults(old_config)
    print_success(f"Извлечено {len(defaults['templates'])} шаблонов")
    
    # 4. Извлекаем приватные параметры
    print_info("Этап 4: Извлечение приватных параметров...")
    secrets = extract_secrets(old_config)
    print_success("Приватные параметры извлечены")
    
    # 5. Сохраняем новые конфиги
    if dry_run:
        print_info("[DRY-RUN] Сохранение будет пропущено")
    else:
        print_info("Этап 5: Сохранение новых конфигов...")
        
        if not save_config_file("config_defaults.json", defaults, script_dir, dry_run):
            return False
        if not save_config_file("config_secret.json", secrets, script_dir, dry_run):
            return False
    
    # 6. Создаём шаблон example файла
    print_info("Этап 6: Создание config_secret.json.example...")
    example_path = os.path.join(script_dir, "config_secret.json.example")
    
    if os.path.exists(example_path):
        print_info("config_secret.json.example уже существует")
    else:
        if not dry_run:
            # ВАЖНО: в шаблон уходят только плейсхолдеры — файл трекается git-ом
            save_config_file(
                "config_secret.json.example",
                build_example_template(secrets),
                script_dir,
                dry_run,
            )
    
    # 7. Итоговая информация
    print_header("РЕЗУЛЬТАТЫ МИГРАЦИИ")
    
    print_info("✅ Миграция успешно завершена!")
    print_info("\nЧто было сделано:")
    print("  1. ✅ Создан config_defaults.json (публичный конфиг)")
    print("  2. ✅ Создан config_secret.json (приватный конфиг)")
    print("  3. ✅ Создан config_secret.json.example (для других пользователей)")
    
    print_info("\nСледующие шаги:")
    print("  1. Проверьте новые конфиги на корректность")
    print("  2. Убедитесь что config_secret.json в .gitignore")
    print("  3. Запустите бота и проверьте что он работает")
    print("  4. Удалите старый config.json если все работает")
    print("\nКоманды:")
    print("  git status                    # Посмотреть изменения")
    print("  ./manage.sh start             # Запустить бота")
    print("  ./manage.sh logs              # Посмотреть логи")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Миграция конфигурации на новую двухуровневую систему"
    )
    parser.add_argument(
        "--old-config",
        type=str,
        default="config.json",
        help="Путь к старому config.json (по умолчанию ./config.json)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Показать что будет сделано без реальных изменений"
    )
    
    args = parser.parse_args()
    
    # Определяем директорию скрипта
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Проверяем что мы в корне проекта
    if not os.path.exists(os.path.join(script_dir, "bot_schedule_nbc.py")):
        print_error("Скрипт должен запускаться из корня проекта (где находится bot_schedule_nbc.py)")
        sys.exit(1)
    
    # Запускаем миграцию
    if args.dry_run:
        print_warning("РЕЖИМ DRY-RUN: Реальные изменения не будут сделаны\n")
    
    success = migrate_config(args.old_config, script_dir, dry_run=args.dry_run)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
