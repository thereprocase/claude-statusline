"""Buddy theme — the /buddy toast gradient. Sunset warmth from Claude's terminal pet."""

from core import R, DIM, BOLD, fg

# ── Buddy sunset palette (the 6 colors from the /buddy toast bar) ───────────
RED    = 167   # warm sunset red
ORANGE = 209   # sunset orange
GOLD   = 215   # golden hour
GREEN  = 114   # twilight green
BLUE   = 110   # dusk blue
VIOLET = 104   # evening violet

# The full sunset sequence for gradients
SUNSET = [VIOLET, BLUE, GREEN, GOLD, ORANGE, RED]
# Reversed for context (cool start, hot end)
SUNRISE = [BLUE, BLUE, GREEN, GREEN, GOLD, GOLD, ORANGE, ORANGE, RED, RED,
           RED, RED, RED, RED, RED, RED, RED, RED, RED, RED]

# Extended tints for variety
WARM_WHITE = 223  # sunset-lit cloud
DUSK       = 60   # deep twilight
HAZE       = 138  # purple haze

# Tier: Opus=violet, Sonnet=blue, Haiku=gold
TIER = {'opus': VIOLET, 'sonnet': BLUE, 'haiku': GOLD}

SEP = f' {fg(DUSK)}\u2502{R} '

def _sunset_color(pct):
    return SUNRISE[min(int(pct / 100 * 19), 19)]

def _rainbow_text(text, colors=None):
    """Paint text with the sunset sequence."""
    if colors is None:
        colors = SUNSET
    out = ''
    for i, ch in enumerate(text):
        if ch == ' ':
            out += ' '
        else:
            out += f'{fg(colors[i % len(colors)])}{ch}'
    return out + R

def render(ctx):
    config = ctx['config']
    used_pct = ctx['used_pct']
    tier = TIER.get(ctx['model_family'], VIOLET)
    parts = []

    # User — sunset-colored initials
    if config.get('show_user', True) and ctx['user_short']:
        parts.append(_rainbow_text(ctx['user_short'], [GOLD, ORANGE]))

    # Model — tier color
    m = ctx['model_name']
    sz = ctx['cw_str']
    label = f'{m} {sz}' if sz else m
    parts.append(f'{BOLD}{fg(tier)}{label}{R}')

    # Effort
    if ctx['effort']:
        parts.append(f'{fg(HAZE)}{ctx["effort"]}{R}')

    # Context bar — the sunset itself
    if used_pct is not None:
        N = 10
        fill = used_pct / 100 * N
        bar = ''
        for i in range(N):
            # Map bar position to sunset colors (blue horizon -> red sky)
            c = SUNRISE[i * 2]
            cell = fill - i
            if cell >= 1.0:   bar += f'{fg(c)}\u2588'
            elif cell >= 0.75:bar += f'{fg(c)}\u2593'
            elif cell >= 0.5: bar += f'{fg(c)}\u2592'
            elif cell >= 0.25:bar += f'{fg(c)}\u2591'
            else:             bar += f'{fg(DUSK)}\u2500'
        bar += R
        pc = _sunset_color(used_pct)
        parts.append(f'{bar}  {fg(pc)}{int(round(used_pct))}%{R}')

    # Rate limits — sunset colors by severity
    for rl in ctx['rate_limits']:
        pct = rl['pct']
        if pct is None:
            parts.append(f'{fg(DUSK)}{rl["label"]} --{R}')
            continue
        rc = _sunset_color(pct)
        ts = rl['reset_str']
        if ts:
            parts.append(f'{fg(HAZE)}{rl["label"]} {fg(rc)}{pct}%{fg(DUSK)}@{ts}{R}')
        else:
            parts.append(f'{fg(HAZE)}{rl["label"]} {fg(rc)}{pct}%{R}')

    # Duration
    parts.append(f'{fg(DUSK)}{ctx["session_dur"]}{R}')

    line1 = SEP.join(parts)

    # Line 2
    git = ctx['git']
    l2 = []
    if git['operation']:
        l2.append(f'{BOLD}{fg(RED)}{git["operation"]}{R}')
    if git['worktree']:
        l2.append(f'{fg(VIOLET)}[{git["worktree"]}]{R}')
    if git['branch']:
        if git['detached']:
            l2.append(f'{fg(RED)}{git["branch"]} det{R}')
        else:
            l2.append(f'{fg(GREEN)}{git["branch"]}{R}')
        if git['remote_short']:
            l2.append(f'{fg(DUSK)}\u2192{fg(BLUE)}{git["remote_short"]}{R}')
        ab = ''
        if git['ahead']:  ab += f'{fg(GREEN)}\u2191{git["ahead"]}{R}'
        if git['behind']: ab += f'{fg(ORANGE)}\u2193{git["behind"]}{R}'
        if ab: l2.append(ab)
    if git['dirty']:
        l2.append(f'{fg(GOLD)}+{git["dirty"]}{R}')
    if git['stash']:
        l2.append(f'{fg(VIOLET)}\u2691{git["stash"]}{R}')

    path = ctx['path_display']
    if path:
        l2.append(f'{fg(WARM_WHITE)}{path}{R}')

    # Sunset bar prefix
    prefix = f'{fg(VIOLET)}\u2588{fg(BLUE)}\u2588{fg(GREEN)}\u2588{fg(GOLD)}\u2588{fg(ORANGE)}\u2588{fg(RED)}\u2588{R} '
    line2 = prefix + ' '.join(l2) if l2 else ''

    return f'{line1}\n{line2}' if line2 else line1
