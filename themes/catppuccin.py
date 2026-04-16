"""Catppuccin theme — Mocha variant. Warm pastels on dark. Cozy."""

from core import R, DIM, BOLD, fg

# ── Catppuccin Mocha palette (official hex -> xterm-256) ────────────────────
ROSEWATER  = 224   # #f5e0dc
FLAMINGO   = 217   # #f2cdcd
PINK       = 211   # #f5c2e7
MAUVE      = 141   # #cba6f7
RED        = 203   # #f38ba8
MAROON     = 174   # #eba0ac
PEACH      = 209   # #fab387
YELLOW     = 222   # #f9e2af
GREEN      = 115   # #a6e3a1
TEAL       = 116   # #94e2d5
SKY        = 117   # #89dceb
SAPPHIRE   = 74    # #74c7ec
BLUE       = 111   # #89b4fa
LAVENDER   = 147   # #b4befe
TEXT       = 254   # #cdd6f4
SUBTEXT1   = 249   # #bac2de
SUBTEXT0   = 245   # #a6adc8
OVERLAY2   = 243   # #9399b2
OVERLAY1   = 240   # #7f849c
OVERLAY0   = 238   # #6c7086
SURFACE2   = 236   # #585b70
SURFACE1   = 235   # #45475a
SURFACE0   = 234   # #313244
BASE       = 233   # #1e1e2e
MANTLE     = 232   # #181825
CRUST      = 16    # #11111b

SEP = f' {fg(OVERLAY0)}\u2502{R} '

# Tier: Opus=mauve, Sonnet=blue, Haiku=green
TIER = {'opus': MAUVE, 'sonnet': BLUE, 'haiku': GREEN}

GRAD = [
    BLUE, BLUE, SAPPHIRE, SAPPHIRE, TEAL,
    GREEN, GREEN, YELLOW, YELLOW, YELLOW,
    PEACH, PEACH, PEACH, MAROON, MAROON,
    RED, RED, RED, RED, RED,
]

def _grad_color(pct):
    return GRAD[min(int(pct / 100 * 19), 19)]

def render(ctx):
    config = ctx['config']
    used_pct = ctx['used_pct']
    tier = TIER.get(ctx['model_family'], MAUVE)
    parts = []

    if config.get('show_user', True) and ctx['user_short']:
        parts.append(f'{BOLD}{fg(FLAMINGO)}{ctx["user_short"]}{R}')

    m = ctx['model_name']
    sz = ctx['cw_str']
    label = f'{m} {sz}' if sz else m
    parts.append(f'{BOLD}{fg(tier)}{label}{R}')

    if ctx['effort']:
        parts.append(f'{fg(OVERLAY1)}{ctx["effort"]}{R}')

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
            else:             bar += f'{fg(SURFACE2)}\u2500'
        bar += R
        pc = _grad_color(used_pct)
        parts.append(f'{bar}  {fg(pc)}{int(round(used_pct))}%{R}')

    for rl in ctx['rate_limits']:
        pct = rl['pct']
        if pct is None:
            parts.append(f'{fg(SURFACE2)}{rl["label"]} --{R}')
            continue
        rc = _grad_color(pct)
        ts = rl['reset_str']
        if ts:
            parts.append(f'{fg(OVERLAY0)}{rl["label"]} {fg(rc)}{pct}%{fg(OVERLAY0)}@{ts}{R}')
        else:
            parts.append(f'{fg(OVERLAY0)}{rl["label"]} {fg(rc)}{pct}%{R}')

    parts.append(f'{fg(SURFACE2)}{ctx["session_dur"]}{R}')

    line1 = SEP.join(parts)

    git = ctx['git']
    l2 = []
    if git['operation']:
        l2.append(f'{BOLD}{fg(RED)}{git["operation"]}{R}')
    if git['worktree']:
        l2.append(f'{fg(MAUVE)}[{git["worktree"]}]{R}')
    if git['branch']:
        if git['detached']:
            l2.append(f'{fg(RED)}{git["branch"]} det{R}')
        else:
            l2.append(f'{fg(GREEN)}{git["branch"]}{R}')
        if git['remote_short']:
            l2.append(f'{fg(OVERLAY0)}\u2192{fg(LAVENDER)}{git["remote_short"]}{R}')
        ab = ''
        if git['ahead']:  ab += f'{fg(TEAL)}\u2191{git["ahead"]}{R}'
        if git['behind']: ab += f'{fg(MAROON)}\u2193{git["behind"]}{R}'
        if ab: l2.append(ab)
    if git['dirty']:
        l2.append(f'{fg(PEACH)}+{git["dirty"]}{R}')
    if git['stash']:
        l2.append(f'{fg(MAUVE)}\u2691{git["stash"]}{R}')

    path = ctx['path_display']
    if path:
        l2.append(f'{fg(TEXT)}{path}{R}')

    line2 = ' '.join(l2) if l2 else ''
    return f'{line1}\n{line2}' if line2 else line1
