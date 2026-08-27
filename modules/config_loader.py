import json
import os
from pathlib import Path


def get_script_dir():
    """Возвращает директорию проекта"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config_defaults(script_dir=None):
    """
    Загружает публичную конфигурацию (синхронизируется с GitHub).
    Содержит параметры шаблонов, CSS, настройки AI и другие нечувствительные данные.
    
    Args:
        script_dir: директория проекта (если None, используется текущая)
    
    Returns:
        dict: конфигурация из config_defaults.json
    
    Raises:
        FileNotFoundError: если config_defaults.json не найден
    """
    if script_dir is None:
        script_dir = get_script_dir()
    
    config_path = os.path.join(script_dir, "config_defaults.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"\n[!] Файл публичной конфигурации не найден: {config_path}\n"
            f"[!] Пожалуйста, убедитесь что config_defaults.json существует в корне проекта."
        )
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Ошибка парсинга JSON в {config_path}: {e}")


def load_config_secret(script_dir=None):
    """
    Загружает приватную конфигурацию (НЕ синхронизируется с GitHub).
    Содержит токены, API ключи, ID пользователей и пути к RAM-диску.
    
    Args:
        script_dir: директория проекта (если None, используется текущая)
    
    Returns:
        dict: конфигурация из config_secret.json или пустой dict если файл не найден
    
    Note:
        Возвращает пустой dict вместо выброса исключения для мягкого падения.
        Если какие-то значения критичны, их использующий код должен проверить наличие.
    """
    if script_dir is None:
        script_dir = get_script_dir()
    
    config_path = os.path.join(script_dir, "config_secret.json")
    if not os.path.exists(config_path):
        print(
            f"⚠️  [NOTICE] Файл приватной конфигурации не найден: {config_path}\n"
            f"⚠️  [NOTICE] Используйте config_secret.json.example как шаблон.\n"
            f"⚠️  [NOTICE] Скопируйте: cp {os.path.join(script_dir, 'config_secret.json.example')} {config_path}"
        )
        return {}
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"⚠️  Ошибка парсинга JSON в {config_path}: {e}")
        return {}


def save_config_defaults(config, script_dir=None):
    """
    Сохраняет публичную конфигурацию в config_defaults.json.
    
    Args:
        config: dict с конфигурацией
        script_dir: директория проекта (если None, используется текущая)
    
    Raises:
        IOError: если не удалось записать файл
    """
    if script_dir is None:
        script_dir = get_script_dir()
    
    config_path = os.path.join(script_dir, "config_defaults.json")
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"✅ Конфигурация сохранена: {config_path}")
    except IOError as e:
        raise IOError(f"Ошибка при сохранении {config_path}: {e}")


def save_config_secret(config, script_dir=None):
    """
    Сохраняет приватную конфигурацию в config_secret.json.
    
    Args:
        config: dict с конфигурацией
        script_dir: директория проекта (если None, используется текущая)
    
    Raises:
        IOError: если не удалось записать файл
    """
    if script_dir is None:
        script_dir = get_script_dir()
    
    config_path = os.path.join(script_dir, "config_secret.json")
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        # Ограничиваем права доступа для приватного файла (только владелец может читать)
        os.chmod(config_path, 0o600)
        print(f"✅ Приватная конфигурация сохранена: {config_path}")
    except IOError as e:
        raise IOError(f"Ошибка при сохранении {config_path}: {e}")


def get_environment_config(env_name="production", script_dir=None):
    """
    Получает конфигурацию для конкретного окружения (production/test).
    Содержит пути к RAM-диску и уровень логирования.
    
    Args:
        env_name: имя окружения ("production" или "test")
        script_dir: директория проекта (если None, используется текущая)
    
    Returns:
        dict: конфигурация окружения
    
    Example:
        >>> env_cfg = get_environment_config("production")
        >>> print(env_cfg["shm_dir"])
        /dev/shm/schedule_nbc/prod
    """
    secret_cfg = load_config_secret(script_dir)
    environments = secret_cfg.get("environments", {})
    
    env_config = environments.get(env_name, {})
    if not env_config:
        print(f"⚠️  Конфигурация для окружения '{env_name}' не найдена в config_secret.json")
        # Возвращаем дефолтные значения
        return {
            "shm_dir": f"/dev/shm/schedule_nbc/{env_name}",
            "log_level": "INFO"
        }
    
    return env_config


def get_shm_dir(env_name="production", script_dir=None):
    """
    Получает путь к RAM-диску для конкретного окружения.
    
    Args:
        env_name: имя окружения ("production" или "test")
        script_dir: директория проекта (если None, используется текущая)
    
    Returns:
        str: путь к RAM-диску
    
    Example:
        >>> shm = get_shm_dir("production")
        >>> print(shm)
        /dev/shm/schedule_nbc/prod
    """
    env_cfg = get_environment_config(env_name, script_dir)
    return env_cfg.get("shm_dir", f"/dev/shm/schedule_nbc/{env_name}")


def get_telegram_config(script_dir=None):
    """
    Получает конфигурацию Telegram бота (токен, admin_id, allowed_users).
    
    Args:
        script_dir: директория проекта (если None, используется текущая)
    
    Returns:
        dict: конфигурация Telegram с ключами token, admin_id, allowed_users
    
    Raises:
        ValueError: если config_secret.json не содержит telegram_bot конфигурацию
    """
    secret_cfg = load_config_secret(script_dir)
    telegram_cfg = secret_cfg.get("telegram_bot", {})
    
    if not telegram_cfg:
        raise ValueError(
            "\n[!] Конфигурация Telegram бота не найдена в config_secret.json\n"
            "[!] Пожалуйста, заполните config_secret.json используя config_secret.json.example как шаблон"
        )
    
    required_keys = ["token", "admin_id"]
    for key in required_keys:
        if key not in telegram_cfg or not telegram_cfg[key]:
            raise ValueError(f"\n[!] Отсутствует обязательный параметр: telegram_bot.{key}")
    
    return telegram_cfg


def get_openai_config(script_dir=None):
    """
    Получает конфигурацию OpenAI API (api_key).
    
    Args:
        script_dir: директория проекта (если None, используется текущая)
    
    Returns:
        dict: конфигурация OpenAI с ключом api_key (может быть пустой если AI отключен)
    """
    secret_cfg = load_config_secret(script_dir)
    return secret_cfg.get("openai_api", {})


def get_template_config(template_name, script_dir=None):
    """
    Получает конфигурацию конкретного шаблона.
    
    Args:
        template_name: ��мя шаблона (например "template_16_9" или "template_1_1")
        script_dir: директория проекта (если None, используется текущая)
    
    Returns:
        dict: конфигурация шаблона
    
    Raises:
        KeyError: если шаблон не найден
    
    Example:
        >>> cfg = get_template_config("template_16_9")
        >>> print(cfg["base_width"])
        1920
    """
    defaults_cfg = load_config_defaults(script_dir)
    templates = defaults_cfg.get("templates", {})
    
    if template_name not in templates:
        available = list(templates.keys())
        raise KeyError(
            f"\n[!] Шаблон '{template_name}' не найден\n"
            f"[!] Доступные шаблоны: {available}"
        )
    
    return templates[template_name]


def get_ai_prompt_template(template_name, script_dir=None):
    """
    Получает AI промт-шаблон для конкретного шаблона расписания.
    
    Args:
        template_name: имя шаблона (например "template_16_9" или "template_1_1")
        script_dir: директория проекта (если None, используется текущая)
    
    Returns:
        str: AI промт-шаблон с плейсхолдером {text}
    
    Example:
        >>> prompt = get_ai_prompt_template("template_16_9")
        >>> filled = prompt.format(text="07 сентября | причастие")
    """
    template_cfg = get_template_config(template_name, script_dir)
    return template_cfg.get(
        "ai_prompt_template",
        "Проверь текст на опечатки:\n{text}"
    )


# === ОБРАТНАЯ СОВМЕСТИМОСТЬ ===
def load_config(script_dir=None):
    """
    Загружает публичную конфигурацию (обратная совместимость).
    Идентична load_config_defaults().
    
    Args:
        script_dir: директория проекта (если None, используется текущая)
    
    Returns:
        dict: конфигурация
    """
    return load_config_defaults(script_dir)


def save_config(cfg, script_dir=None):
    """
    Сохраняет публичную конфигурацию (обратная совместимость).
    Идентична save_config_defaults().
    
    Args:
        cfg: dict с конфигурацией
        script_dir: директория проекта (если None, используется текущая)
    """
    return save_config_defaults(cfg, script_dir)
