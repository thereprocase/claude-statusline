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
    # Atomic write via tempfile; path passed via env to avoid shell interpolation
    SETTINGS_PATH="${SETTINGS}" python3 -c '
import json, os, tempfile
path = os.environ["SETTINGS_PATH"]
with open(path) as f:
    s = json.load(f)
s.pop("statusLine", None)
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
try:
    with os.fdopen(fd, "w") as t:
        json.dump(s, t, indent=2)
    os.replace(tmp, path)
except Exception:
    os.unlink(tmp)
    raise
print("Removed statusLine from", path)
' 2>/dev/null || echo "Could not update ${SETTINGS} — remove statusLine key manually."
fi

echo "Restart Claude Code to deactivate."
