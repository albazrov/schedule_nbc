# 📚 Руководство по миграции конфигурации

## Что изменилось?

Проект перешёл на **двухуровневую систему конфигурации**:

| Было | Стало |
|------|-------|
| Один `config.json` с мешаниной всех параметров | Два отдельных файла |
| | ✅ `config_defaults.json` — публичный (в GitHub) |
| | ❌ `config_secret.json` — приватный (в .gitignore) |

**Преимущества:**
- 🔐 **Безопасность**: токены не попадут в GitHub
- 👥 **Командная работа**: настройки можно синхронизировать, секреты — нет
- 🚀 **Гибкость**: легко добавлять новые шаблоны
- 🔄 **Окружения**: prod и test с разными путями RAM

---

## 🚀 Быстрая миграция (Автоматическая)

### Шаг 1: Обновите репозиторий
```bash
git pull origin feature/config-restructuring
# или если вы на ветке test:
git fetch origin
git checkout feature/config-restructuring
```

### Шаг 2: Запустите скрипт миграции
```bash
python3 migrate_config.py
```

**Скрипт автоматически:**
- ✅ Прочитает старый `config.json`
- ✅ Разделит его на два файла
- ✅ Создаст `config_secret.json` с вашими приватными данными
- ✅ Создаст `config_secret.json.example` для других пользователей
- ✅ Сделает резервную копию старого конфига

### Шаг 3: Проверьте результат
```bash
ls -la config_*.json
# Должно быть:
# -rw-r--r-- config_defaults.json
# -rw------- config_secret.json           (права 0o600)
# -rw-r--r-- config_secret.json.example
```

### Шаг 4: Подтвердите что всё работает
```bash
# Проверьте что конфиги валидны
python3 -c "from modules.config_loader import load_config_defaults; print('✅ config_defaults.json OK')"
python3 -c "from modules.config_loader import load_config_secret; print('✅ config_secret.json OK')"

# Запустите бота
./manage.sh start
./manage.sh logs
```

### Шаг 5 (опционально): Удалите старый конфиг
```bash
# Когда всё работает, удалите старый файл
rm config.json
```

---

## 🔍 Тестовый режим (Dry-Run)

Если хотите сначала посмотреть что будет сделано:

```bash
python3 migrate_config.py --dry-run
```

Выведет план действий без реальных изменений.

---

## 📝 Ручная миграция (Если автоматическая не прошла)

### Шаг 1: Создайте `config_defaults.json`
```bash
cat > config_defaults.json << 'EOF'
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
        "container_left": 100,
        "container_top": 200,
        "font_date_size": 48,
        "font_event_size": 44,
        "row_height": 120,
        "event_column_offset": 300
      },
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
  "files": {
    "font_regular": "Kraskario.ttf",
    "font_italic": "Kraskario_italic.ttf",
    "excel_name": "data.xlsx",
    "output_name": "schedule_output.png"
  },
  "settings": {
    "force_scale": null,
    "default_template": "template_16_9"
  },
  "ai_settings": {
    "enabled": false,
    "model": "gpt-4o-mini",
    "timeout": 10
  }
}
EOF
```

### Шаг 2: Скопируйте пример приватного конфига
```bash
cp config_secret.json.example config_secret.json
```

### Шаг 3: Заполните приватные данные
Откройте `config_secret.json` и заполните:
- `telegram_bot.token` — токен от @BotFather
- `telegram_bot.admin_id` — ваш Telegram ID
- `telegram_bot.allowed_users` — ID разрешённых пользователей
- `openai_api.api_key` — (опционально) API ключ OpenAI

```bash
nano config_secret.json
```

### Шаг 4: Установите права на приватный файл
```bash
chmod 600 config_secret.json
```

### Шаг 5: Проверьте что старый конфиг совместим
Если у вас были кастомные параметры в старом `config.json`, скопируйте их:

```python
# Если в старом config.json были кастомные figma_css параметры:
# Скопируйте их в соответствующий шаблон в config_defaults.json
```

