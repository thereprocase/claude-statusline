#!/usr/bin/env bash
# Install or update the Claude Code status line.
# First install: prompts for theme, then offers full setup.
# Update: keeps current theme/config, copies latest files.
# CLI arg: ./install.sh <theme> to set theme without prompts.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"
SL_DIR="${CLAUDE_DIR}/statusline"
THEME_FILE="${CLAUDE_DIR}/statusline-theme"
SETTINGS="${CLAUDE_DIR}/settings.json"

# Discover themes
THEMES=()
for f in "${SCRIPT_DIR}/themes/"*.py; do
    name=$(basename "$f" .py)
    [[ "$name" == "core" || "$name" == "__init__" ]] && continue
    THEMES+=("$name")
done

# Determine mode: fresh install or update
CURRENT=""
[ -f "$THEME_FILE" ] && CURRENT=$(cat "$THEME_FILE" 2>/dev/null)
IS_UPDATE=false
[ -n "$CURRENT" ] && IS_UPDATE=true

# Theme selection
if [ -n "$1" ]; then
    THEME="$1"
elif $IS_UPDATE; then
    THEME="$CURRENT"
    echo "Keeping current theme: $THEME"
else
    echo "Available themes: ${THEMES[*]}"
    read -rp "Choose theme [buddy]: " THEME
    THEME="${THEME:-buddy}"
fi

# Validate
if [ ! -f "${SCRIPT_DIR}/themes/${THEME}.py" ]; then
    echo "Unknown theme: $THEME (available: ${THEMES[*]})"
    exit 1
fi

# Copy theme files
mkdir -p "$SL_DIR"
for f in "${SCRIPT_DIR}/themes/"*.py; do
    cp "$f" "$SL_DIR/"
done

# Copy dispatcher
cp "${SCRIPT_DIR}/statusline-command.sh" "${CLAUDE_DIR}/statusline-command.sh"
chmod +x "${CLAUDE_DIR}/statusline-command.sh"

# Save theme choice
echo "$THEME" > "$THEME_FILE"
echo "Theme: $THEME"

# Update settings.json — use Python's expanduser to resolve path on all platforms
if [ -f "${SETTINGS}" ]; then
    if python3 -c "
import json, os
p = os.path.join(os.path.expanduser('~'), '.claude', 'settings.json')
with open(p, encoding='utf-8') as f: s = json.load(f)
s['statusLine'] = {'type': 'command', 'command': 'bash ~/.claude/statusline-command.sh'}
with open(p, 'w', encoding='utf-8') as f: json.dump(s, f, indent=2)
print(f'Updated {p}')
" 2>/dev/null; then
        :
    else
        echo "Could not update ${SETTINGS} — add manually:"
        echo '  "statusLine": { "type": "command", "command": "bash ~/.claude/statusline-command.sh" }'
    fi
else
    echo '{ "statusLine": { "type": "command", "command": "bash ~/.claude/statusline-command.sh" } }' > "${SETTINGS}"
    echo "Created ${SETTINGS}"
fi

echo ""
echo "Installed to ${CLAUDE_DIR}/statusline/"

# Post-install guidance
if $IS_UPDATE; then
    echo "Run 'bash setup.sh' to reconfigure theme and settings."
else
    echo ""
    read -rp "Run interactive setup to configure all options? (Y/n): " DO_SETUP
    if [[ ! "$DO_SETUP" =~ [nN] ]]; then
        bash "${SCRIPT_DIR}/setup.sh"
    else
        echo ""
        echo "You can run 'bash setup.sh' anytime to configure."
        echo "Or switch themes: bash theme.sh <name>"
    fi
fi

echo ""
echo "Restart Claude Code to activate."
