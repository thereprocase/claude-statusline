#!/usr/bin/env bash
set -e

CLAUDE_DIR="${HOME}/.claude"
DEST="${CLAUDE_DIR}/statusline-command.sh"
STATE="${CLAUDE_DIR}/statusline-state.json"
LOG="${CLAUDE_DIR}/rate-limit-log.jsonl"
SETTINGS="${CLAUDE_DIR}/settings.json"

rm -f "${DEST}" "${STATE}" "${LOG}"
echo "Removed statusline files."

if [ -f "${SETTINGS}" ]; then
    python -c "
import json
with open('${SETTINGS}') as f: s = json.load(f)
s.pop('statusLine', None)
with open('${SETTINGS}', 'w') as f: json.dump(s, f, indent=2)
print('Removed statusLine from ${SETTINGS}')
" 2>/dev/null || echo "Could not update ${SETTINGS} — remove statusLine key manually."
fi

echo "Restart Claude Code to deactivate."
