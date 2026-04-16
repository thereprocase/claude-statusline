# Claude Code Status Line

A colorful, information-dense, themeable status line for [Claude Code](https://claude.ai/code).

![Clean statusline at 30% context](images/statusline-clean.svg)

## Themes

Six built-in themes. Switch anytime — no reinstall needed.

| Theme | Description |
|-------|-------------|
| `rainbow` | The original. Sherwin-Williams SHIFT palette, corruption glitch effects past 55% context. |
| `lcars` | Star Trek TNG. Solid colored pill chips, eggplant panel bars, everything uppercase. |
| `monochrome` | Grayscale only. Clean, professional, no color. |
| `skittles` | Every character a different candy color. Stars for separators. Unhinged. |
| `outrun` | Synthwave. Hot pink, electric cyan, chrome, neon purple, sunset gradients. |
| `ibm3278` | Green phosphor CRT. Four intensity levels, `==>` prompt. Mainframe vibes. |

## Install

```bash
git clone https://github.com/thereprocase/claude-statusline.git
cd claude-statusline
bash install.sh
```

First install prompts for a theme, then offers the interactive setup walkthrough to configure model format, user initials, date style, and more.

Restart Claude Code to activate.

## Interactive Setup

Run the full configurator anytime:

```bash
bash setup.sh
```

This walks you through:
- **Theme** — pick from all available themes, with optional side-by-side previews
- **Model format** — `short` (`Op46`), `long` (`Opus 4.6`), or `full` (`Claude Opus 4.6`)
- **User initials** — on/off (2-char account prefix chip)
- **Date format** — `short` (`3p`, `th`) or `long` (`3:00pm`, `thu`)
- **Auto-hide reset** — only show reset times when usage is meaningful

Settings are saved to `~/.claude/statusline-config.json` and persist across updates.

## Quick Theme Switch

```bash
bash theme.sh lcars
```

Or without arguments to see what's available:

```bash
bash theme.sh
```

Or the manual way:

```bash
echo outrun > ~/.claude/statusline-theme
```

Takes effect on the next Claude Code tool call.

## Update

```bash
cd claude-statusline
git pull
bash install.sh
```

Updates keep your current theme and config. All theme files are refreshed.

## Layout

Two lines. Line 1 is the dashboard, line 2 is where you are.

```
kn │ Op46 1M │ ██████──── 42% │ 5h 38% │ 7d 15% │ 12m
main →gl:owner │ /path/to/project
```

### Line 1

| Section | Description |
|---------|-------------|
| `kn` | First 2 chars of the active Claude account email — styled per theme |
| `Op46 1M` | Model abbreviation + context window size — tier colored |
| `██████──── 42%` | Context window usage bar + percentage |
| `5h 38%` | 5-hour rate limit % (+ reset time when usage is high) |
| `7d 15%` | 7-day rate limit % (+ reset time when usage is high) |
| `12m` | Session duration — resets on new session |

### Line 2

| Section | Description |
|---------|-------------|
| `main` | Git branch (styled per theme; omitted if not a git repo) |
| `→gl:owner` | Remote tracking (host:owner format) |
| `▲3 ▼2` | Commits ahead/behind upstream |
| `Δ7` | Dirty file count |
| `⚑2` | Stash entries |
| `/path/to/project` | Working directory — always prominent, never dimmed |

All git info is optional and gracefully hidden when not in a repo.

### Path truncation

Paths under 75 characters are shown in full. Longer paths truncate to:

```
F:/Cl.../products/fieldLog/src/components
```

### Reset time format

| Format | Meaning |
|--------|---------|
| `5p` | Resets at 5 PM today |
| `mo9a` | Resets Monday at 9 AM |

Reset times auto-hide when usage is low (configurable via setup).

### Model abbreviations (short format)

| Model | Short | Long |
|-------|-------|------|
| Claude Opus 4.6 | `Op46` | `Opus 4.6` |
| Claude Opus 4.5 | `Op45` | `Opus 4.5` |
| Claude Sonnet 4.6 | `Sn46` | `Sonnet 4.6` |
| Claude Sonnet 4.5 | `Sn45` | `Sonnet 4.5` |
| Claude Haiku 4.5 | `Hk45` | `Haiku 4.5` |

## Context Corruption (rainbow theme)

As the context window fills past 55%, the rainbow theme's status bar progressively self-destructs. Bar cells mutate into random block characters, colors wobble, glitch characters leak past the bar boundary. Rate limit percentages are never touched — you can always read your actual usage.

![Corruption progression from 30% to 100%](images/corruption-progression.svg)

| Range | What happens |
|-------|-------------|
| 0–55% | Clean, normal rendering |
| 55–70% | Bar cells flicker, color wobble begins |
| 70–85% | Reverse video, separators degrading, overflow leaks |
| 85–100% | Consumed. Only rate limits survive. |

## Architecture

```
~/.claude/
  statusline-command.sh     # 13-line bash dispatcher
  statusline-theme          # plain text: "rainbow", "lcars", etc.
  statusline-config.json    # user preferences (model format, dates, etc.)
  statusline-state.json     # rate limit state between invocations
  rate-limit-log.jsonl      # threshold crossing log (auto-rotated)
  statusline/
    core.py                 # shared: parsing, storage, git, rate limits
    rainbow.py              # rainbow theme renderer
    lcars.py                # LCARS theme renderer
    monochrome.py           # monochrome theme renderer
    skittles.py             # skittles theme renderer
    outrun.py               # outrun theme renderer
    ibm3278.py              # IBM 3278 theme renderer
```

The dispatcher reads `statusline-theme`, imports the matching Python module, calls `render(ctx)`. Themes are single files with one function. Adding a theme = adding one `.py` file.

## Requirements

- Claude Code v2.1+
- Python 3.6+ on PATH
- Bash
- Git (for branch/remote display — gracefully omitted if unavailable)

Works on Windows (Git Bash or WSL), macOS, and Linux.

## Uninstall

```bash
bash uninstall.sh
```

## Rate Limit Logging

The status line logs a threshold crossing event to `~/.claude/rate-limit-log.jsonl` when either rate limit window reaches **≥95%**. Entries older than 60 days are automatically pruned. This log is consumed by [claude-usage](https://github.com/thereprocase/claude-usage) for heatmap markers.

## Known Limitations

**Bash required.** Uses `<<< here-string` syntax. Run via `bash`, not `sh`.

**Git subprocess per refresh.** Branch display calls `git rev-parse` each render (~50ms, 2s timeout).

**Unicode block characters.** The bar uses Unicode block elements. If garbled, switch to JetBrains Mono, Cascadia Code, or any Nerd Font.

## License

MIT
