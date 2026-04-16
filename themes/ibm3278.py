"""IBM 3278 theme — green phosphor CRT terminal. The mainframe is watching."""

from core import R, DIM, BOLD, fg

# ── P1 Green Phosphor palette ──────────────────────────────────────────────
# Classic IBM 3278/3279 monochrome green phosphor display
BRIGHT  = 46    # full intensity green (P1 phosphor peak)
NORMAL  = 34    # standard intensity
DK_GRN  = 28    # dim green
FAINT   = 22    # barely visible green
SHADOW  = 236   # CRT off / shadow

# The 3278 had 4 intensity levels. We map to those.
# Bright = high intensity (protected fields, headers)
# Normal = normal intensity (input/data)
# Dim    = non-display or low intensity
# Off    = blank positions

SEP = f' {fg(FAINT)}\u2502{R} '

def _intensity(pct):
    """Map percentage to phosphor intensity."""
    if pct >= 80: return BRIGHT
    if pct >= 50: return NORMAL
    if pct >= 20: return DK_GRN
    return FAINT

def render(ctx):
    config = ctx['config']
    used_pct = ctx['used_pct']
    parts = []

    # User — high intensity
    if config.get('show_user', True) and ctx['user_short']:
        parts.append(f'{BOLD}{fg(BRIGHT)}{ctx["user_short"].upper()}{R}')

    # Model
    m = ctx['model_name'].upper()
    sz = ctx['cw_str']
    label = f'{m} {sz}' if sz else m
    parts.append(f'{BOLD}{fg(BRIGHT)}{label}{R}')

    # Effort
    if ctx['effort']:
        parts.append(f'{fg(DK_GRN)}{ctx["effort"]}{R}')

    # Context bar — phosphor intensity fill
    if used_pct is not None:
        N = 10
        fill = used_pct / 100 * N
        bar = ''
        for i in range(N):
            cell = fill - i
            if cell >= 1.0:
                # Brighter as we go higher
                if i >= 8:    bar += f'{fg(BRIGHT)}\u2588'
                elif i >= 5:  bar += f'{fg(NORMAL)}\u2588'
                else:         bar += f'{fg(DK_GRN)}\u2588'
            elif cell >= 0.5: bar += f'{fg(DK_GRN)}\u2593'
            elif cell >= 0.25:bar += f'{fg(FAINT)}\u2591'
            else:             bar += f'{fg(SHADOW)}\u2500'
        bar += R
        pc = _intensity(used_pct)
        parts.append(f'{bar}  {fg(pc)}{int(round(used_pct))}%{R}')

    # Rate limits
    for rl in ctx['rate_limits']:
        pct = rl['pct']
        if pct is None:
            parts.append(f'{fg(FAINT)}{rl["label"].upper()} --{R}')
            continue
        ic = _intensity(pct)
        ts = rl['reset_str'].upper() if rl['reset_str'] else ''
        if ts:
            parts.append(f'{fg(DK_GRN)}{rl["label"].upper()} {fg(ic)}{pct}%{fg(FAINT)}@{ts}{R}')
        else:
            parts.append(f'{fg(DK_GRN)}{rl["label"].upper()} {fg(ic)}{pct}%{R}')

    # Duration — dim
    parts.append(f'{fg(FAINT)}{ctx["session_dur"].upper()}{R}')

    line1 = SEP.join(parts)

    # Line 2 — command line area
    git = ctx['git']
    l2 = []
    if git['operation']:
        l2.append(f'{BOLD}{fg(BRIGHT)}{git["operation"]}{R}')
    if git['worktree']:
        l2.append(f'{fg(NORMAL)}[{git["worktree"].upper()}]{R}')
    if git['branch']:
        br = git['branch'].upper()
        if git['detached']:
            l2.append(f'{BOLD}{fg(BRIGHT)}{br} DET{R}')
        else:
            l2.append(f'{fg(NORMAL)}{br}{R}')
        if git['remote_short']:
            l2.append(f'{fg(FAINT)}\u2192{git["remote_short"].upper()}{R}')
        ab = ''
        if git['ahead']:
            ab += f'{fg(NORMAL)}\u2191{git["ahead"]}{R}'
        if git['behind']:
            ab += f'{fg(BRIGHT)}\u2193{git["behind"]}{R}'
        if ab:
            l2.append(ab)
    if git['dirty']:
        l2.append(f'{fg(NORMAL)}+{git["dirty"]}{R}')
    if git['stash']:
        l2.append(f'{fg(DK_GRN)}\u2691{git["stash"]}{R}')

    # Path — high intensity, this is important
    path = ctx['path_display'].upper()
    if path:
        l2.append(f'{fg(BRIGHT)}{path}{R}')

    # Cursor prefix
    prefix = f'{fg(DK_GRN)}==>{R} '
    line2 = prefix + ' '.join(l2) if l2 else ''

    return f'{line1}\n{line2}' if line2 else line1
