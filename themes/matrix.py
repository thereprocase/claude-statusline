"""Matrix theme — digital rain. Green code falling on black. There is no spoon."""

import random
from datetime import datetime
from core import R, DIM, BOLD, fg

# ── Matrix palette ──────────────────────────────────────────────────────────
# The Matrix uses a specific green — not pure green, but phosphor-tinted
BRIGHT  = 46    # full intensity matrix green
NORMAL  = 34    # standard green
DIM_GRN = 28    # dim trails
FAINT   = 22    # almost gone
GHOST   = 236   # dead pixels
WHITE   = 15    # the flash of a new drop

# Half-width katakana and symbols for the rain effect
RAIN_CHARS = list('\uff66\uff67\uff68\uff69\uff6a\uff71\uff72\uff73\uff74\uff75'
                  '\uff76\uff77\uff78\uff79\uff7a\uff7b\uff7c\uff7d\uff7e\uff7f'
                  '01234567890:.<>{}|\\/')

SEP = f' {fg(FAINT)}\u2502{R} '

def _rain_char():
    return random.choice(RAIN_CHARS)

def _intensity(pct):
    if pct >= 80: return BRIGHT
    if pct >= 50: return NORMAL
    if pct >= 20: return DIM_GRN
    return FAINT

def render(ctx):
    random.seed(int(datetime.now().timestamp() * 1000) % 100000)
    config = ctx['config']
    used_pct = ctx['used_pct']
    parts = []

    if config.get('show_user', True) and ctx['user_short']:
        parts.append(f'{fg(BRIGHT)}{ctx["user_short"]}{R}')

    m = ctx['model_name']
    sz = ctx['cw_str']
    label = f'{m} {sz}' if sz else m
    parts.append(f'{BOLD}{fg(BRIGHT)}{label}{R}')

    if ctx['effort']:
        parts.append(f'{fg(DIM_GRN)}{ctx["effort"]}{R}')

    # Context bar — digital rain fills it
    if used_pct is not None:
        N = 10
        fill = used_pct / 100 * N
        bar = ''
        for i in range(N):
            cell = fill - i
            if cell >= 1.0:
                # Filled cells show rain characters at varying intensity
                if i >= 8:
                    # Leading edge — bright flash
                    bar += f'{BOLD}{fg(WHITE)}{_rain_char()}{R}'
                elif i >= 5:
                    bar += f'{fg(BRIGHT)}{_rain_char()}'
                else:
                    bar += f'{fg(NORMAL)}{_rain_char()}'
            elif cell >= 0.5:
                # Transition — dim rain
                bar += f'{fg(DIM_GRN)}{_rain_char()}'
            elif cell >= 0.25:
                bar += f'{fg(FAINT)}{_rain_char()}'
            else:
                bar += f'{fg(GHOST)}\u2500'
        bar += R
        pc = _intensity(used_pct)
        parts.append(f'{bar}  {fg(pc)}{int(round(used_pct))}%{R}')

    for rl in ctx['rate_limits']:
        pct = rl['pct']
        if pct is None:
            parts.append(f'{fg(GHOST)}{rl["label"]} --{R}')
            continue
        ic = _intensity(pct)
        ts = rl['reset_str']
        if ts:
            parts.append(f'{fg(DIM_GRN)}{rl["label"]} {fg(ic)}{pct}%{fg(FAINT)}@{ts}{R}')
        else:
            parts.append(f'{fg(DIM_GRN)}{rl["label"]} {fg(ic)}{pct}%{R}')

    parts.append(f'{fg(FAINT)}{ctx["session_dur"]}{R}')

    line1 = SEP.join(parts)

    # Line 2
    git = ctx['git']
    l2 = []
    if git['operation']:
        l2.append(f'{BOLD}{fg(WHITE)}{git["operation"]}{R}')
    if git['worktree']:
        l2.append(f'{fg(DIM_GRN)}[{git["worktree"]}]{R}')
    if git['branch']:
        if git['detached']:
            l2.append(f'{BOLD}{fg(WHITE)}{git["branch"]} det{R}')
        else:
            l2.append(f'{fg(NORMAL)}{git["branch"]}{R}')
        if git['remote_short']:
            l2.append(f'{fg(FAINT)}\u2192{git["remote_short"]}{R}')
        ab = ''
        if git['ahead']:  ab += f'{fg(BRIGHT)}\u2191{git["ahead"]}{R}'
        if git['behind']: ab += f'{fg(BRIGHT)}\u2193{git["behind"]}{R}'
        if ab: l2.append(ab)
    if git['dirty']:
        l2.append(f'{fg(NORMAL)}+{git["dirty"]}{R}')
    if git['stash']:
        l2.append(f'{fg(DIM_GRN)}\u2691{git["stash"]}{R}')

    path = ctx['path_display']
    if path:
        l2.append(f'{fg(BRIGHT)}{path}{R}')

    # Wake up, Neo...
    prefix = f'{fg(DIM_GRN)}>{R} '
    line2 = prefix + ' '.join(l2) if l2 else ''

    return f'{line1}\n{line2}' if line2 else line1
