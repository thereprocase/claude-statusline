"""Dracula theme — the beloved dark palette. Purple, pink, cyan, green on dark."""

from core import R, DIM, BOLD, fg

# ── Dracula palette (official hex -> xterm-256) ─────────────────────────────
BG         = 236   # #282a36 background
FG_COLOR   = 253   # #f8f8f2 foreground
COMMENT    = 103   # #6272a4 comment
CYAN_D     = 81    # #8be9fd cyan
GREEN_D    = 84    # #50fa7b green
ORANGE_D   = 215   # #ffb86c orange
PINK       = 212   # #ff79c6 pink
PURPLE     = 141   # #bd93f9 purple
RED_D      = 203   # #ff5555 red
YELLOW_D   = 228   # #f1fa8c yellow

SEP = f' {fg(COMMENT)}\u2502{R} '

# Tier: Opus=purple, Sonnet=cyan, Haiku=green
TIER = {'opus': PURPLE, 'sonnet': CYAN_D, 'haiku': GREEN_D}

GRAD = [
    CYAN_D, CYAN_D, CYAN_D, CYAN_D, GREEN_D,
    GREEN_D, GREEN_D, YELLOW_D, YELLOW_D, YELLOW_D,
    ORANGE_D, ORANGE_D, ORANGE_D, PINK, PINK,
    RED_D, RED_D, RED_D, RED_D, RED_D,
]

def _grad_color(pct):
    return GRAD[min(int(pct / 100 * 19), 19)]

def render(ctx):
    config = ctx['config']
    used_pct = ctx['used_pct']
    tier = TIER.get(ctx['model_family'], PURPLE)
    parts = []

    if config.get('show_user', True) and ctx['user_short']:
        parts.append(f'{BOLD}{fg(PINK)}{ctx["user_short"]}{R}')

    m = ctx['model_name']
    sz = ctx['cw_str']
    label = f'{m} {sz}' if sz else m
    parts.append(f'{BOLD}{fg(tier)}{label}{R}')

    if ctx['effort']:
        parts.append(f'{fg(COMMENT)}{ctx["effort"]}{R}')

    if used_pct is not None:
        N = 10
        fill = used_pct / 100 * N
        bar = ''
        for i in range(N):
            c = GRAD[i * 2]
            cell = fill - i
            if cell >= 1.0:   bar += f'{fg(c)}\u2588'
            elif cell >= 0.75:bar += f'{fg(c)}\u2593'
            elif cell >= 0.5: bar += f'{fg(c)}\u2592'
            elif cell >= 0.25:bar += f'{fg(c)}\u2591'
            else:             bar += f'{fg(COMMENT)}\u2500'
        bar += R
        pc = _grad_color(used_pct)
        parts.append(f'{bar}  {fg(pc)}{int(round(used_pct))}%{R}')

    for rl in ctx['rate_limits']:
        pct = rl['pct']
        if pct is None:
            parts.append(f'{fg(COMMENT)}{rl["label"]} --{R}')
            continue
        rc = _grad_color(pct)
        ts = rl['reset_str']
        if ts:
            parts.append(f'{fg(COMMENT)}{rl["label"]} {fg(rc)}{pct}%{fg(COMMENT)}@{ts}{R}')
        else:
            parts.append(f'{fg(COMMENT)}{rl["label"]} {fg(rc)}{pct}%{R}')

    parts.append(f'{fg(COMMENT)}{ctx["session_dur"]}{R}')

    line1 = SEP.join(parts)

    git = ctx['git']
    l2 = []
    if git['operation']:
        l2.append(f'{BOLD}{fg(RED_D)}{git["operation"]}{R}')
    if git['worktree']:
        l2.append(f'{fg(PURPLE)}[{git["worktree"]}]{R}')
    if git['branch']:
        if git['detached']:
            l2.append(f'{fg(RED_D)}{git["branch"]} det{R}')
        else:
            l2.append(f'{fg(GREEN_D)}{git["branch"]}{R}')
        if git['remote_short']:
            l2.append(f'{fg(COMMENT)}\u2192{fg(PURPLE)}{git["remote_short"]}{R}')
        ab = ''
        if git['ahead']:  ab += f'{fg(GREEN_D)}\u2191{git["ahead"]}{R}'
        if git['behind']: ab += f'{fg(RED_D)}\u2193{git["behind"]}{R}'
        if ab: l2.append(ab)
    if git['dirty']:
        l2.append(f'{fg(ORANGE_D)}+{git["dirty"]}{R}')
    if git['stash']:
        l2.append(f'{fg(PURPLE)}\u2691{git["stash"]}{R}')

    path = ctx['path_display']
    if path:
        l2.append(f'{fg(FG_COLOR)}{path}{R}')

    line2 = ' '.join(l2) if l2 else ''
    return f'{line1}\n{line2}' if line2 else line1
