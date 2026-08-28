#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сканер секретов / Secret scanner.

Защищает репозиторий от случайного коммита реальных токенов и ключей —
в первую очередь через config_secret.json.example, который специально
разрешён в .gitignore (`!config_secret.json.example`) и поэтому попадает
в GitHub при любом изменении.

Что проверяется:
  1. Шаблон config_secret.json.example содержит ТОЛЬКО плейсхолдеры.
  2. Приватные файлы (config_secret.json, .env) не попали под контроль git.
  3. Ни один файл не содержит строк, похожих на реальные секреты
     (Telegram-токен, OpenAI/GitHub/AWS/Slack/Google ключи, приватные ключи).
  4. В любом *.json значения полей token/api_key/secret/password
     являются плейсхолдерами.

Использование:
    python3 scripts/check_secrets.py --staged     # только staged-файлы (pre-commit)
    python3 scripts/check_secrets.py --all        # все отслеживаемые файлы (CI)
    python3 scripts/check_secrets.py path1 path2  # конкретные файлы

Коды возврата:
    0 — секретов не найдено
    1 — найдены потенциальные секреты
    2 — ошибка запуска (например, не git-репозиторий)

Подавление ложного срабатывания: добавьте в ту же строку комментарий
`pragma: allowlist secret`.
"""

import argparse
import json
import os
import re
import subprocess
import sys

# --- Файлы, которые никогда не должны быть под контролем git -----------------
# Паттерн для поиска любых файлов .env, включая .env.production, .env.local и т.д.
ENV_FILE_PATTERN = re.compile(r'(^|/)\.env(\..+)?$')
FORBIDDEN_TRACKED_FILES = ("config_secret.json",)

# Файл-шаблон, ради которого и написан этот скрипт
TEMPLATE_FILE = "config_secret.json.example"

# --- Разрешённые плейсхолдеры ------------------------------------------------
# Значения, которые НЕ считаются секретами. Сравнение регистронезависимое.

PLACEHOLDER_VALUES = {
    "",
    "replace_with_telegram_bot_token",
    "replace_with_openai_api_key",
    "your_bot_token_here",
    "your_api_key_here",
    "sk-your-api-key-here",
    "changeme",
    "placeholder",
    "none",
    "null",
    "todo",
    "xxx",
}

# Подстроки-маркеры плейсхолдера: если значение их содержит — это не секрет
PLACEHOLDER_MARKERS = (
    "replace_with",
    "your_",
    "your-",
    "_here",
    "-here",
    "example",
    "placeholder",
    "dummy",
    "<",
    "xxxx",
)

# Комментарий для подавления проверки в конкретной строке
ALLOWLIST_PRAGMA = "pragma: allowlist secret"

# --- Сигнатуры реальных секретов --------------------------------------------

SECRET_PATTERNS = (
    (
        "Telegram bot token",
        re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{35}\b"),
    ),
    (
        "OpenAI API key",
        re.compile(r"\bsk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_-]{20,}\b"),
    ),
    (
        "GitHub token",
        re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}\b"),
    ),
    (
        "AWS access key ID",
        re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    ),
    (
        "Slack token",
        re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b"),
    ),
    (
        "Google API key",
        re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    ),
    (
        "Private key block",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
    ),
)

# Имена JSON-полей, значения которых обязаны быть плейсхолдерами
SENSITIVE_JSON_KEYS = re.compile(
    r"^(?:.*_)?(?:token|api_key|apikey|secret|password|passwd|access_key|private_key)$",
    re.IGNORECASE,
)

# Расширения, которые заведомо не содержат текст (шрифты, картинки и т.п.)
BINARY_SUFFIXES = (
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp",
    ".ttf", ".otf", ".woff", ".woff2",
    ".xlsx", ".xls", ".zip", ".gz", ".pdf",
    ".pyc", ".so", ".dll",
)


class Finding:
    """Одна находка сканера."""

    def __init__(self, path, line, kind, detail):
        self.path = path
        self.line = line
        self.kind = kind
        self.detail = detail

    def __str__(self):
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"  [{self.kind}] {where}\n      {self.detail}"


# --- Вспомогательные функции -------------------------------------------------

def redact(value):
    """Показывает секрет так, чтобы он не попал в логи CI целиком."""
    text = str(value)
    if len(text) <= 6:
        return "*" * len(text)
    return f"{text[:4]}…{'*' * 6} (длина/length: {len(text)})"


def is_placeholder(value):
    """True, если значение — очевидный плейсхолдер, а не реальный секрет."""
    if value is None:
        return True
    if isinstance(value, (int, float, bool)):
        # Числовые ID: 0 и общеизвестный пример 123456789 считаем шаблонными
        return value in (0, 123456789, 987654321, False, True)
    if not isinstance(value, str):
        return True

    normalized = value.strip().lower()
    if normalized in PLACEHOLDER_VALUES:
        return True
    if len(normalized) < 8:
        # Слишком коротко, чтобы быть настоящим токеном
        return True
    return any(marker in normalized for marker in PLACEHOLDER_MARKERS)


def git(*args):
    """Запускает git и возвращает stdout (или None при ошибке)."""
    try:
        result = subprocess.run(
            ("git",) + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout.decode("utf-8", errors="replace")


def repo_root():
    root = git("rev-parse", "--show-toplevel")
    return root.strip() if root else None


def looks_binary(path, data):
    if path.lower().endswith(BINARY_SUFFIXES):
        return True
    return b"\0" in data[:8000]


# --- Сбор файлов и их содержимого -------------------------------------------
def collect_range(commit_range):
    """Получает список файлов, измененных в заданном диапазоне коммитов."""
    cmd = ["git", "diff", "--name-only", "--diff-filter=d", commit_range]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]

def collect_staged():
    """Файлы в индексе (то, что реально уйдёт в коммит)."""
    out = git("diff", "--cached", "--name-only", "--diff-filter=ACM", "-z")
    if out is None:
        return []
    return [p for p in out.split("\0") if p]


def collect_tracked():
    """Все отслеживаемые файлы репозитория."""
    out = git("ls-files", "-z")
    if out is None:
        return []
    return [p for p in out.split("\0") if p]


def read_staged(path):
    """Содержимое файла из индекса, а не с диска."""
    try:
        result = subprocess.run(
            ("git", "show", f":{path}"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout


def read_worktree(root, path):
    full = os.path.join(root, path)
    try:
        with open(full, "rb") as handle:
            return handle.read()
    except OSError:
        return None


# --- Проверки ----------------------------------------------------------------

def scan_patterns(path, text):
    """Ищет сигнатуры известных форматов секретов построчно."""
    findings = []
    for number, line in enumerate(text.splitlines(), start=1):
        if ALLOWLIST_PRAGMA in line:
            continue
        for kind, pattern in SECRET_PATTERNS:
            match = pattern.search(line)
            if match:
                findings.append(
                    Finding(
                        path,
                        number,
                        kind,
                        f"похоже на реальный секрет / looks like a real secret: "
                        f"{redact(match.group(0))}",
                    )
                )
    return findings


def walk_json(node, path_parts=()):
    """Рекурсивно обходит JSON, отдавая пары (путь_к_ключу, значение)."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk_json(value, path_parts + (str(key),))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk_json(value, path_parts + (f"[{index}]",))
    else:
        yield ".".join(path_parts), node


