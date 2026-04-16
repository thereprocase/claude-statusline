#!/usr/bin/env bash
# Quick theme switch. Usage: bash theme.sh [name]
# Without arguments, lists themes and shows current.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"
THEME_FILE="${CLAUDE_DIR}/statusline-theme"

CURRENT=""
[ -f "$THEME_FILE" ] && CURRENT=$(cat "$THEME_FILE" 2>/dev/null)

THEMES=()
for f in "${SCRIPT_DIR}/themes/"*.py; do
    name=$(basename "$f" .py)
    [[ "$name" == "core" || "$name" == "__init__" ]] && continue
    THEMES+=("$name")
done

if [ -z "$1" ]; then
    echo "Available themes:"
    for t in "${THEMES[@]}"; do
        if [ "$t" = "$CURRENT" ]; then
            echo "  * $t (current)"
        else
            echo "    $t"
        fi
    done
    echo ""
    echo "Usage: bash theme.sh <name>"
    exit 0
fi

if [[ ! "$1" =~ ^[a-z0-9_-]+$ ]]; then
    echo "Invalid theme name: '$1' (only lowercase letters, digits, hyphens, underscores allowed)"
    exit 1
fi

if [ ! -f "${SCRIPT_DIR}/themes/$1.py" ]; then
    echo "Unknown theme: $1 (available: ${THEMES[*]})"
    exit 1
fi

echo "$1" > "$THEME_FILE"
echo "Switched to: $1"
