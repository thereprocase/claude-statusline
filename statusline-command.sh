#!/usr/bin/env bash
# Claude Code status line — theme dispatcher
# https://github.com/thereprocase/claude-statusline

CLAUDE_DIR="${HOME}/.claude"
THEME_FILE="${CLAUDE_DIR}/statusline-theme"
THEME=$(cat "$THEME_FILE" 2>/dev/null || echo "rainbow")

PYTHONIOENCODING=utf-8 exec python3 -c "
import sys, os, importlib
sl_dir = os.path.join(os.path.expanduser('~'), '.claude', 'statusline')
sys.path.insert(0, sl_dir)
from core import build_context
theme = importlib.import_module('${THEME}')
ctx = build_context()
print(theme.render(ctx), end='')
" <<< "$(cat)"