def scan_json_fields(path, text):
    """Проверяет, что чувствительные поля любого *.json содержат плейсхолдеры."""
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        # Невалидный JSON — отдельная проверка ниже, здесь просто пропускаем
        return []

    findings = []
    for key_path, value in walk_json(data):
        leaf = key_path.split(".")[-1]
        if not SENSITIVE_JSON_KEYS.match(leaf):
            continue
        if is_placeholder(value):
            continue
        findings.append(
            Finding(
                path,
                None,
                "JSON secret field",
                f'поле "{key_path}" содержит непохожее на плейсхолдер значение / '
                f"field holds a non-placeholder value: {redact(value)}",
            )
        )
    return findings


def check_template(path, text):
    """
    Строгая валидация config_secret.json.example.

    Шаблон трекается git-ом принудительно (`!config_secret.json.example`),
    поэтому к нему требования жёстче, чем к остальным файлам.
    """
    findings = []

    try:
        data = json.loads(text)
    except ValueError as error:
        findings.append(
            Finding(path, None, "Template invalid", f"невалидный JSON / invalid JSON: {error}")
        )
        return findings

    if not isinstance(data, dict):
        findings.append(
            Finding(path, None, "Template invalid", "ожидается JSON-объект / expected a JSON object")
        )
        return findings

    if "_WARNING" not in data:
        findings.append(
            Finding(
                path,
                None,
                "Template warning missing",
                'отсутствует ключ "_WARNING" с предупреждением о секретах / '
                'missing the "_WARNING" header key',
            )
        )

    telegram = data.get("telegram_bot", {})
    if isinstance(telegram, dict):
        for field in ("token", "admin_id"):
            if field not in telegram:
                findings.append(
                    Finding(
                        path,
                        None,
                        "Template incomplete",
                        f"нет поля telegram_bot.{field} / missing telegram_bot.{field}",
                    )
                )
        allowed = telegram.get("allowed_users", [])
        if isinstance(allowed, list):
            real_ids = [uid for uid in allowed if not is_placeholder(uid)]
            if real_ids:
                findings.append(
                    Finding(
                        path,
                        None,
                        "Template real data",
                        "telegram_bot.allowed_users содержит похожие на реальные ID / "
                        f"holds real-looking IDs: {len(real_ids)} шт.",
                    )
                )

    # Все чувствительные поля шаблона обязаны быть плейсхолдерами
    findings.extend(scan_json_fields(path, text))
    return findings

