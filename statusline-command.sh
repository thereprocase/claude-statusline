#!/usr/bin/env bash
# Claude Code status line — theme dispatcher
# https://github.com/thereprocase/claude-statusline

CLAUDE_DIR="${HOME}/.claude"
THEME_FILE="${CLAUDE_DIR}/statusline-theme"

# Read theme; strip \r in case file has CRLF line endings
THEME=$(cat "$THEME_FILE" 2>/dev/null) || THEME="buddy"
THEME="${THEME%$'\r'}"
THEME="${THEME:-buddy}"

# Resolve python: prefer python3, then python, then Windows `py` launcher.
# Final fallback scans common Windows install locations — Git Bash often has
# python.exe absent from PATH even when the system has it.
PYTHON=
for cand in python3 python py; do
    if command -v "$cand" >/dev/null 2>&1; then
        PYTHON=$cand
        break
    fi
done
if [ -z "$PYTHON" ]; then
    for p in \
        "${HOME}/AppData/Local/Programs/Python/Launcher/py.exe" \
        "${HOME}/AppData/Local/Programs/Python/Python313/python.exe" \
        "${HOME}/AppData/Local/Programs/Python/Python312/python.exe" \
        "${HOME}/AppData/Local/Programs/Python/Python311/python.exe" \
        "/c/Windows/py.exe"; do
        if [ -x "$p" ]; then
            PYTHON=$p
            break
        fi
    done
fi
if [ -z "$PYTHON" ]; then
    echo "⚠ statusline: no python interpreter found"
    exit 1
fi

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
