# Примеры использования конфигурации в коде

## 1. Загрузка конфигов в боте

### В `bot_schedule_nbc.py`

```python
import argparse
import os
from modules.config_loader import (
    load_config_defaults,
    get_telegram_config,
    get_environment_config,
    get_template_config,
    get_shm_dir
)

# Парсим аргументы команды
parser = argparse.ArgumentParser(description="Schedule Telegram Bot")
parser.add_argument("--shm-dir", type=str, help="Путь к временной папке в RAM-диске")
parser.add_argument("--env", type=str, default="production", help="Окружение (production/test)")
args, unknown = parser.parse_known_args()

# Получаем Telegram конфигурацию
try:
    telegram_cfg = get_telegram_config()
    BOT_TOKEN = telegram_cfg["token"]
    ADMIN_ID = telegram_cfg["admin_id"]
except ValueError as e:
    print(f"❌ Ошибка конфигурации: {e}")
    exit(1)

# Получаем путь RAM-диска для выбранного окружения
if args.shm_dir:
    SHM_DIR = args.shm_dir
else:
    env_cfg = get_environment_config(args.env)
    SHM_DIR = env_cfg.get("shm_dir", f"/dev/shm/schedule_nbc/{args.env}")

# Гарантируем наличие рабочей папки
os.makedirs(SHM_DIR, exist_ok=True)

# Загружаем публичную конфигурацию
defaults_cfg = load_config_defaults()
DEFAULT_TEMPLATE = defaults_cfg["settings"]["default_template"]

print(f"✅ Конфигурация загружена")
print(f"   Окружение: {args.env}")
print(f"   RAM-диск: {SHM_DIR}")
print(f"   Шаблон по умолчанию: {DEFAULT_TEMPLATE}")
```

---

## 2. Использование конфигов в sch.py

### Загрузка параметров шаблона

```python
from modules.config_loader import (
    load_config_defaults,
    get_template_config,
    get_script_dir
)

def generate_exact_schedule_fixed(template_name=None):
    """Генерирует расписание с поддержкой выбора шаблона"""
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Загружаем конфигурацию
    defaults_cfg = load_config_defaults(script_dir)
    
    # Если шаблон не указан, используем дефолтный
    if template_name is None:
        template_name = defaults_cfg["settings"]["default_template"]
    
    # Получаем конфигурацию конкретного шаблона
    try:
        template_cfg = get_template_config(template_name, script_dir)
    except KeyError as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    # Получаем параметры из конфига шаблона
    template_path = os.path.join(script_dir, template_cfg["file"])
    base_width = template_cfg["base_width"]
    base_height = template_cfg["base_height"]
    css = template_cfg["figma_css"]
    text_colors = template_cfg["text_colors"]
    output_pattern = template_cfg["output_filename_pattern"]
    
    print(f"📋 Используется шаблон: {template_name}")
    print(f"   Формат: {template_cfg['format']}")
    print(f"   Размер: {base_width}x{base_height}")
    print(f"   Позиция текста: ({css['container_left']}, {css['container_top']})")
    
    # ... остальная логика генерации
```

---

## 3. Выбор шаблона через клавиатуру бота

### В `modules/keyboards.py`

```python
from aiogram.utils.keyboard import InlineKeyboardBuilder
from modules.config_loader import load_config_defaults

def get_templates_keyboard():
    """Создает клавиатуру со всеми доступными шаблонами"""
    cfg = load_config_defaults()
    templates = cfg.get("templates", {})
    
    kb = InlineKeyboardBuilder()
    
    for template_id, template_info in templates.items():
        # Формируем текст кнопки с описанием
        button_text = f"{template_info['description']} ({template_info['format']})"
        kb.button(text=button_text, callback_data=f"select_template:{template_id}")
    
    kb.adjust(1)  # По одной кнопке в строку
    return kb.as_markup()

def get_settings_keyboard():
    """Создает клавиатуру настроек (обновленная версия)"""
    cfg = load_config_defaults()
    current_scale = cfg["settings"]["force_scale"] or "Авто"
    current_height = cfg["figma_css"]["row_height"]
    current_template = cfg["settings"]["default_template"]
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🎨 Выбрать шаблон", callback_data="select_template_menu")
    kb.button(text=f"🔍 Масштаб: {current_scale}", callback_data="set_scale_menu")
    kb.button(text=f"➖ Шаг ({current_height})", callback_data="height_down")
    kb.button(text="➕ Шаг", callback_data="height_up")
    
    kb.adjust(1, 3)
    return kb.as_markup()
```

