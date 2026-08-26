import datetime
import os


def clean_old_bot_data(shm_dir):
    """Очищает старые временные файлы данных из RAM"""
    for f in os.listdir(shm_dir):
        if f.startswith("bot_data.") or f == "bot_text_data.txt":
            try:
                os.remove(os.path.join(shm_dir, f))
            except OSError:
                pass


def get_current_data_file(shm_dir, script_dir, default_excel_name):
    """Ищет актуальный файл данных в RAM или возвращает дефолтный"""
    for f in os.listdir(shm_dir):
        if f.startswith("bot_data.") or f == "bot_text_data.txt":
            return os.path.join(shm_dir, f)
    return os.path.join(script_dir, default_excel_name)
