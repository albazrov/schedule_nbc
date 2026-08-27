# 📋 Конфигурация Schedule NBC

## Обзор системы конфигурации

Проект использует **двухуровневую систему конфигурации** для безопасного управления настройками:

### 1. **`config_defaults.json`** (Публичная конфигурация ✅ в GitHub)
Содержит:
- Параметры шаблонов (16:9 и 1:1)
- CSS настройки для наложения текста
- Шрифты и форматирование
- AI промт-шаблоны
- Общие приложения

**Синхронизируется с GitHub** — безопасно делиться всем командой.

### 2. **`config_secret.json`** (Приватная конфигурация ❌ НЕ в GitHub)
Содержит:
- Telegram Bot Token
- OpenAI API ключ
- ID администратора и пользователей
- Пути к RAM-диску для prod/test окружений

**НЕ синхронизируется** — только на локальной машине и сервере.

---

## 🚀 Первоначальная настройка

### Шаг 1: Клонируем репозиторий
```bash
git clone https://github.com/albazrov/schedule_nbc.git
cd schedule_nbc
```

### Шаг 2: Создаём приватный конфиг из шаблона
```bash
cp config_secret.json.example config_secret.json
```

### Шаг 3: Заполняем `config_secret.json`
Откройте файл в редакторе и заполните все поля:

```json
{
  "telegram_bot": {
    "token": "YOUR_BOT_TOKEN_HERE",      // ← Вставьте токен от @BotFather
    "admin_id": 123456789,                // ← Ваш Telegram ID
    "allowed_users": [123456789]          // ← ID разрешённых пользователей
  },
  "openai_api": {
    "api_key": "sk-your-api-key-here"     // ← API ключ для ChatGPT (опционально, если будете использовать AI)
  },
  "environments": {
    "production": {
      "shm_dir": "/dev/shm/schedule_nbc/prod",  // ← Путь RAM-диска для продакшена
      "log_level": "INFO"
    },
    "test": {
      "shm_dir": "/dev/shm/schedule_nbc/test",  // ← Путь RAM-диска для тестов
      "log_level": "DEBUG"
    }
  }
}
```

### Шаг 4: Устанавливаем зависимости
```bash
pip install -r requirements.txt
```

### Шаг 5: Запускаем бота
```bash
# Production окружение (по умолчанию)
./manage.sh start

# Или с явным указанием окружения
./manage.sh start /dev/shm/schedule_nbc/prod production

# Test окружение
./manage.sh start /dev/shm/schedule_nbc/test test
```

---

## 📝 Структура `config_defaults.json`

```json
{
  "templates": {
    "template_16_9": {
      "name": "template_16_9",
      "description": "Шаблон 16:9 (1920x1080) для расписаний",
      "file": "templates/default_16_9.png",
      "format": "16:9",
      "base_width": 1920,
      "base_height": 1080,
      "figma_css": {
        "container_left": 100,       // ← X координата начала текста
        "container_top": 200,        // ← Y координата начала текста
        "font_date_size": 48,        // ← Размер шрифта даты
        "font_event_size": 44,       // ← Размер шрифта события
        "row_height": 120,           // ← Высота строки в пиксель
        "event_column_offset": 300   // ← Отступ колонки события от даты
      },
      "text_colors": {
        "date": [0, 0, 0, 204],      // ← RGBA для даты
        "event": [0, 0, 0, 255]      // ← RGBA для события
      },
      "ai_prompt_template": "Проверь расписание на опечатки...",  // ← Промт для AI
      "output_filename_pattern": "расписание_16_9_({scale})"       // ← Шаблон имени файла
    },
    "template_1_1": {
      // ← Аналогично, но для формата 1:1 (1080x1080)
    }
  },
  "files": {
    "font_regular": "Kraskario.ttf",
    "font_italic": "Kraskario_italic.ttf",
    "excel_name": "data.xlsx",
    "output_name": "schedule_output.png"
  },
  "settings": {
    "force_scale": null,             // ← null = авто, или 1.0, 2.0 и т.д.
    "default_template": "template_16_9"
  },
  "ai_settings": {
    "enabled": false,                // ← AI по умолчанию отключена
    "model": "gpt-4o-mini",
    "timeout": 10
  }
}
```

---

## 🔧 Работа с окружениями

### Production окружение
Используется на рабочем сервере:
```bash
./manage.sh start /dev/shm/schedule_nbc/prod production
```
- RAM-диск: `/dev/shm/schedule_nbc/prod`
- Логи: INFO уровня (минимум информации)

### Test окружение
Используется для разработки и тестирования:
```bash
./manage.sh start /dev/shm/schedule_nbc/test test
```
- RAM-диск: `/dev/shm/schedule_nbc/test`
- Логи: DEBUG уровня (полная информация)

