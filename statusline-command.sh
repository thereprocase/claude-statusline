#!/usr/bin/env bash
# Claude Code status line — theme dispatcher
# https://github.com/thereprocase/claude-statusline

CLAUDE_DIR="${HOME}/.claude"
THEME_FILE="${CLAUDE_DIR}/statusline-theme"
THEME=$(cat "$THEME_FILE" 2>/dev/null || echo "rainbow")

# Find Python 3 — prefer python3, fall back to python if it's 3.x
PY3=""
if command -v python3 &>/dev/null; then
    PY3="python3"
elif command -v python &>/dev/null && python -c "import sys; sys.exit(0 if sys.version_info[0]>=3 else 1)" 2>/dev/null; then
    PY3="python"
else
    echo "statusline: python3 not found" >&2
    exit 0
fi

PYTHONIOENCODING=utf-8 exec "$PY3" -c "
import sys, os, importlib
sl_dir = os.path.join(os.path.expanduser('~'), '.claude', 'statusline')
sys.path.insert(0, sl_dir)
from core import build_context
theme = importlib.import_module('${THEME}')
ctx = build_context()
print(theme.render(ctx), end='')
" <<< "$(cat)"
