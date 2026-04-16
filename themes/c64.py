"""C64 theme — Commodore 64. Light blue on dark blue. READY."""

from core import R, DIM, BOLD, fg, bg

# ── C64 palette (xterm-256 approximations) ──────────────────────────────────
# The C64 had 16 colors. The iconic look is light blue text on dark blue bg.
LIGHT_BLUE = 75    # C64 light blue (foreground)
DARK_BLUE  = 18    # C64 dark blue (background feel)
WHITE      = 15
CYAN       = 44    # C64 cyan
GREEN      = 71    # C64 green
RED        = 124   # C64 red
YELLOW     = 226   # C64 yellow
ORANGE     = 208   # C64 orange
BROWN      = 130   # C64 brown
LIGHT_GRN  = 114   # C64 light green
GREY       = 246   # C64 medium grey
DK_GREY    = 240   # C64 dark grey

SEP = f' {fg(DARK_BLUE)}\u2502{R} '

def _c64_color(pct):
    if pct >= 90: return RED
    if pct >= 70: return ORANGE
    if pct >= 50: return YELLOW
    if pct >= 30: return GREEN
    return LIGHT_BLUE

def render(ctx):
    config = ctx['config']
    used_pct = ctx['used_pct']
    parts = []

    if config.get('show_user', True) and ctx['user_short']:
        parts.append(f'{BOLD}{fg(WHITE)}{ctx["user_short"].upper()}{R}')

    m = ctx['model_name'].upper()
    sz = ctx['cw_str']
    label = f'{m} {sz}' if sz else m
    parts.append(f'{BOLD}{fg(CYAN)}{label}{R}')

    if ctx['effort']:
        parts.append(f'{fg(DK_GREY)}{ctx["effort"]}{R}')

    # Context bar — C64 block characters
    if used_pct is not None:
        N = 10
        fill = used_pct / 100 * N
        bar = ''
        for i in range(N):
            cell = fill - i
            c = _c64_color(i * 10)
            if cell >= 1.0:   bar += f'{fg(c)}\u2588'
            elif cell >= 0.5: bar += f'{fg(c)}\u2592'
            elif cell >= 0.25:bar += f'{fg(DARK_BLUE)}\u2591'
            else:             bar += f'{fg(DARK_BLUE)}\u2500'
        bar += R
        pc = _c64_color(used_pct)
        parts.append(f'{bar}  {fg(pc)}{int(round(used_pct))}%{R}')

    for rl in ctx['rate_limits']:
        pct = rl['pct']
        if pct is None:
            parts.append(f'{fg(DK_GREY)}{rl["label"]} --{R}')
            continue
        rc = _c64_color(pct)
        ts = rl['reset_str']
        if ts:
            parts.append(f'{fg(LIGHT_BLUE)}{rl["label"]} {fg(rc)}{pct}%{fg(DK_GREY)}@{ts}{R}')
        else:
            parts.append(f'{fg(LIGHT_BLUE)}{rl["label"]} {fg(rc)}{pct}%{R}')

    parts.append(f'{fg(DK_GREY)}{ctx["session_dur"]}{R}')

    line1 = SEP.join(parts)

    # Line 2 — READY. prompt style
    git = ctx['git']
    l2 = []
    if git['operation']:
        l2.append(f'{BOLD}{fg(RED)}{git["operation"]}{R}')
    if git['worktree']:
        l2.append(f'{fg(GREEN)}[{git["worktree"]}]{R}')
    if git['branch']:
        if git['detached']:
            l2.append(f'{fg(RED)}{git["branch"]} DET{R}')
        else:
            l2.append(f'{fg(LIGHT_GRN)}{git["branch"]}{R}')
        if git['remote_short']:
            l2.append(f'{fg(DK_GREY)}\u2192{git["remote_short"]}{R}')
        ab = ''
        if git['ahead']:  ab += f'{fg(GREEN)}\u2191{git["ahead"]}{R}'
        if git['behind']: ab += f'{fg(RED)}\u2193{git["behind"]}{R}'
        if ab: l2.append(ab)
    if git['dirty']:
        l2.append(f'{fg(YELLOW)}+{git["dirty"]}{R}')
    if git['stash']:
        l2.append(f'{fg(GREY)}\u2691{git["stash"]}{R}')

    path = ctx['path_display']
    if path:
        l2.append(f'{fg(LIGHT_BLUE)}{path}{R}')

    # The blinking cursor prompt
    prefix = f'{fg(LIGHT_BLUE)}READY.{R} '
    line2 = prefix + ' '.join(l2) if l2 else ''

    return f'{line1}\n{line2}' if line2 else line1
