#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import re
import subprocess
import sys
from collections import NamedTuple

# Структура для хранения информации о найденном секрете
Finding = NamedTuple("Finding", [("path", str), ("line_num", type(None)), ("check_name", str), ("description", str)])

# Статические запрещенные файлы (динамические .env проверяются регулярным выражением)
FORBIDDEN_TRACKED_FILES = (
    "config_secret.json",
)

TEMPLATE_FILE = "config_secret.json.example"
ALLOWLIST_PRAGMA = "pragma: allowlist secret"

def repo_root():
    try:
        cmd = ["git", "rev-parse", "--show-toplevel"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def collect_staged():
    cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=d"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return [f.strip() for f in res.stdout.splitlines() if f.strip()]

def collect_tracked():
    cmd = ["git", "ls-files"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return [f.strip() for f in res.stdout.splitlines() if f.strip()]

def read_worktree(root, rel_path):
    p = os.path.join(root, rel_path)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "rb") as f:
            return f.read()
    except IOError:
        return None

def read_staged(rel_path):
    try:
        cmd = ["git", "show", f":{rel_path}"]
        res = subprocess.run(cmd, capture_output=True, check=True)
        return res.stdout
    except subprocess.CalledProcessError:
        return None

# --- НОВАЯ ФУНКЦИЯ ДЛЯ ЧТЕНИЯ СОДЕРЖИМОГО ИЗ ИСТОРИИ КОММИТОВ ---
def read_from_commit(commit_path):
    """Читает содержимое файла из конкретного коммита Git (формат commit_sha:path)."""
    try:
        cmd = ["git", "show", commit_path]
        result = subprocess.run(cmd, capture_output=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError:
        return None

# --- ИСПРАВЛЕННАЯ ФУНКЦИЯ ПРОВЕРКИ ЗАПРЕЩЕННЫХ ФАЙЛОВ ---
def check_forbidden_tracked(paths):
    """Приватные файлы вообще не должны попадать в git."""
    findings = []
    # Регулярное выражение ловит: .env, .env.local, .env.production, path/to/.env.test и т.д.
    ENV_FILE_PATTERN = re.compile(r'(^|/)\.env(\..+)?$')

    for path in paths:
        # Для истории пути имеют вид `sha:path`, отсекаем sha для проверки имени
        clean_path = path.split(":", 1)[1] if ":" in path and not os.path.exists(path) else path
        name = os.path.basename(clean_path)
        
        is_forbidden_env = bool(ENV_FILE_PATTERN.search(clean_path))
        is_forbidden_json = name in FORBIDDEN_TRACKED_FILES or bool(re.match(r"^config_secret.*\.json$", name))

        if is_forbidden_env or is_forbidden_json:
            findings.append(
                Finding(
                    path,
                    None,
                    "Private file tracked",
                    "приватный файл не должен попадать в git / "
                    "private file must never be committed "
                    "(git rm --cached "
                    f"{clean_path})",
                )
            )
    return findings

def looks_binary(path, data):
    if not data:
        return False
    return b"\x00" in data[:1024]

def scan_patterns(path, text):
    # Заглушка для демонстрации работоспособности структуры scan
    return []

def scan(paths, reader):
    findings = list(check_forbidden_tracked(paths))
    for path in paths:
        data = reader(path)
        if data is None or looks_binary(path, data):
            continue
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            continue
        # Дополнительные проверки содержимого (scan_patterns и т.д.) можно вызвать здесь
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
    # ИСПРАВЛЕНИЕ: Добавлен аргумент --range в группу параметров
    group.add_argument(
        "--range",
        metavar="COMMIT_RANGE",
        help="проверить историю изменений в диапазоне коммитов (для CI)",
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

    if args.staged:
        paths = collect_staged()
        reader = read_staged
        scope = "staged-файлы / staged files"
    elif args.range:
        paths = []
        try:
            rev_cmd = ["git", "rev-list", args.range]
            commits = subprocess.run(rev_cmd, capture_output=True, text=True, check=True).stdout.splitlines()
            for commit in commits:
                commit = commit.strip()
                if not commit:
                    continue
                diff_cmd = ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "--diff-filter=d", commit]
                mod_files = subprocess.run(diff_cmd, capture_output=True, text=True, check=True).stdout.splitlines()
                for f in mod_files:
                    f = f.strip()
                    if f:
                        paths.append(f"{commit}:{f}")
        except subprocess.CalledProcessError as e:
            print(f"[!] Ошибка при обработке диапазона {args.range}: {e.stderr}", file=sys.stderr)
            return 2
        reader = read_from_commit
        scope = f"история диапазона {args.range} / history of range"
    elif args.paths:
        paths = [os.path.relpath(os.path.abspath(p), root) for p in args.paths]
        reader = lambda p: read_worktree(root, p)
        scope = "указанные файлы / given files"
    else:
        paths = collect_tracked()
        reader = lambda p: read_worktree(root, p)
        scope = "отслеживаемые файлы / tracked files"

    if args.verbose:
        print(f"[i] Проверяется {len(paths)} шт. ({scope})")

    findings = scan(paths, reader)

    if not findings:
        print(f"[OK] Секретов не найдено ({scope}, {len(paths)} шт.) / no secrets found")
        return 0

    print("\n" + "=" * 72 + "\n[!] НАЙДЕНЫ ПОТЕНЦИАЛЬНЫЕ СЕКРЕТЫ / POTENTIAL SECRETS FOUND\n" + "=" * 72)
    for finding in findings:
        print(finding)
    return 1

if __name__ == "__main__":
    sys.exit(main())
