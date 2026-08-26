import asyncio
import os
import sys
import argparse
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Импортируем наши собственные модули
from modules.config_loader import load_config, save_config
from modules.data_reader import clean_old_bot_data, get_current_data_file
from modules.keyboards import get_scale_menu_keyboard, get_settings_keyboard

# Импортируем ядро генерации графики
from sch import generate_exact_schedule_fixed

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Настраиваем парсер аргументов командной строки
parser = argparse.ArgumentParser(description="Schedule Telegram Bot")
parser.add_argument("--shm-dir", type=str, help="Путь к временной папке в RAM-диске")
parser.add_argument("--print-shm", action="store_true", help="Вывести итоговый путь SHM и выйти")
args, unknown = parser.parse_known_args()

# Загружаем стартовый конфиг
config = load_config()

# ПРИОРИТЕТ ПУТЕЙ: 1. Ключ запуска --shm-dir -> 2. Параметр в config.json -> 3. Дефолт
if args.shm_dir:
    SHM_DIR = args.shm_dir
else:
    SHM_DIR = config.get("files", {}).get("shm_dir", "/dev/shm/schedule_nbc")

# Если запрошен вывод пути для утилит управления — выводим его и завершаем работу
if args.print_shm:
    print(SHM_DIR)
    sys.exit(0)

# Гарантируем наличие рабочей папки в RAM при старте
os.makedirs(SHM_DIR, exist_ok=True)

BOT_TOKEN = config["telegram_bot"]["token"]
ADMIN_ID = config["telegram_bot"]["admin_id"]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def rebuild_current_schedule():
    """Перезапускает движок генерации с актуальными параметрами"""
    cfg = load_config()
    data_file = get_current_data_file(SHM_DIR, SCRIPT_DIR, cfg["files"]["excel_name"])
    temp_output_path = os.path.join(SHM_DIR, cfg["files"]["output_name"])
    sys.argv = ["sch.py", "-d", data_file, "-o", temp_output_path]
    generate_exact_schedule_fixed()
    return temp_output_path

# === МИДЛВАРЬ ПРОВЕРКИ ДОСТУПА ===
@dp.message.outer_middleware()
async def access_check_middleware(handler, event: types.Message, data):
    if not event.from_user:
        return await handler(event, data)
    user_id = event.from_user.id
    current_config = load_config()
    allowed = current_config["telegram_bot"]["allowed_users"]
    admin = current_config["telegram_bot"]["admin_id"]
    if user_id in allowed or user_id == admin:
        return await handler(event, data)
    if event.text == "/start":
        await event.answer("🔒 Доступ ограничен. Запрос отправлен администратору. Ожидайте...")
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Разрешить", callback_data=f"auth_allow:{user_id}")
        kb.button(text="❌ Заблокировать", callback_data=f"auth_deny:{user_id}")
        username = f"@{event.from_user.username}" if event.from_user.username else "Нет никнейма"
        await bot.send_message(
            chat_id=admin,
            text=f"👤 **Новый запрос доступа!**\n\nИмя: {event.from_user.full_name}\nID: `{user_id}`\nЮзернейм: {username}",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown",
        )
        return
    await event.answer("⛔ У вас нет доступа к этому боту.")

# === ОБРАБОТЧИКИ АВТОРИЗАЦИИ ===
@dp.callback_query(F.data.startswith("auth_"))
async def handle_auth_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет прав.", show_alert=True)
        return
    action, target_id_str = callback.data.split(":")
    target_id = int(target_id_str)
    current_config = load_config()
    if action == "auth_allow":
        if target_id not in current_config["telegram_bot"]["allowed_users"]:
            current_config["telegram_bot"]["allowed_users"].append(target_id)
        save_config(current_config)
        await callback.message.edit_text(f"✅ Пользователь {target_id} добавлен в белый список.")
        try:
            await bot.send_message(target_id, "🎉 Доступ одобрен! Отправляйте файлы или текст.")
        except Exception:
            pass
    elif action == "auth_deny":
        await callback.message.edit_text(f"❌ Запрос {target_id} отклонен.")
    await callback.answer()

