"""Amber theme — warm phosphor CRT. HP 2622, Wyse 50, early PCs. That golden glow."""

from core import R, DIM, BOLD, fg

# ── P3 Amber Phosphor palette ──────────────────────────────────────────────
BRIGHT  = 220   # full intensity amber
NORMAL  = 178   # standard intensity
DK_AMB  = 136   # dim amber
FAINT   = 94    # barely visible
SHADOW  = 236   # CRT off

SEP = f' {fg(FAINT)}\u2502{R} '

def _intensity(pct):
    if pct >= 80: return BRIGHT
    if pct >= 50: return NORMAL
    if pct >= 20: return DK_AMB
    return FAINT

def render(ctx):
    config = ctx['config']
    used_pct = ctx['used_pct']
    parts = []

    if config.get('show_user', True) and ctx['user_short']:
        parts.append(f'{BOLD}{fg(BRIGHT)}{ctx["user_short"].upper()}{R}')

    m = ctx['model_name'].upper()
    sz = ctx['cw_str']
    label = f'{m} {sz}' if sz else m
    parts.append(f'{BOLD}{fg(BRIGHT)}{label}{R}')

    if ctx['effort']:
        parts.append(f'{fg(DK_AMB)}{ctx["effort"]}{R}')

    if used_pct is not None:
        N = 10
        fill = used_pct / 100 * N
        bar = ''
        for i in range(N):
            cell = fill - i
            if cell >= 1.0:
                if i >= 8:    bar += f'{fg(BRIGHT)}\u2588'
                elif i >= 5:  bar += f'{fg(NORMAL)}\u2588'
                else:         bar += f'{fg(DK_AMB)}\u2588'
            elif cell >= 0.5: bar += f'{fg(DK_AMB)}\u2593'
            elif cell >= 0.25:bar += f'{fg(FAINT)}\u2591'
            else:             bar += f'{fg(SHADOW)}\u2500'
        bar += R
        pc = _intensity(used_pct)
        parts.append(f'{bar}  {fg(pc)}{int(round(used_pct))}%{R}')

    for rl in ctx['rate_limits']:
        pct = rl['pct']
        if pct is None:
            parts.append(f'{fg(FAINT)}{rl["label"].upper()} --{R}')
            continue
        ic = _intensity(pct)
        ts = rl['reset_str'].upper() if rl['reset_str'] else ''
        if ts:
            parts.append(f'{fg(DK_AMB)}{rl["label"].upper()} {fg(ic)}{pct}%{fg(FAINT)}@{ts}{R}')
        else:
            parts.append(f'{fg(DK_AMB)}{rl["label"].upper()} {fg(ic)}{pct}%{R}')

    parts.append(f'{fg(FAINT)}{ctx["session_dur"].upper()}{R}')

    line1 = SEP.join(parts)

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
        if git['ahead']:  ab += f'{fg(NORMAL)}\u2191{git["ahead"]}{R}'
        if git['behind']: ab += f'{fg(BRIGHT)}\u2193{git["behind"]}{R}'
        if ab: l2.append(ab)
    if git['dirty']:
        l2.append(f'{fg(NORMAL)}+{git["dirty"]}{R}')
    if git['stash']:
        l2.append(f'{fg(DK_AMB)}\u2691{git["stash"]}{R}')

    path = ctx['path_display'].upper()
    if path:
        l2.append(f'{fg(BRIGHT)}{path}{R}')

    prefix = f'{fg(DK_AMB)}>{R} '
    line2 = prefix + ' '.join(l2) if l2 else ''

    return f'{line1}\n{line2}' if line2 else line1
