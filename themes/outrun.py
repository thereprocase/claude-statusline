"""Outrun theme — synthwave sunset. Hot pink, electric cyan, chrome, neon purple."""

from core import R, DIM, BOLD, fg, bg

# ── Synthwave palette ───────────────────────────────────────────────────────
HOT_PINK    = 199   # neon magenta
ELECTRIC    = 51    # electric cyan
CHROME      = 252   # bright chrome/silver
NEON_PURPLE = 135   # deep neon purple
SUNSET_ORG  = 208   # sunset orange
SUNSET_RED  = 196   # horizon red
GRID        = 93    # the perspective grid purple
DARK_CHROME = 243   # muted chrome
VOID        = 236   # dark background reference
LASER       = 201   # laser pink

# Model tier: Opus=hot pink, Sonnet=electric cyan, Haiku=sunset orange
TIER = {'opus': HOT_PINK, 'sonnet': ELECTRIC, 'haiku': SUNSET_ORG}

# Context: cool cyan -> chrome -> sunset -> hot pink -> laser
CTX_GRAD = [
    ELECTRIC, ELECTRIC, ELECTRIC, 45, 44,
    CHROME, CHROME, SUNSET_ORG, SUNSET_ORG, SUNSET_ORG,
    HOT_PINK, HOT_PINK, HOT_PINK, LASER, LASER,
    SUNSET_RED, SUNSET_RED, SUNSET_RED, SUNSET_RED, SUNSET_RED,
]

RL_GRAD = [
    ELECTRIC, ELECTRIC, ELECTRIC, ELECTRIC, CHROME,
    CHROME, CHROME, SUNSET_ORG, SUNSET_ORG, SUNSET_ORG,
    HOT_PINK, HOT_PINK, HOT_PINK, HOT_PINK, LASER,
    LASER, SUNSET_RED, SUNSET_RED, SUNSET_RED, SUNSET_RED,
]

# Separator: the grid line
SEP = f' {fg(GRID)}\u2502{R} '
HLINE = '\u2500'

def _grad(pct, grad):
    return grad[min(int(pct / 100 * (len(grad) - 1)), len(grad) - 1)]

def _neon(text, color):
    """Bold neon text — the synthwave glow."""
    return f'{BOLD}{fg(color)}{text}{R}'

def _chrome_text(text):
    return f'{fg(CHROME)}{text}{R}'

def render(ctx):
    config = ctx['config']
    used_pct = ctx['used_pct']
    tier_color = TIER.get(ctx['model_family'], ELECTRIC)
    parts = []

    # User — chrome initials
    if config.get('show_user', True) and ctx['user_short']:
        parts.append(_neon(ctx['user_short'], CHROME))

    # Model — tier neon
    m = ctx['model_name']
    sz = ctx['cw_str']
    label = f'{m} {sz}' if sz else m
    parts.append(_neon(label, tier_color))

    # Effort
    if ctx['effort']:
        parts.append(f'{fg(DARK_CHROME)}{ctx["effort"]}{R}')

    # Context bar — sunset gradient
    if used_pct is not None:
        N = 10
        fill = used_pct / 100 * N
        bar = ''
        for i in range(N):
            c = CTX_GRAD[i * 2]
            cell = fill - i
            if cell >= 1.0:   bar += f'{fg(c)}\u2588'
            elif cell >= 0.75:bar += f'{fg(c)}\u2593'
            elif cell >= 0.5: bar += f'{fg(c)}\u2592'
            elif cell >= 0.25:bar += f'{fg(c)}\u2591'
            else:             bar += f'{fg(GRID)}{HLINE}'
        bar += R
        pc = _grad(used_pct, CTX_GRAD)
        parts.append(f'{bar}  {fg(pc)}{int(round(used_pct))}%{R}')

    # Rate limits
    for rl in ctx['rate_limits']:
        pct = rl['pct']
        if pct is None:
            parts.append(f'{fg(GRID)}{rl["label"]} --{R}')
            continue
        rc = _grad(pct, RL_GRAD)
        ts = rl['reset_str']
        if ts:
            parts.append(f'{fg(GRID)}{rl["label"]} {fg(rc)}{pct}%{fg(NEON_PURPLE)}@{ts}{R}')
        else:
            parts.append(f'{fg(GRID)}{rl["label"]} {fg(rc)}{pct}%{R}')

    # Duration — grid purple
    parts.append(f'{fg(GRID)}{ctx["session_dur"]}{R}')

    line1 = SEP.join(parts)

    # Line 2 — the grid
    git = ctx['git']
    l2 = []
    if git['operation']:
        l2.append(_neon(git['operation'], SUNSET_RED))
    if git['worktree']:
        l2.append(f'{fg(NEON_PURPLE)}[{git["worktree"]}]{R}')
    if git['branch']:
        if git['detached']:
            l2.append(_neon(f'{git["branch"]} det', SUNSET_RED))
        else:
            l2.append(_neon(git['branch'], ELECTRIC))
        if git['remote_short']:
            l2.append(f'{fg(GRID)}\u2192{fg(NEON_PURPLE)}{git["remote_short"]}{R}')
        ab = ''
        if git['ahead']:
            ab += f'{fg(ELECTRIC)}\u2191{git["ahead"]}{R}'
        if git['behind']:
            ab += f'{fg(HOT_PINK)}\u2193{git["behind"]}{R}'
        if ab:
            l2.append(ab)
    if git['dirty']:
        l2.append(f'{fg(SUNSET_ORG)}+{git["dirty"]}{R}')
    if git['stash']:
        l2.append(f'{fg(NEON_PURPLE)}\u2691{git["stash"]}{R}')

    path = ctx['path_display']
    if path:
        l2.append(f'{fg(CHROME)}{path}{R}')

    # Grid prefix
    prefix = f'{fg(GRID)}{HLINE}{HLINE}{R} '
    line2 = prefix + ' '.join(l2) if l2 else ''

    return f'{line1}\n{line2}' if line2 else line1
