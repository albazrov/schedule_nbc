#!/usr/bin/env bash
#
# Устанавливает git-хуки проекта из каталога .githooks.
# Installs the project's git hooks from the .githooks directory.
#
# Запуск один раз после клонирования / run once after cloning:
#     ./scripts/install-hooks.sh
#
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

chmod +x .githooks/* 2>/dev/null || true
chmod +x scripts/*.sh scripts/*.py 2>/dev/null || true

git config core.hooksPath .githooks

echo "✅ Git-хуки установлены (core.hooksPath = .githooks)"
echo "✅ Git hooks installed."
echo ""
echo "Активные хуки / active hooks:"
for hook in .githooks/*; do
    [ -f "$hook" ] && echo "   - $(basename "$hook")"
done
echo ""
echo "Проверить весь репозиторий вручную / scan the whole repo manually:"
echo "   python3 scripts/check_secrets.py --all"