### Кастомная папка RAM-диска
Можно переопределить путь через аргумент скрипта:
```bash
./manage.sh start /custom/ram/path production
```

---

## 🔐 Безопасность

### `.gitignore` исключает:
- ❌ `config_secret.json` — никогда не будет в GitHub
- ✅ `config_defaults.json` — всегда будет в GitHub
- ✅ `config_secret.json.example` — шаблон для новых установок

### Права доступа
При сохранении `config_secret.json` устанавливаются права `0o600`:
```bash
-rw------- config_secret.json  # Только владелец может читать/писать
```

### Никогда не коммитьте:
```bash
# ❌ ПЛОХО
git add config_secret.json
git commit -m "Add bot token"

# ✅ ХОРОШО
cp config_secret.json.example config_secret.json
# Отредактировать и использовать локально
```

---

## 📚 Использование в коде

### Загрузка конфигов

```python
from modules.config_loader import (
    load_config_defaults,
    load_config_secret,
    get_environment_config,
    get_telegram_config,
    get_template_config
)

# Публичная конфигурация
defaults = load_config_defaults()
templates = defaults["templates"]

# Приватная конфигурация
secret = load_config_secret()
bot_token = secret["telegram_bot"]["token"]

# Конфигурация окружения
env = get_environment_config("production")
shm_dir = env["shm_dir"]

# Удобные функции
telegram_cfg = get_telegram_config()  # Автоматическая проверка
template_cfg = get_template_config("template_16_9")  # С проверкой наличия
```

### Сохранение конфигов

```python
from modules.config_loader import (
    save_config_defaults,
    save_config_secret
)

# Сохранить публичную конфигурацию
defaults["settings"]["force_scale"] = 1.5
save_config_defaults(defaults)

# Сохранить приватную конфигурацию
secret["telegram_bot"]["allowed_users"].append(987654321)
save_config_secret(secret)  # Автоматически устанавливает права 0o600
```

---

## 🐛 Решение проблем

### "config_defaults.json не найден"
```bash
# Убедитесь что файл находится в корне проекта
ls -la config_defaults.json

# Если нет, создайте его из резервной копии или GitHub
git checkout config_defaults.json
```

### "config_secret.json не найден"
```bash
# Это НОРМАЛЬНО при первой установке
# Просто скопируйте шаблон:
cp config_secret.json.example config_secret.json

# И заполните значения своих параметров
nano config_secret.json
```

### Ошибка парсинга JSON
```bash
# Проверьте синтаксис JSON
python3 -m json.tool config_defaults.json
python3 -m json.tool config_secret.json

# Если ошибка - отредактируйте файл в VS Code (показывает ошибки синтаксиса)
```

### RAM-диск недоступен
```bash
# Создайте RAM-диск вручную
mkdir -p /dev/shm/schedule_nbc/prod
mkdir -p /dev/shm/schedule_nbc/test

# На некоторых системах может быть другой путь
mount | grep shm
```

---

## 📖 Дальнейшее расширение

### Добавление кастомного шаблона
Отредактируйте `config_defaults.json` и добавьте новый шаблон:
```json
{
  "templates": {
    "template_custom": {
      "name": "template_custom",
      "file": "templates/my_custom_template.png",
      "format": "custom",
      "base_width": 1080,
      "base_height": 1080,
      "figma_css": { /* ... */ }
    }
  }
}
```

### Включение AI проверки текста
В `config_defaults.json` установите:
```json
{
  "ai_settings": {
    "enabled": true,
    "model": "gpt-4o-mini",
    "timeout": 10
  }
}
```

И добавьте ключ OpenAI в `config_secret.json`:
```json
{
  "openai_api": {
    "api_key": "sk-..."
  }
}
```

---

## ✅ Чеклист после первой установки

- [ ] Клонировал репозиторий
- [ ] Скопировал `config_secret.json.example` → `config_secret.json`
- [ ] Заполнил Telegram токен и admin_id
- [ ] Заполнил пути RAM-диска (или оставил дефолтные)
- [ ] Установил зависимости (`pip install -r requirements.txt`)
- [ ] Создал RAM-диск (`mkdir -p /dev/shm/schedule_nbc/{prod,test}`)
- [ ] Запустил бота (`./manage.sh start`)
- [ ] Проверил логи (`./manage.sh logs`)

---

## 📞 Поддержка

Если что-то не работает:
1. Проверьте логи: `./manage.sh logs`
2. Убедитесь что все необходимые поля в `config_secret.json` заполнены
3. Проверьте доступность RAM-диска: `ls -la /dev/shm/schedule_nbc/`
4. Проверьте синтаксис JSON: `python3 -m json.tool config_defaults.json`
