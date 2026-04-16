#!/usr/bin/env bash
# Claude Code status line — theme dispatcher
# https://github.com/thereprocase/claude-statusline

CLAUDE_DIR="${HOME}/.claude"
THEME_FILE="${CLAUDE_DIR}/statusline-theme"

# Read theme; strip \r in case file has CRLF line endings
THEME=$(cat "$THEME_FILE" 2>/dev/null) || THEME="buddy"
THEME="${THEME%$'\r'}"
THEME="${THEME:-buddy}"

# Resolve python: prefer python3, fall back to python
PYTHON=python3
command -v python3 >/dev/null 2>&1 || PYTHON=python

# Pass all values via environment so no shell interpolation enters Python source.
# exec replaces this process; Python inherits stdin directly from the caller.
STATUSLINE_THEME="$THEME" CLAUDE_DIR_PATH="$CLAUDE_DIR" PYTHONIOENCODING=utf-8 \
    exec "$PYTHON" -c '
import os, sys, importlib
theme_name = os.environ["STATUSLINE_THEME"]
claude_dir = os.environ["CLAUDE_DIR_PATH"]
sys.path.insert(0, os.path.join(claude_dir, "statusline"))
from core import build_context
mod = importlib.import_module(theme_name)
ctx = build_context()
print(mod.render(ctx), end="")
' || echo '⚠ statusline error'
