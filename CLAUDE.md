# Claude Code Statusline

A themeable status line for Claude Code with rate limit tracking, context corruption effects, and session timers.

## For Claude Code Sessions

When a user asks to **install**, **update**, or **pull** this statusline:

### Fresh install
1. Run `bash install.sh <theme>` with the user's chosen theme
2. If they don't pick a theme, show them the available options first (see "Showing themes" below)

### Update (pulling latest from git)
1. `git pull` or `gh repo clone thereprocase/claude-statusline /tmp/claude-statusline`
2. **Before running install.sh**, check if new themes were added since the user's last install:
   - Compare `ls /tmp/claude-statusline/themes/*.py` against `ls ~/.claude/statusline/*.py`
   - If there are new themes, **show the user all available themes** and ask if they want to switch
3. Run `bash install.sh` (with current theme to keep, or new theme if they chose one)
4. Test the result: `echo '<mock-json>' | bash ~/.claude/statusline-command.sh`

### Showing themes
Generate a live preview by piping mock data through each theme:
```bash
MOCK='{"model":{"display_name":"Claude","id":"claude-opus-4-6"},"context_window":{"used_percentage":42,"context_window_size":1000000},"rate_limits":{"five_hour":{"used_percentage":31},"seven_day":{"used_percentage":67}},"cwd":"/home/user/project","session_id":"demo"}'
for theme in /tmp/claude-statusline/themes/*.py; do
  name=$(basename "$theme" .py)
  [[ "$name" == "core" ]] && continue
  output=$(echo "$MOCK" | PYTHONIOENCODING=utf-8 python3 -c "
import sys, importlib; sys.path.insert(0, 'themes')
from core import build_context
theme = importlib.import_module('$name')
print(theme.render(build_context()), end='')
" 2>&1)
  printf "\n%-12s %s\n" "$name" "$output"
done
```

### Switching themes
```bash
bash theme.sh <name>     # or edit ~/.claude/statusline-theme
```

### Windows / Git Bash compatibility
The dispatcher uses `os.path.expanduser('~')` for the Python sys.path, NOT bash `$HOME`. Bash `$HOME` on Git Bash is `/c/Users/...` which Python can't resolve as a module path. This is a known fix — don't revert it.

## File structure

```
~/.claude/
  statusline-command.sh    # Dispatcher — reads theme, calls Python
  statusline-theme         # Single line: theme name (e.g., "win95")
  statusline-state.json    # Rate limit tracking state (auto-managed)
  rate-limit-log.jsonl     # Threshold crossing history (auto-managed)
  statusline/              # Theme modules (installed by install.sh)
    core.py                # Shared context builder
    buddy.py, win95.py...  # Theme renderers
```

## PII notes
- The statusline reads the user's email from `~/.claude/.claude.json` to show colored initials (first 3 chars of local part). This data never leaves the local machine.
- No real names, emails, or identifying information should appear in this repo's source code.
- Theme previews in documentation use generic placeholders, not real user data.
