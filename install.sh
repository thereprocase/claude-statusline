#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"
DEST="${CLAUDE_DIR}/statusline-command.sh"
SETTINGS="${CLAUDE_DIR}/settings.json"

# Copy script
cp "${SCRIPT_DIR}/statusline-command.sh" "${DEST}"
chmod +x "${DEST}"
echo "Installed statusline-command.sh to ${DEST}"

# Update settings.json
if [ -f "${SETTINGS}" ]; then
    if python3 -c "
import json, sys
with open('${SETTINGS}') as f: s = json.load(f)
s['statusLine'] = {'type': 'command', 'command': 'bash ~/.claude/statusline-command.sh'}
with open('${SETTINGS}', 'w') as f: json.dump(s, f, indent=2)
print('Updated ${SETTINGS}')
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
echo "Restart Claude Code to activate the status line."
