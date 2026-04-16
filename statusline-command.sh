#!/usr/bin/env bash
# Claude Code status line — theme dispatcher
# https://github.com/thereprocase/claude-statusline

CLAUDE_DIR="${HOME}/.claude"
THEME_FILE="${CLAUDE_DIR}/statusline-theme"
# Use bash builtin to avoid a cat fork; fall back to buddy (not rainbow)
THEME=$(<"$THEME_FILE" 2>/dev/null) || THEME="buddy"
THEME="${THEME:-buddy}"

# Pass all values via environment so no shell interpolation enters Python source.
# exec replaces this process; Python inherits stdin directly from the caller.
STATUSLINE_THEME="$THEME" CLAUDE_DIR_PATH="$CLAUDE_DIR" PYTHONIOENCODING=utf-8 \
    exec python3 -c '
import os, sys, importlib
theme_name = os.environ["STATUSLINE_THEME"]
claude_dir = os.environ["CLAUDE_DIR_PATH"]
sys.path.insert(0, os.path.join(claude_dir, "statusline"))
from core import build_context
mod = importlib.import_module(theme_name)
ctx = build_context()
print(mod.render(ctx), end="")
' || echo '⚠ statusline error'
