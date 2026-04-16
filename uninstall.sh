#!/usr/bin/env bash
set -e

CLAUDE_DIR="${HOME}/.claude"
SETTINGS="${CLAUDE_DIR}/settings.json"

rm -f "${CLAUDE_DIR}/statusline-command.sh"
rm -f "${CLAUDE_DIR}/statusline-state.json"
rm -f "${CLAUDE_DIR}/rate-limit-log.jsonl"
rm -f "${CLAUDE_DIR}/statusline-theme"
rm -f "${CLAUDE_DIR}/statusline-config.json"
rm -rf "${CLAUDE_DIR}/statusline"
echo "Removed statusline files."

if [ -f "${SETTINGS}" ]; then
    python3 -c "
import json
with open('${SETTINGS}') as f: s = json.load(f)
s.pop('statusLine', None)
with open('${SETTINGS}', 'w') as f: json.dump(s, f, indent=2)
print('Removed statusLine from ${SETTINGS}')
" 2>/dev/null || echo "Could not update ${SETTINGS} — remove statusLine key manually."
fi

echo "Restart Claude Code to deactivate."