### В `bot_schedule_nbc.py` — обработчик выбора шаблона

```python
from aiogram import F
from aiogram.types import CallbackQuery
from modules.config_loader import load_config_defaults, save_config_defaults

# Сохраняем активный шаблон пользователя (простой способ - в памяти)
# Для production нужна БД
user_templates = {}

@dp.callback_query(F.data.startswith("select_template:"))
async def handle_template_selection(callback: CallbackQuery):
    """Обработчик выбора шаблона"""
    template_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    # Проверяем что шаблон существует
    cfg = load_config_defaults()
    if template_id not in cfg["templates"]:
        await callback.answer(f"❌ Шаблон {template_id} не найден", show_alert=True)
        return
    
    # Сохраняем выбор пользователя
    user_templates[user_id] = template_id
    
    template_info = cfg["templates"][template_id]
    await callback.answer(f"✅ Выбран шаблон: {template_info['description']}")
    await callback.message.edit_text(
        f"📋 Активный шаблон: {template_info['description']}\n"
        f"Формат: {template_info['format']}\n\n"
        f"Отправьте файл или текст для генерации расписания.",
        reply_markup=get_settings_keyboard()
    )

@dp.message(F.text)
async def handle_text_input(message: types.Message):
    """Обработчик текста с поддержкой выбранного шаблона"""
    user_id = message.from_user.id
    
    # Получаем выбранный пользователем шаблон или дефолтный
    cfg = load_config_defaults()
    template_name = user_templates.get(user_id, cfg["settings"]["default_template"])
    
    text = message.text.strip()
    if "|" not in text:
        await message.answer("⚠ Используйте разделитель `|`.\nПример:\n06 сентября | причастие")
        return
    
    status_msg = await message.answer(f"✍ Обрабатываю текст используя {template_name}...")
    
    # Генерируем расписание с выбранным шаблоном
    # ... логика генерации с передачей template_name
```

---

## 4. Изменение настроек и сохранение конфига

### Обновление параметров шаблона

```python
from modules.config_loader import (
    load_config_defaults,
    save_config_defaults,
    get_template_config
)

def update_template_settings(template_name, new_css_params):
    """Обновляет CSS параметры конкретного шаблона"""
    
    # Загружаем текущую конфигурацию
    cfg = load_config_defaults()
    
    # Проверяем существование шаблона
    if template_name not in cfg["templates"]:
        raise ValueError(f"Шаблон {template_name} не найден")
    
    # Обновляем CSS параметры
    cfg["templates"][template_name]["figma_css"].update(new_css_params)
    
    # Сохраняем обновленную конфигурацию
    save_config_defaults(cfg)
    
    print(f"✅ Параметры шаблона {template_name} обновлены")

# Пример использования
update_template_settings("template_16_9", {
    "container_left": 120,
    "container_top": 250,
    "row_height": 140
})
```

### Обновление параметров масштаба (callback из бота)

```python
@dp.callback_query(F.data.startswith("scale_val:"))
async def handle_scale_selection(callback: CallbackQuery):
    """Обновляет масштаб и пересохраняет конфиг"""
    val = callback.data.split(":")[1]
    
    # Загружаем конфигурацию
    cfg = load_config_defaults()
    
    # Обновляем параметр масштаба
    cfg["settings"]["force_scale"] = None if val == "auto" else float(val)
    
    # Сохраняем обновленный конфиг
    save_config_defaults(cfg)
    
    # Перегенерируем расписание с новым масштабом
    try:
        updated_file_path = rebuild_current_schedule()
        new_doc = types.InputMediaDocument(
            media=types.FSInputFile(updated_file_path),
            caption="📊 Масштаб изменен! Расписание перегенерировано.",
        )
        await callback.message.edit_media(media=new_doc, reply_markup=get_settings_keyboard())
        await callback.answer(f"✅ Установлен масштаб: {val}")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)
```

---

## 5. Работа с приватной конфигурацией

### Управление списком разрешённых пользователей

