"""Monochrome theme — grayscale terminal. Clean, no-nonsense, 1990s workstation."""

from core import R, DIM, BOLD, fg

# ── Grayscale palette (xterm-256 grays: 232-255) ───────────────────────────
WHITE  = 255
BRIGHT = 253
MID    = 249
MUTED  = 245
DARK   = 240
DARKER = 237
FAINT  = 235

SEP = f' {fg(DARK)}\u2502{R} '

def _bar_char(fill_level):
    if fill_level >= 1.0:  return '\u2588'
    if fill_level >= 0.75: return '\u2593'
    if fill_level >= 0.5:  return '\u2592'
    if fill_level >= 0.25: return '\u2591'
    return '\u2500'

def _pct_shade(pct):
    """Higher usage = brighter (more alarming)."""
    if pct >= 80: return WHITE
    if pct >= 60: return BRIGHT
    if pct >= 40: return MID
    if pct >= 20: return MUTED
    return DARK

def render(ctx):
    config = ctx['config']
    used_pct = ctx['used_pct']
    parts = []

    # User
    if config.get('show_user', True) and ctx['user_short']:
        parts.append(f'{fg(MUTED)}{ctx["user_short"]}{R}')

    # Model
    parts.append(f'{BOLD}{fg(BRIGHT)}{ctx["model_name"]}{R}{fg(DARK)} {ctx["cw_str"]}{R}' if ctx['cw_str'] else f'{BOLD}{fg(BRIGHT)}{ctx["model_name"]}{R}')

    # Effort
    if ctx['effort']:
        parts.append(f'{fg(MUTED)}{ctx["effort"]}{R}')

    # Context bar
    if used_pct is not None:
        N = 10
        fill = used_pct / 100 * N
        bar = ''
        for i in range(N):
            cell = fill - i
            shade = DARKER if cell < 0.25 else (MID if i < N * 0.6 else BRIGHT if i < N * 0.8 else WHITE)
            bar += f'{fg(shade)}{_bar_char(cell)}'
        bar += R
        pc = _pct_shade(used_pct)
        parts.append(f'{bar}  {fg(pc)}{int(round(used_pct))}%{R}')

    # Rate limits
    for rl in ctx['rate_limits']:
        pct = rl['pct']
        if pct is None:
            parts.append(f'{fg(DARKER)}{rl["label"]} --{R}')
            continue
        shade = _pct_shade(pct)
        ts = rl['reset_str']
        if ts:
            parts.append(f'{fg(DARK)}{rl["label"]} {fg(shade)}{pct}%{fg(DARKER)}@{ts}{R}')
        else:
            parts.append(f'{fg(DARK)}{rl["label"]} {fg(shade)}{pct}%{R}')

    # Duration
    parts.append(f'{fg(DARKER)}{ctx["session_dur"]}{R}')

    line1 = SEP.join(parts)

    # Line 2
    git = ctx['git']
    l2 = []
    if git['operation']:
        l2.append(f'{BOLD}{fg(WHITE)}{git["operation"]}{R}')
    if git['worktree']:
        l2.append(f'{fg(MUTED)}[{git["worktree"]}]{R}')
    if git['branch']:
        if git['detached']:
            l2.append(f'{fg(BRIGHT)}{git["branch"]} det{R}')
        else:
            l2.append(f'{fg(MUTED)}{git["branch"]}{R}')
        if git['remote_short']:
            l2.append(f'{fg(DARKER)}\u2192{git["remote_short"]}{R}')
        ab = ''
        if git['ahead']:
            ab += f'{fg(BRIGHT)}\u2191{git["ahead"]}{R}'
        if git['behind']:
            ab += f'{fg(BRIGHT)}\u2193{git["behind"]}{R}'
        if ab:
            l2.append(ab)
    if git['dirty']:
        l2.append(f'{fg(MUTED)}+{git["dirty"]}{R}')
    if git['stash']:
        l2.append(f'{fg(DARKER)}\u2691{git["stash"]}{R}')

    path = ctx['path_display']
    git_str = ' '.join(l2) if l2 else ''
    path_str = f'{fg(BRIGHT)}{path}{R}' if path else ''

    line2_parts = [p for p in [git_str, path_str] if p]
    line2 = SEP.join(line2_parts)

    return f'{line1}\n{line2}' if line2 else line1
