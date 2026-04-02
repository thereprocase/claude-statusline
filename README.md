# Claude Code Rainbow Status Line

A colorful, information-dense status line for [Claude Code](https://claude.ai/code).

```
So4.6 200k │ ███▓────── 38.0% │ 9%5p │ 100%su9a
```

## What it shows

| Section | Description |
|---------|-------------|
| `So4.6 200k` | Model abbreviation + context window size |
| `███▓──────` | Context window usage bar — shaded fill (░▒▓█) at 25/50/75/100% per bin, cyan → red gradient |
| `38.0%` | Context window usage percentage |
| `9%5p` | 5-hour rate limit % + reset time (today) |
| `100%su9a` | 7-day rate limit % + reset time (day prefix when not today) |

### Reset time format

| Format | Meaning |
|--------|---------|
| `5p` | Resets at 5 PM today |
| `mo9a` | Resets Monday at 9 AM |

### Model abbreviations

| Model | Abbreviation |
|-------|-------------|
| Claude Opus 4.6 | `Op4.6` |
| Claude Opus 4.5 | `Op4.5` |
| Claude Sonnet 4.6 | `So4.6` |
| Claude Sonnet 4.5 | `So4.5` |
| Claude Sonnet 4.0 | `So4` |
| Claude Haiku 4.5 | `Ha4.5` |
| Claude Haiku 3.5 | `Ha3.5` |

## Requirements

- Claude Code v2.1+
- Python 3.6+ on PATH
- Bash

Works on Windows (Git Bash or WSL), macOS, and Linux.

## Install

```bash
git clone https://github.com/thereprocase/claude-statusline.git
cd claude-statusline
bash install.sh
```

Then restart Claude Code.

## Uninstall

```bash
cd claude-statusline
bash uninstall.sh
```

## Manual install

1. Copy `statusline-command.sh` to `~/.claude/statusline-command.sh`
2. `chmod +x ~/.claude/statusline-command.sh`
3. Add to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "bash ~/.claude/statusline-command.sh"
  }
}
```

4. Restart Claude Code.

## Files created

| File | Purpose |
|------|---------|
| `~/.claude/statusline-command.sh` | The status line script |
| `~/.claude/statusline-state.json` | Tracks rate limit state between invocations |
| `~/.claude/rate-limit-log.jsonl` | Persistent log of rate limit threshold crossings |

## Known limitations

**Bash required.** The script uses `<<< here-string` syntax, which is a bashism. It will fail under `/bin/sh` on strict systems. The shebang is `#!/usr/bin/env bash` — as long as bash is on PATH, it works. On Windows, run it via Git Bash or WSL; the Claude Code `settings.json` command should be `bash ~/.claude/statusline-command.sh`, not `sh`.

**Rate limits are all-model aggregates.** The Claude Code statusline hook payload exposes `five_hour` and `seven_day` rate limit percentages combined across all models. There is no per-model breakdown available to external hooks. The `/usage` dialog in Claude Code shows per-model data; that is not accessible here.

**Unicode block characters.** The bar uses Unicode block elements (U+2588, U+258x series) and separator (U+2502). These render correctly in most modern terminals. If you see garbled characters, your terminal font doesn't cover the Block Elements or Box Drawing Unicode blocks — switch to a font like JetBrains Mono, Cascadia Code, or any Nerd Font.

## License

MIT