# === ОБРАБОТЧИКИ НАСТРОЕК (ИНЛАЙН-КНОПКИ) ===
@dp.callback_query(F.data.in_(["set_scale_menu", "set_main_menu", "height_up", "height_down"]))
async def handle_settings_callbacks(callback: types.CallbackQuery):
    cfg = load_config()
    if callback.data == "set_scale_menu":
        await callback.message.edit_reply_markup(reply_markup=get_scale_menu_keyboard())
        await callback.answer()
        return
    elif callback.data == "set_main_menu":
        await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard())
        await callback.answer()
        return
    if callback.data == "height_up":
        cfg["figma_css"]["row_height"] += 15
    elif callback.data == "height_down":
        cfg["figma_css"]["row_height"] = max(40, cfg["figma_css"]["row_height"] - 15)
    save_config(cfg)
    try:
        updated_file_path = rebuild_current_schedule()
        new_doc = types.InputMediaDocument(
            media=types.FSInputFile(updated_file_path),
            caption="📊 Параметры обновлены! Расписание перегенерировано.",
        )
        await callback.message.edit_media(media=new_doc, reply_markup=get_settings_keyboard())
        await callback.answer("Шаг строк изменен!")
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

@dp.callback_query(F.data.startswith("scale_val:"))
async def handle_scale_selection(callback: types.CallbackQuery):
    val = callback.data.split(":")
    cfg = load_config()
    cfg["settings"]["force_scale"] = None if val == "auto" else float(val)
    save_config(cfg)
    try:
        updated_file_path = rebuild_current_schedule()
        new_doc = types.InputMediaDocument(
            media=types.FSInputFile(updated_file_path),
            caption="📊 Масштаб изменен! Расписание перегенерировано.",
        )
        await callback.message.edit_media(media=new_doc, reply_markup=get_settings_keyboard())
        await callback.answer(f"Установлен масштаб: {val}")
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

# === БАЗОВЫЕ КОМАНДЫ И ПРИЕМ ДАННЫХ ===
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("👋 Доступ подтвержден.\n\nОтправляйте мне файл `.xlsx`, `.txt` или просто напишите текст через разделитель `|`.")

@dp.message(F.document)
async def handle_document(message: types.Message):
    doc = message.document
    filename = doc.file_name
    _, ext = os.path.splitext(filename.lower())
    if ext not in [".xlsx", ".txt"]:
        await message.answer("❌ Пожалуйста, отправьте файл .xlsx или .txt")
        return
    status_msg = await message.answer("📥 Обрабатываю файл в RAM...")
    clean_old_bot_data(SHM_DIR)
    temp_data_name = f"bot_data{ext}"
    temp_data_path = os.path.join(SHM_DIR, temp_data_name)
    try:
        file_info = await bot.get_file(doc.file_id)
        await bot.download_file(file_info.file_path, temp_data_path)
        cfg = load_config()
        temp_output_path = os.path.join(SHM_DIR, cfg["files"]["output_name"])
        sys.argv = ["sch.py", "-d", temp_data_path, "-o", temp_output_path]
        generate_exact_schedule_fixed()
        output_file = types.FSInputFile(temp_output_path)
        await message.answer_document(
            output_file,
            caption="📊 Ваше расписание сгенерировано! Настройки ниже:",
            reply_markup=get_settings_keyboard(),
        )
        await status_msg.delete()
    except Exception as e:
        await message.answer(f"💥 Ошибка генерации: {e}")

@dp.message(F.text)
async def handle_text_input(message: types.Message):
    text = message.text.strip()
    if "|" not in text:
        await message.answer("⚠ Используйте разделитель `|`.\nПример:\n06 сентября | причастие")
        return
    status_msg = await message.answer("✍ Обрабатываю текст в RAM...")
    clean_old_bot_data(SHM_DIR)
    temp_txt_path = os.path.join(SHM_DIR, "bot_text_data.txt")
    with open(temp_txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    try:
        cfg = load_config()
        temp_output_path = os.path.join(SHM_DIR, cfg["files"]["output_name"])
        sys.argv = ["sch.py", "-d", temp_txt_path, "-o", temp_output_path]
        generate_exact_schedule_fixed()
        output_file = types.FSInputFile(temp_output_path)
        await message.answer_document(
            output_file,
            caption="📊 Расписание из текста готово! Настройки ниже:",
            reply_markup=get_settings_keyboard(),
        )
        await status_msg.delete()
    except Exception as e:
        await message.answer(f"💥 Ошибка: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
