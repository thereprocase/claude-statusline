# Claude Code Rainbow Status Line

A colorful, information-dense status line for [Claude Code](https://claude.ai/code).

```
So4.6 200k │ ██████──── 18.0% │ ↑1 ↓29 │ 3%5p │ 99%mo9a │ $0.61 │ 0x/0x
```

## What it shows

| Section | Description |
|---------|-------------|
| `So4.6 200k` | Model abbreviation + context window size |
| `██████────` | Context window usage as a rainbow heat gradient (cyan → red) |
| `18.0%` | Context window usage percentage |
| `↑1 ↓29` | Input and output tokens for the last turn |
| `3%5p` | 5-hour rate limit % + reset time (today) |
| `99%mo9a` | 7-day rate limit % + reset time (day prefix when not today) |
| `$0.61` | Session cost (equivalent API pricing, not actual charge on Pro/Max) |
| `0x/0x` | Monthly rate limit exceedance count (5h / 7d), per active model |

### Rate limit exceedance tracking

The `x` counters track how many times per calendar month your rate limits have crossed upward through 30%, 55%, 75%, or 99%. Each threshold is independently armed — it counts once per crossing, then waits for the rate to drop back below before counting again.

Counts are tracked **per model family** (Opus, Sonnet, Haiku) so switching models doesn't pollute your history.

The color shifts from cool cyan toward red as you approach monthly limits (~30 daily spikes / ~4 weekly spikes).

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

**Rate limits are all-model aggregates.** The Claude Code statusline hook payload exposes `five_hour` and `seven_day` rate limit percentages, but these are combined across all models. There is no per-model rate limit in the payload. The exceedance counters (`0x/0x`) are tracked per model family from the local log, but the live `%` figures always reflect total usage. The `/usage` dialog in Claude Code shows a per-model breakdown; that data is not available to external hooks.

**Unicode block characters.** The bar uses Unicode block elements (U+2588, U+258x series) and separator (U+2502). These render correctly in most modern terminals. If you see garbled characters, your terminal font doesn't cover the Latin Extended block — switch to a font like JetBrains Mono, Cascadia Code, or any Nerd Font.

## License

MIT
