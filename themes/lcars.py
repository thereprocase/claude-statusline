"""LCARS theme — Star Trek TNG-era Library Computer Access and Retrieval System."""

from core import R, DIM, BOLD, fg, bg

# ── TNG Palette (xterm-256) ─────────────────────────────────────────────────
CANARY      = 227   # pale yellow
TANOI       = 222   # warm tan/peach
GOLDEN      = 221   # golden orange
NEON_CARROT = 214   # bright orange
EGGPLANT    = 96    # dark purple
LILAC       = 182   # light purple
ANAKIWA     = 153   # light blue
MARINER     = 68    # medium blue
BAHAMA      = 24    # dark blue
BRICK       = 167   # alert red
PEACH       = 215   # mango/peach
BLACK       = 16

TIER_COLORS = {'opus': LILAC, 'sonnet': ANAKIWA, 'haiku': CANARY}

CTX_GRADIENT = [
    BAHAMA, BAHAMA, MARINER, MARINER, ANAKIWA,
    CANARY, GOLDEN, GOLDEN, NEON_CARROT, NEON_CARROT,
    NEON_CARROT, PEACH, PEACH, BRICK, BRICK,
    BRICK, BRICK, BRICK, BRICK, BRICK,
]

RL_GRADIENT = [
    ANAKIWA, ANAKIWA, ANAKIWA, ANAKIWA, CANARY,
    CANARY, CANARY, GOLDEN, GOLDEN, GOLDEN,
    NEON_CARROT, NEON_CARROT, NEON_CARROT, NEON_CARROT, PEACH,
    PEACH, BRICK, BRICK, BRICK, BRICK,
]

# ── LCARS UI primitives ─────────────────────────────────────────────────────
HBAR   = '\u2501'
LBRAK  = '\u2590'
RBRAK  = '\u258C'
BAR    = '\u2588'
HALF_L = '\u258C'

def _chip(text, color):
    return f'{fg(color)}{LBRAK}{bg(color)}{fg(BLACK)}{BOLD}{text}{R}{fg(color)}{RBRAK}{R}'

def _bar(width, color):
    return f'{fg(color)}{BAR * width}{R}'

def _sep():
    return f'{fg(EGGPLANT)}{HBAR}{R}'

def _grad_color(pct, grad):
    return grad[min(int(pct / 100 * (len(grad) - 1)), len(grad) - 1)]

# ── Render ──────────────────────────────────────────────────────────────────
def render(ctx):
    config = ctx['config']
    used_pct = ctx['used_pct']
    tier_color = TIER_COLORS.get(ctx['model_family'], ANAKIWA)
    sep = _sep()

    parts = []

    # User chip
    if config.get('show_user', True) and ctx['user_short']:
        parts.append(_chip(ctx['user_short'].upper(), TANOI))

    # Model chip
    m = ctx['model_name'].upper()
    sz = ctx['cw_str']
    label = f'{m} {sz}' if sz else m
    parts.append(_chip(label, tier_color))

    # Effort
    if ctx['effort']:
        parts.append(f'{fg(GOLDEN)}{ctx["effort"].upper()}{R}')

    # ── Context bar (BEFORE rate limits) ────────────────────────────────────
    if used_pct is not None:
        N = 12
        fill = used_pct / 100 * N
        bar_str = f'{fg(EGGPLANT)}{LBRAK}{R}'
        for i in range(N):
            c = CTX_GRADIENT[min(i * 2, len(CTX_GRADIENT) - 1)]
            cell = fill - i
            if cell >= 1.0:
                bar_str += f'{fg(c)}{BAR}'
            elif cell >= 0.5:
                bar_str += f'{fg(c)}{HALF_L}'
            else:
                bar_str += f'{fg(EGGPLANT)}{HBAR}'
        bar_str += f'{fg(EGGPLANT)}{RBRAK}{R}'
        pct_color = _grad_color(used_pct, CTX_GRADIENT)
        bar_str += f' {fg(pct_color)}{int(round(used_pct))}%{R}'
        parts.append(bar_str)

    # ── Rate limits ─────────────────────────────────────────────────────────
    for rl in ctx['rate_limits']:
        label = rl['label'].upper()
        pct = rl['pct']
        if pct is None:
            continue
        rc = _grad_color(pct, RL_GRADIENT)
        ts = rl['reset_str'].upper() if rl['reset_str'] else ''
        rl_str = f'{fg(EGGPLANT)}{label} {fg(rc)}{pct}%{R}'
        if ts:
            rl_str += f'{fg(EGGPLANT)}@{fg(TANOI)}{ts}{R}'
        parts.append(rl_str)

    # Session duration
    parts.append(f'{fg(EGGPLANT)}{ctx["session_dur"].upper()}{R}')

    line1 = sep.join(parts)

    # ── Line 2: LCARS nav strip ─────────────────────────────────────────────
    git = ctx['git']
    nav_parts = []

    if git['operation']:
        nav_parts.append(_chip(git['operation'], BRICK))
    if git['worktree']:
        nav_parts.append(_chip(git['worktree'].upper(), LILAC))
    if git['branch']:
        br = git['branch'].upper()
        if git['detached']:
            nav_parts.append(_chip(f'{br} DET', BRICK))
        else:
            nav_parts.append(_chip(br, ANAKIWA))
        if git['remote_short']:
            nav_parts.append(f'{fg(TANOI)}{git["remote_short"].upper()}{R}')
        ab = ''
        if git['ahead']:
            ab += f'{fg(GOLDEN)}\u25B2{git["ahead"]}{R}'
        if git['behind']:
            ab += f'{fg(BRICK)}\u25BC{git["behind"]}{R}'
        if ab:
            nav_parts.append(ab)
    if git['dirty']:
        nav_parts.append(_chip(f'\u0394{git["dirty"]}', NEON_CARROT))
    if git['stash']:
        nav_parts.append(f'{fg(LILAC)}\u2691{git["stash"]}{R}')

    path = ctx['path_display'].upper() if ctx['path_display'] else ''
    elbow = _bar(2, EGGPLANT)

    if nav_parts or path:
        if nav_parts:
            line2 = f'{elbow}{sep}{sep.join(nav_parts)}{sep}{fg(TANOI)}{path}{R}'
        else:
            line2 = f'{elbow}{sep}{fg(TANOI)}{path}{R}'
        return f'{line1}\n{line2}'

    return line1
