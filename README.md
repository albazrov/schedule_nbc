# 📅 Schedule NBC

Telegram бот для генерации красивых расписаний с использованием Pillow и OpenAI API.

## 📖 Документация

### 🚀 Начало работы
- **[CONFIGURATION.md](CONFIGURATION.md)** — Полная документация системы конфигурации
- **[MIGRATION.md](MIGRATION.md)** — Руководство по переходу с одного конфига на два
- **[CONFIG_EXAMPLES.md](CONFIG_EXAMPLES.md)** — Примеры использования конфигов в коде

### 📋 Быстрая установка

#### Шаг 1: Клонируйте репозиторий
```bash
git clone https://github.com/albazrov/schedule_nbc.git
cd schedule_nbc
```

#### Шаг 2: Создайте приватный конфиг
```bash
cp config_secret.json.example config_secret.json
```

#### Шаг 3: Заполните приватные данные
```bash
nano config_secret.json
```

Минимально необходимо заполнить:
- `telegram_bot.token` — Получите у @BotFather
- `telegram_bot.admin_id` — Ваш Telegram ID

#### Шаг 4: Установите зависимости
```bash
pip install -r requirements.txt
```

#### Шаг 5: Запустите бота
```bash
./manage.sh start
```

---

## 🎨 Возможности

### Основные функции
- ✅ Генерация расписаний из текста
- ✅ Поддержка двух формата: 16:9 (1920x1080) и 1:1 (1080x1080)
- ✅ Кастомизируемые шаблоны и CSS параметры
- ✅ Интеграция с OpenAI для проверки текста
- ✅ Безопасное управление приватными данными

### Поддерживаемые команды
- `/start` — Начало работы
- `/help` — Справка по использованию
- `/config` — Информация о конфигурации (только админ)
- Отправка файла или текста вида: `06 сентября | причастие`

---

## 📁 Структура проекта

```
schedule_nbc/
├── README.md                      # Этот файл
├── CONFIGURATION.md               # Документация конфигурации
├── MIGRATION.md                   # Руководство по миграции
├── CONFIG_EXAMPLES.md             # Примеры использования
│
├── config_defaults.json           # Публичная конфигурация (в GitHub)
├── config_secret.json             # Приватная конфигурация (НЕ в GitHub)
├── config_secret.json.example     # Шаблон приватного конфига
├── .gitignore                     # Исключение приватных файлов
│
├── bot_schedule_nbc.py            # Главный бот (Telegram)
├── sch.py                         # Логика генерации расписаний
├── manage.sh                      # Скрипт управления ботом
├── migrate_config.py              # Скрипт миграции конфигов
│
├── modules/
│   ├── __init__.py
│   ├── config_loader.py           # Загрузка конфигов (NEW!)
│   ├── keyboards.py               # Клавиатуры бота
│   └── ... другие модули
│
├── templates/
│   ├── default_16_9.png           # Шаблон 16:9
│   └── default_1_1.png            # Шаблон 1:1
│
└── requirements.txt               # Python зависимости
```

---

## 🔐 Безопасность

### Двухуровневая система конфигурации

**`config_defaults.json`** (Публичный ✅ в GitHub):
- Параметры шаблонов
- CSS настройки
- Общие параметры приложения

**`config_secret.json`** (Приватный ❌ НЕ в GitHub):
- Telegram Bot Token
- OpenAI API ключ
- ID администратора и пользователей
- Пути окружений

### .gitignore исключает:
```
config_secret.json        # Приватный конфиг (никогда не коммитить!)
config_secret*.json       # Все вариации приватного конфига
.env files                # Переменные окружения
*.log, *.png              # Логи и выходные файлы
```

---

## 🚀 Использование конфигов в коде

### Загрузка конфигов
```python
from modules.config_loader import (
    load_config_defaults,        # Публичная конфигурация
    load_config_secret,          # Приватная конфигурация
    get_telegram_config,         # Получить конфиг Telegram
    get_template_config,         # Получить конфиг шаблона
    get_environment_config       # Получить конфиг окружения
)

# Загрузить публичные параметры
defaults = load_config_defaults()
template_name = defaults["settings"]["default_template"]

# Загрузить приватные данные
secret = load_config_secret()
bot_token = secret["telegram_bot"]["token"]

# Удобные функции
telegram_cfg = get_telegram_config()  # С проверкой наличия
template_cfg = get_template_config("template_16_9")
```

### Сохранение изменений
```python
from modules.config_loader import save_config_defaults, save_config_secret

# Сохранить публичный конфиг
defaults["settings"]["force_scale"] = 1.5
save_config_defaults(defaults)

# Сохранить приватный конфиг (автоматически устанавливает права 0o600)
secret["telegram_bot"]["allowed_users"].append(123456789)
save_config_secret(secret)
```