```python
from modules.config_loader import (
    load_config_secret,
    save_config_secret
)

def add_user_to_whitelist(user_id):
    """Добавляет пользователя в список разрешённых"""
    
    # Загружаем приватный конфиг
    secret_cfg = load_config_secret()
    
    # Добавляем пользователя если его еще нет
    if user_id not in secret_cfg["telegram_bot"]["allowed_users"]:
        secret_cfg["telegram_bot"]["allowed_users"].append(user_id)
        
        # Сохраняем обновленный конфиг
        save_config_secret(secret_cfg)
        print(f"✅ Пользователь {user_id} добавлен в белый список")
        return True
    else:
        print(f"⚠️  Пользователь {user_id} уже в списке")
        return False

# Пример использования в боте
@dp.callback_query(F.data.startswith("auth_allow:"))
async def handle_auth_callback(callback: CallbackQuery):
    """Одобряет доступ новому пользователю"""
    action, target_id_str = callback.data.split(":")
    target_id = int(target_id_str)
    
    # Добавляем в белый список
    if add_user_to_whitelist(target_id):
        await callback.message.edit_text(f"✅ Пользователь {target_id} добавлен в белый список.")
        try:
            await bot.send_message(target_id, "🎉 Доступ одобрен! Отправляйте файлы или текст.")
        except Exception:
            pass
    
    await callback.answer()
```

---

## 6. Вспомогательные функции для конфигов

### Валидация конфигурации

```python
from modules.config_loader import load_config_defaults, get_template_config

def validate_config():
    """Проверяет корректность всей конфигурации"""
    
    print("🔍 Проверяю конфигурацию...")
    
    try:
        # Загружаем конфиг
        cfg = load_config_defaults()
        
        # Проверяем наличие шаблонов
        templates = cfg.get("templates", {})
        if not templates:
            print("❌ Ошибка: нет шаблонов в конфиге")
            return False
        
        # Проверяем каждый шаблон
        for template_name in templates:
            template_cfg = get_template_config(template_name)
            
            # Проверяем обязательные поля
            required_fields = ["name", "file", "base_width", "base_height", "figma_css"]
            for field in required_fields:
                if field not in template_cfg:
                    print(f"❌ Ошибка: отсутствует поле {field} в шаблоне {template_name}")
                    return False
            
            # Проверяем что файл шаблона существует
            template_path = os.path.join(get_script_dir(), template_cfg["file"])
            if not os.path.exists(template_path):
                print(f"❌ Ошибка: файл шаблона не найден: {template_path}")
                return False
        
        print(f"✅ Конфигурация валидна ({len(templates)} шаблонов)")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка валидации: {e}")
        return False

# Использование при старте бота
if __name__ == "__main__":
    if not validate_config():
        exit(1)
    asyncio.run(main())
```

---

## 7. Вывод информации о конфигурации

### Команда для администратора

```python
@dp.message(Command("config"))
async def show_config(message: types.Message):
    """Показывает информацию о текущей конфигурации (только админ)"""
    
    if message.from_user.id != ADMIN_ID:
        await message.answer("🔒 Эта команда доступна только администратору")
        return
    
    cfg = load_config_defaults()
    templates = cfg.get("templates", {})
    
    info = "📋 **Текущая конфигурация:**\n\n"
    info += f"🎨 **Доступные шаблоны ({len(templates)}):**\n"
    
    for template_id, template_info in templates.items():
        info += f"  • `{template_id}`\n"
        info += f"    └─ {template_info['description']}\n"
        info += f"    └─ Формат: {template_info['format']}\n"
    
    info += f"\n📊 **Текущие настройки:**\n"
    info += f"  • Масштаб: {cfg['settings']['force_scale'] or 'Авто'}\n"
    info += f"  • Шаблон по умолчанию: {cfg['settings']['default_template']}\n"
    
    info += f"\n🤖 **AI:**\n"
    info += f"  • Включена: {'Да' if cfg['ai_settings']['enabled'] else 'Нет'}\n"
    info += f"  • Модель: {cfg['ai_settings']['model']}\n"
    
    await message.answer(info, parse_mode="Markdown")
```

---

## 📝 Резюме

Теперь при использовании конфигов в коде:

1. **Загружайте конфиги** правильными функциями
2. **Проверяйте наличие** нужных параметров
3. **Сохраняйте конфиги** после изменений
4. **Не коммитьте** приватные данные
5. **Валидируйте** конфигурацию при старте
