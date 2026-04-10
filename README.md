# Claude Code Rainbow Status Line

A colorful, information-dense status line for [Claude Code](https://claude.ai/code).

![Clean statusline at 30% context](images/statusline-clean.svg)

## What it shows

| Section | Description |
|---------|-------------|
| `use` | First 3 chars of the active Claude account email — each char gets a unique color from a 60-char golden-angle palette (a–z, 0–9, dot-atom specials) |
| `Op4.6 1M` | Model abbreviation + context window size — bold tier color (Opus-1M gold, Opus-200k orange, Sonnet-1M cyan, Sonnet-200k azure, Haiku lime) |
| `ClauDe` | Working directory — rainbow alias (configurable, normal weight) |
| `██████────` | Context window usage bar — shaded fill (░▒▓█), cyan → red gradient |
| `58%` | Context window usage percentage |
| `7%8p` | 5-hour rate limit % + reset time (today) |
| `52%fr11a` | 7-day rate limit % + reset time (day prefix when not today) |

The account prefix lets you tell at a glance which account a Claude Code session is signed into when you run multiple accounts side-by-side via `CLAUDE_CONFIG_DIR`. The script reads `emailAddress` from `.claude.json` (checking both inside `CLAUDE_CONFIG_DIR` and one level up) and falls back silently if no email is found.

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

## Context corruption

As the context window fills past 55%, the status bar progressively self-destructs. The bar cells mutate into random block and line-drawing characters, colors wobble, glitch characters leak past the bar boundary and start consuming the model name, path, and separators. Rate limit percentages are never touched — you can always read your actual usage.

![Corruption progression from 30% to 100%](images/corruption-progression.svg)

| Range | What happens |
|-------|-------------|
| 0–55% | Clean, normal rendering |
| 55–60% | Bar cells start flickering to glitch characters |
| 60–65% | Color wobble, overflow chars leak past bar, path text catches stray glitches |
| 65–80% | Reverse video on bar cells, separators degrading, model/path visibly corrupted |
| 80–95% | Bar is mostly unrecognizable, glitch chars infest everything, separators mutate independently |
| 95–100% | The statusline has been consumed. Only the rate limit percentages survive. |

The corruption is seeded from the current timestamp, so the glitch pattern shifts on every render — it looks alive.

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

## Configuration

Create `~/.claude/statusline-config.json` to customize the working directory display:

```json
{
  "path_aliases": {
    "D:/ClauDe": "ClauDe",
    "/home/me/work/big-project": "bigproj"
  },
  "path_depth": 3,
  "rainbow_aliases": true
}
```

### Options

| Key | Default | Description |
|-----|---------|-------------|
| `path_aliases` | `{}` | Map directory prefixes to short nicknames |
| `path_depth` | `3` | Max directory segments to show |
| `rainbow_aliases` | `true` | Apply rainbow gradient to the alias nickname |

### Path alias rules

- Paths normalize to forward slashes before matching — `D:\ClauDe` and `D:/ClauDe` both work.
- Longest matching prefix wins — a specific subdirectory alias beats a parent.
- Subdirectories append after the alias: running from `D:/ClauDe/orca/clean` shows `ClauDe/orca/clean`.
- `path_depth` controls total segments shown. The alias counts as one segment, so depth 3 means alias + 2 subdirectories.
- When segments are elided, an ellipsis (`…`) appears and the alias abbreviates to its first character (teal) with the drive prefix, so you can tell the path is truncated.
- If no alias matches, the default is `~` substitution + last `path_depth` segments (also with `…/` when truncated).

### Examples

| Config | CWD | Display |
|--------|-----|---------|
| `"D:/ClauDe": "ClauDe"`, depth 3 | `D:/ClauDe` | `ClauDe` |
| `"D:/ClauDe": "ClauDe"`, depth 3 | `D:/ClauDe/orca/clean` | `ClauDe/orca/clean` |
| `"D:/ClauDe": "ClauDe"`, depth 3 | `D:/ClauDe/orca/clean/build` | `D:/C…/clean/build` |
| No alias, depth 3 | `/home/user/dev/myapp/src` | `…/dev/myapp/src` |

## Files created

| File | Purpose |
|------|---------|
| `~/.claude/statusline-command.sh` | The status line script |
| `~/.claude/statusline-config.json` | Optional — path aliases and display preferences |
| `~/.claude/statusline-state.json` | Tracks rate limit state between invocations |
| `~/.claude/rate-limit-log.jsonl` | Persistent log of rate limit threshold crossings |

## Rate limit logging

The status line logs a threshold crossing event to `~/.claude/rate-limit-log.jsonl` when either the 5-hour or 7-day rate limit window reaches **≥95%**. Each entry includes the window type (`five_hour` or `seven_day`), the percentage, and the reset timestamp.

This log file is consumed by [claude-usage](https://github.com/thereprocase/claude-usage) to render rate limit markers on its 90-day heatmap:
- **▲** (red) on days with a 5-hour spike
- **▼** (magenta) on weeks with a weekly limit breach

If you don't use claude-usage, the log file is harmless — it grows slowly (one entry per threshold crossing) and can be safely deleted.

## Known limitations

**Bash required.** The script uses `<<< here-string` syntax, which is a bashism. It will fail under `/bin/sh` on strict systems. The shebang is `#!/usr/bin/env bash` — as long as bash is on PATH, it works. On Windows, run it via Git Bash or WSL; the Claude Code `settings.json` command should be `bash ~/.claude/statusline-command.sh`, not `sh`.

**Rate limits are all-model aggregates.** The Claude Code statusline hook payload exposes `five_hour` and `seven_day` rate limit percentages combined across all models. There is no per-model breakdown available to external hooks. The `/usage` dialog in Claude Code shows per-model data; that is not accessible here.

**Regenerating renders.** Run `python generate-renders.py` to regenerate the SVG images in `images/`. Requires the statusline script and bash on PATH.

**Unicode block characters.** The bar uses Unicode block elements (U+2588, U+258x series) and separator (U+2502). These render correctly in most modern terminals. If you see garbled characters, your terminal font doesn't cover the Block Elements or Box Drawing Unicode blocks — switch to a font like JetBrains Mono, Cascadia Code, or any Nerd Font.

## License

MIT
