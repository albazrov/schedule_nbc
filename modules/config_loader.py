import json
import os
import tempfile
from pathlib import Path


def get_script_dir():
    """Возвращает директорию проекта"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Значения-плейсхолдеры из config_secret.json.example. Если они дошли до
# рантайма — значит шаблон скопировали, но не заполнили (или, что хуже,
# правят сам .example вместо config_secret.json).
_PLACEHOLDER_MARKERS = ("replace_with", "your_", "your-", "_here", "-here", "placeholder")


def is_placeholder_value(value):
    """
    Проверяет, что значение осталось шаблонным и не является реальным секретом.

    Args:
        value: проверяемое значение (str/int/None)

    Returns:
        bool: True если это плейсхолдер из config_secret.json.example
    """
    if value is None:
        return True
    if isinstance(value, str):
        normalized = value.strip().lower()
        if not normalized:
            return True
        return any(marker in normalized for marker in _PLACEHOLDER_MARKERS)
    if isinstance(value, int) and not isinstance(value, bool):
        return value in (0, 123456789, 987654321)
    return False


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

    Файл создаётся атомарно с правами 0600 (только владелец может
    читать/писать) — режим доступа устанавливается уже в момент
    создания дескриптора, до записи каких-либо данных, чтобы не
    оставлять окно, в котором секреты доступны для чтения другим
    пользователям системы. Если файл уже существовал (в т.ч. с более
    широкими правами или как symlink), он безопасно заменяется через
    временный файл и atomic rename, так что права 0600 сохраняются и
    при перезаписи.

    Args:
        config: dict с конфигурацией
        script_dir: директория проекта (если None, используется текущая)
    
    Raises:
        IOError: если не удалось записать файл
    """
    if script_dir is None:
        script_dir = get_script_dir()
    
    config_path = os.path.join(script_dir, "config_secret.json")
    tmp_path = None
    try:
        # Уникальное имя временного файла для каждой попытки (в той же
        # директории, чтобы os.replace ниже был атомарным): если
        # процесс упадёт до os.replace, файл с фиксированным именем
        # ".tmp" не остаётся зависшим и не блокирует последующие
        # сохранения через O_EXCL. tempfile.mkstemp создаёт файл с
        # правами 0600 (POSIX) уже в момент открытия дескриптора — до
        # записи каких-либо данных, так что окна с более широкими
        # правами не возникает.
        fd, tmp_path = tempfile.mkstemp(
            dir=script_dir, prefix=".config_secret.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())

            # Явно фиксируем режим ещё раз перед заменой на случай, если
            # umask или ФС повлияли на итоговые биты (защитный дубль).
            os.chmod(tmp_path, 0o600)
            # Atomic rename: заменяет целевой файл целиком (включая его
            # старые права), новый файл на диске появляется уже с 0600 —
            # окна с более широкими правами не возникает.
            os.replace(tmp_path, config_path)
            tmp_path = None  # успешно перемещён — больше не наш файл
        finally:
            # Любой не-успешный путь (исключение при записи/chmod/replace)
            # должен убрать временный файл, чтобы не оставлять секреты
            # на диске и не засорять директорию.
            if tmp_path is not None and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        print(f"✅ Приватная конфигурация сохранена: {config_path}")
    except IOError as e:
        raise IOError(f"Ошибка при сохранении {config_path}: {e}")
    except OSError as e:
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
    


    return telegram_cfg


def get_openai_config(script_dir=None):
    """
    Получает конфигурацию OpenAI API (api_key).
    
    Args:
        script_dir: директория проекта (если None, используется текущая)
    
    Returns:
        dict: конфигурация OpenAI с ключом api_key (может быть пустой если AI отключен
              или если ключ остался плейсхолдером из шаблона)
    """
    secret_cfg = load_config_secret(script_dir)
    openai_cfg = dict(secret_cfg.get("openai_api", {}))

    if "api_key" in openai_cfg and is_placeholder_value(openai_cfg["api_key"]):
        print(
            "⚠️  [NOTICE] openai_api.api_key в config_secret.json — плейсхолдер, AI отключён.\n"
            "⚠️  [NOTICE] Впишите реальный ключ в config_secret.json (НЕ в .example)."
        )
        openai_cfg.pop("api_key")

    return openai_cfg


def get_template_config(template_name, script_dir=None):
    """
    Получает конфигурацию конкретного шаблона.
    
    Args:
        template_name: имя шаблона (например "template_16_9" или "template_1_1")
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
