# Claude Code Rainbow Status Line

A colorful, information-dense status line for [Claude Code](https://claude.ai/code).

```
Op4.6 1M │ ██████──────────────── 14.0% │ 3% 9pm │ 11% wed 12pm │ $34.40 │ +3646/-448 │ ↑0/↑0
```

## What it shows

| Section | Description |
|---------|-------------|
| `Op4.6 1M` | Model abbreviation + context window size |
| `██████────` | Context window usage as a rainbow heat gradient (cyan → red) |
| `14.0%` | Context window usage percentage |
| `3% 9pm` | 5-hour rate limit % + next reset time |
| `11% wed 12pm` | 7-day rate limit % + next reset time |
| `$34.40` | Session cost (equivalent API pricing, not actual charge on Pro/Max) |
| `+3646/-448` | Lines added/removed this session |
| `↑0/↑0` | Monthly rate limit exceedance count (5h / 7d) |

### Rate limit exceedance tracking

The `↑` counters track how many times per calendar month your rate limits have crossed upward through 30%, 55%, or 75%. Each threshold is independently armed — it counts once per crossing, then waits for the rate to drop back below before counting again.

The color shifts from cool cyan toward red as you approach monthly limits (~30 daily spikes / ~4 weekly spikes).

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

Works on Windows, macOS, and Linux.

## Install

```bash
git clone https://github.com/YOUR_USERNAME/claude-statusline.git
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

## License

MIT
