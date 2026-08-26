from aiogram.utils.keyboard import InlineKeyboardBuilder
from modules.config_loader import load_config


def get_settings_keyboard():
    cfg = load_config()
    current_scale = cfg["settings"]["force_scale"] or "Авто"
    current_height = cfg["figma_css"]["row_height"]

    kb = InlineKeyboardBuilder()
    kb.button(
        text=f"🔍 Масштаб: {current_scale}", callback_data="set_scale_menu"
    )
    kb.button(text=f"➖ Шаг ({current_height})", callback_data="height_down")
    kb.button(text="➕ Шаг", callback_data="height_up")

    kb.adjust(1, 2)
    return kb.as_markup()


def get_scale_menu_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📱 1.0 (FullHD)", callback_data="scale_val:1.0")
    kb.button(text="🖥️ 2.0 (4K)", callback_data="scale_val:2.0")
    kb.button(text="🤖 Авто (По макету)", callback_data="scale_val:auto")
    kb.button(text="⬅️ Назад", callback_data="set_main_menu")
    kb.adjust(2, 1, 1)
    return kb.as_markup()