Подробнее в [CONFIG_EXAMPLES.md](CONFIG_EXAMPLES.md).

---

## 🔧 Команды управления

### Запуск бота
```bash
# Production окружение (по умолчанию)
./manage.sh start

# Test окружение
./manage.sh start /dev/shm/schedule_nbc/test test
```

### Просмотр логов
```bash
./manage.sh logs
```

### Остановка бота
```bash
./manage.sh stop
```

### Перезагрузка
```bash
./manage.sh restart
```

---

## 📊 Примеры использования

### Простой текст
```
Отправьте в бот:
06 сентября | причастие
07 сентября | деепричастие
```

Бот вернёт красивое расписание в виде картинки.

### Выбор шаблона
Через клавиатуру бота можно выбрать нужный формат:
- 16:9 (1920x1080) — для Instagram Stories
- 1:1 (1080x1080) — для квадратного поста

### Изменение масштаба
Используйте кнопки для изменения размера текста и отступов.

---

## 🤖 Интеграция с OpenAI (Опционально)

Если хотите включить автоматическую проверку текста:

1. Установите `OPENAI_API_KEY` в `config_secret.json`
2. Включите в `config_defaults.json`:
   ```json
   {
     "ai_settings": {
       "enabled": true
     }
   }
   ```
3. Перезагрузите бота

AI будет автоматически проверять опечатки и переформатировать даты.

---

## 🐛 Решение проблем

### Бот не запускается
```bash
# Проверьте логи
./manage.sh logs

# Валидируйте JSON конфигов
python3 -m json.tool config_defaults.json
python3 -m json.tool config_secret.json

# Проверьте что токен в config_secret.json
grep "token" config_secret.json | head -1
```

### RAM-диск недоступен
```bash
# Создайте папки для prod и test окружений
mkdir -p /dev/shm/schedule_nbc/{prod,test}
```

### Ошибки при генерации расписания
```bash
# Проверьте что шрифты установлены
ls -la *.ttf

# Проверьте что шаблоны существуют
ls -la templates/
```

Более подробно в [CONFIGURATION.md](CONFIGURATION.md#-решение-проблем).

---

## 📚 Документация

| Документ | Описание |
|----------|---------|
| [CONFIGURATION.md](CONFIGURATION.md) | Полная настройка и структура конфигов |
| [MIGRATION.md](MIGRATION.md) | Переход со старого конфига на новый |
| [CONFIG_EXAMPLES.md](CONFIG_EXAMPLES.md) | Примеры использования в коде |
| [modules/config_loader.py](modules/config_loader.py) | Исходный код модуля загрузки конфигов |

---

## 🔄 Миграция с одного конфига на два

Если вы использовали старую версию с одним `config.json`:

```bash
# Запустите скрипт миграции
python3 migrate_config.py

# Или в режиме preview
python3 migrate_config.py --dry-run
```

Подробнее в [MIGRATION.md](MIGRATION.md).

---

## 📦 Зависимости

```
aiogram >= 3.0           # Telegram Bot API
Pillow >= 9.0            # Работа с изображениями
openpyxl >= 3.0          # Работа с Excel
openai >= 1.0            # OpenAI API (опционально)
```

Установка:
```bash
pip install -r requirements.txt
```

---

## 📝 Лицензия

MIT License - см. [LICENSE](LICENSE) файл

---

## 👨‍💻 Разработка

### Создание новых шаблонов

1. Добавьте новый шаблон в `config_defaults.json`:
   ```json
   {
     "templates": {
       "my_template": {
         "name": "my_template",
         "file": "templates/my_template.png",
         "base_width": 1080,
         "base_height": 1080,
         "figma_css": { /* ... */ }
       }
     }
   }
   ```

2. Положите PNG шаблон в `templates/`

3. Используйте в коде:
   ```python
   from modules.config_loader import get_template_config
   cfg = get_template_config("my_template")
   ```

### Добавление новых параметров

1. Добавьте параметр в `config_defaults.json` (публичный) или `config_secret.json` (приватный)

2. Загрузите в коде:
   ```python
   from modules.config_loader import load_config_defaults
   cfg = load_config_defaults()
   my_param = cfg["my_section"]["my_param"]
   ```

---

## 🆘 Поддержка

- 📖 Прочитайте документацию: [CONFIGURATION.md](CONFIGURATION.md)
- 🔍 Проверьте [CONFIG_EXAMPLES.md](CONFIG_EXAMPLES.md) для примеров
- 🐛 Смотрите логи: `./manage.sh logs`
- 💬 Откройте issue в GitHub

---

**✅ Успехов в использовании Schedule NBC! 🚀**
