"""Monochrome theme — grayscale terminal. Clean, no-nonsense, 1990s workstation."""

from core import R, BOLD, fg, render_standard

# ── Grayscale palette (xterm-256 grays: 232-255) ───────────────────────────
WHITE  = 255
BRIGHT = 253
MID    = 249
MUTED  = 245
DARK   = 240
DARKER = 237
FAINT  = 235

SEP = f' {fg(DARK)}\u2502{R} '

def _pct_shade(pct):
    """Higher usage = brighter (more alarming)."""
    if pct >= 80: return WHITE
    if pct >= 60: return BRIGHT
    if pct >= 40: return MID
    if pct >= 20: return MUTED
    return DARK

def _mono_user(text, theme):
    return f'{fg(MUTED)}{text}{R}'

def _mono_model(label, tier_color, theme):
    """Two-tone model chip: bright name, dark context size."""
    # label is "Op46 1M" or just "Op46"
    parts = label.rsplit(' ', 1)
    if len(parts) == 2 and parts[1]:
        return f'{BOLD}{fg(BRIGHT)}{parts[0]}{R}{fg(DARK)} {parts[1]}{R}'
    return f'{BOLD}{fg(BRIGHT)}{label}{R}'

def _mono_bar(used_pct, theme):
    """Grayscale bar: position-based brightness, brighter = more alarming."""
    N = 10
    fill = used_pct / 100 * N
    bar = ''
    for i in range(N):
        cell = fill - i
        shade = DARKER if cell < 0.25 else (MID if i < N * 0.6 else BRIGHT if i < N * 0.8 else WHITE)
        if cell >= 1.0:    ch = '\u2588'
        elif cell >= 0.75: ch = '\u2593'
        elif cell >= 0.5:  ch = '\u2592'
        elif cell >= 0.25: ch = '\u2591'
        else:              ch = '\u2500'
        bar += f'{fg(shade)}{ch}'
    bar += R
    pc = _pct_shade(used_pct)
    return f'{bar}  {fg(pc)}{int(round(used_pct))}%{R}'

def _mono_rl(rl, theme):
    """Monochrome rate limit with threshold-based brightness."""
    pct = rl['pct']
    if pct is None:
        return ''
    shade = _pct_shade(pct)
    ts = rl['reset_str']
    if ts:
        return f'{fg(DARK)}{rl["label"]} {fg(shade)}{pct}%{fg(DARKER)}@{ts}{R}'
    return f'{fg(DARK)}{rl["label"]} {fg(shade)}{pct}%{R}'

THEME = {
    'sep': SEP,
    'grad': [],  # unused — monochrome uses threshold-based shading
    'tier': {'opus': BRIGHT, 'sonnet': BRIGHT, 'haiku': BRIGHT},
    'tier_default': BRIGHT,
    'user_chip': _mono_user,
    'model_chip': _mono_model,
    'bar_fn': _mono_bar,
    'rl_fn': _mono_rl,
    'colors': {
        'user': MUTED, 'effort': MUTED, 'duration': DARKER,
        'empty_bar': DARKER,
        'rl_label': DARK, 'rl_reset': DARKER, 'rl_null': DARKER,
        'operation': WHITE, 'worktree': MUTED,
        'branch': MUTED, 'detached': BRIGHT,
        'remote_arrow': DARKER, 'remote': DARKER,
        'ahead': BRIGHT, 'behind': BRIGHT,
        'dirty': MUTED, 'stash': DARKER, 'path': BRIGHT,
    },
    'line2_path_sep': SEP,
}

def render(ctx):
    return render_standard(ctx, THEME)