---

## ✅ Контрольный список после миграции

- [ ] Запустил миграцию или выполнил ручную миграцию
- [ ] Проверил что `config_defaults.json` существует и валиден
- [ ] Проверил что `config_secret.json` существует (и в .gitignore)
- [ ] Заполнил приватные данные в `config_secret.json`
- [ ] Установил права `chmod 600 config_secret.json`
- [ ] Запустил бота и проверил логи
- [ ] Удалил старый `config.json`
- [ ] Закоммитил изменения (без config_secret.json!)

---

## 🔧 Если что-то сломалось

### Ошибка: "config_defaults.json не найден"
```bash
git checkout config_defaults.json
```

### Ошибка: "config_secret.json не найден" (но это ОК при первом запуске)
```bash
# Просто создайте его из шаблона:
cp config_secret.json.example config_secret.json
nano config_secret.json  # Заполните данные
chmod 600 config_secret.json
```

### Ошибка: "Невалидный JSON"
```bash
# Проверьте синтаксис
python3 -m json.tool config_defaults.json
python3 -m json.tool config_secret.json
```

### Ошибка: "Токен бота не найден"
```bash
# Убедитесь что заполнили config_secret.json:
grep -i "token" config_secret.json
# Должно быть значение, не "YOUR_BOT_TOKEN_HERE"
```

### Ошибка: "RAM-диск недоступен"
```bash
# Создайте папки для prod и test окружений
mkdir -p /dev/shm/schedule_nbc/{prod,test}
chmod 755 /dev/shm/schedule_nbc/{prod,test}
```

---

## 🔐 Безопасность: Проверьте .gitignore

Убедитесь что приватный конфиг в исключениях:

```bash
cat .gitignore | grep -i "config_secret"
# Должно вывести: config_secret.json
```

**НИКОГДА не коммитьте:**
```bash
# ❌ ПЛОХО
git add config_secret.json
git commit -m "Add config"

# ✅ ХОРОШО
git status  # Проверить что config_secret.json не в staged changes
git commit -m "Add migration"
```

---

## 📚 Дополнительная информация

- 📖 [CONFIGURATION.md](CONFIGURATION.md) — полная документация конфигов
- 💻 [CONFIG_EXAMPLES.md](CONFIG_EXAMPLES.md) — примеры использования в коде
- 🔍 [modules/config_loader.py](modules/config_loader.py) — исходный код модуля

---

## 🆘 Нужна помощь?

Если что-то не работает:

1. **Проверьте логи:**
   ```bash
   ./manage.sh logs
   ```

2. **Валидируйте JSON:**
   ```bash
   python3 -m json.tool config_defaults.json
   python3 -m json.tool config_secret.json
   ```

3. **Проверьте права доступа:**
   ```bash
   ls -la config_*.json
   # config_secret.json должен быть: -rw------- (600)
   ```

4. **Запустите миграцию с --dry-run:**
   ```bash
   python3 migrate_config.py --dry-run
   ```

5. **Откатитесь к старому конфигу (если нужно):**
   ```bash
   git checkout config.json
   # Затем запустите старую версию бота
   ```

---

## 🎉 После успешной миграции

**Команды для синхронизации с командой:**

```bash
# Покажите что обновилось
git diff config_defaults.json

# Закоммитьте только публичный конфиг
git add config_defaults.json
git commit -m "refactor: split configuration into public and private"

# Убедитесь что config_secret.json НЕ будет закоммичен
git status
# Должно быть: "config_secret.json" в "Untracked files" или не видно вообще

# Отправьте на сервер
git push origin feature/config-restructuring
```

**Для других пользователей:**
1. Они обновят репозиторий: `git pull`
2. Скопируют шаблон: `cp config_secret.json.example config_secret.json`
3. Заполнят свои данные в `config_secret.json`
4. Запустят бота

---

**✅ Поздравляем! Миграция завершена! 🚀**