def check_forbidden_tracked(paths):
    """Приватные файлы вообще не должны попадать в git."""
    findings = []
    
    # Регулярное выражение ловит: .env, .env.local, .env.production, sub/dir/.env.test и т.д.
    ENV_FILE_PATTERN = re.compile(r'(^|/)\.env(\..+)?$')

    for path in paths:
        name = os.path.basename(path)
        
        # Проверяем, совпадает ли файл с шаблоном .env.* или старыми правилами
        is_forbidden_env = bool(ENV_FILE_PATTERN.search(path))
        is_forbidden_json = name == "config_secret.json" or bool(re.match(r"^config_secret.*\.json$", name))

        if is_forbidden_env or is_forbidden_json:
            findings.append(
                Finding(
                    path,
                    None,
                    "Private file tracked",
                    "приватный файл не должен попадать в git / "
                    "private file must never be committed "
                    "(git rm --cached "
                    f"{path})",
                )
            )
    return findings

# --- Точка входа -------------------------------------------------------------

def scan(paths, reader):
    findings = list(check_forbidden_tracked(paths))

    for path in paths:
        data = reader(path)
        if data is None:
            continue
        if looks_binary(path, data):
            continue

        text = data.decode("utf-8", errors="replace")
        name = os.path.basename(path)

        if name == TEMPLATE_FILE:
            findings.extend(check_template(path, text))
        elif path.lower().endswith(".json"):
            findings.extend(scan_json_fields(path, text))

        findings.extend(scan_patterns(path, text))

    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Проверка репозитория на утечку секретов / repository secret scan",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--staged",
        action="store_true",
        help="проверить только staged-файлы (для pre-commit хука)",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="проверить все отслеживаемые файлы (для CI)",
    )
    parser.add_argument("paths", nargs="*", help="конкретные файлы для проверки")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="показать список проверенных файлов"
    )
    args = parser.parse_args(argv)

    root = repo_root()
    if root is None:
        print("[!] Не git-репозиторий или git недоступен / not a git repository", file=sys.stderr)
        return 2

        # 1. Добавляем новое условие в цепочку (выделил жирным)
    if args.staged:
        paths = collect_staged()
        reader = read_staged
        scope = "staged-файлы / staged files"
    elif args.range:
        paths = collect_range(args.range)
        reader = lambda p: read_worktree(root, p)
        scope = f"файлы из диапазона {args.range} / files in range"
    elif args.paths:
        paths = [os.path.relpath(os.path.abspath(p), root) for p in args.paths]
        reader = lambda p: read_worktree(root, p)  # noqa: E731
        scope = "указанные файлы / given files"
    else:
        paths = collect_tracked()
        reader = lambda p: read_worktree(root, p)  # noqa: E731
        scope = "отслеживаемые файлы / tracked files"


    if args.verbose:
        print(f"[i] Проверяется {len(paths)} шт. ({scope})")
        for path in paths:
            print(f"    - {path}")

    findings = scan(paths, reader)

    if not findings:
        print(f"[OK] Секретов не найдено ({scope}, {len(paths)} шт.) / no secrets found")
        return 0

    print("")
    print("=" * 72)
    print("[!] НАЙДЕНЫ ПОТЕНЦИАЛЬНЫЕ СЕКРЕТЫ / POTENTIAL SECRETS FOUND")
    print("=" * 72)
    for finding in findings:
        print(finding)
    print("")
    print("Что делать / What to do:")
    print("  1. Уберите реальные значения — редактируйте config_secret.json,")
    print("     а НЕ config_secret.json.example.")
    print("     Edit config_secret.json, never the .example template.")
    print("  2. Если файл уже в индексе:  git restore --staged <файл>")
    print("  3. Если это ложное срабатывание — добавьте в строку комментарий:")
    print(f"     {ALLOWLIST_PRAGMA}")
    print("  4. Если реальный токен всё же был запушен — ОТЗОВИТЕ его")
    print("     (@BotFather /revoke, OpenAI dashboard) — удаления коммита мало.")
    print("")
    return 1


if __name__ == "__main__":
    sys.exit(main())
