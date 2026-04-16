"""Matrix theme — digital rain. Green code falling on black. There is no spoon."""

import random
from datetime import datetime
from core import R, BOLD, fg, render_standard

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

def _rain_char():
    return random.choice(RAIN_CHARS)

def _intensity(pct):
    if pct >= 80: return BRIGHT
    if pct >= 50: return NORMAL
    if pct >= 20: return DIM_GRN
    return FAINT

def _matrix_user(text, theme):
    return f'{fg(BRIGHT)}{text}{R}'

def _matrix_bar(used_pct, theme):
    """Digital rain bar — rain characters at varying phosphor intensity."""
    N = 10
    fill = used_pct / 100 * N
    bar = ''
    for i in range(N):
        cell = fill - i
        if cell >= 1.0:
            if i >= 8:
                bar += f'{BOLD}{fg(WHITE)}{_rain_char()}{R}'
            elif i >= 5:
                bar += f'{fg(BRIGHT)}{_rain_char()}'
            else:
                bar += f'{fg(NORMAL)}{_rain_char()}'
        elif cell >= 0.5:
            bar += f'{fg(DIM_GRN)}{_rain_char()}'
        elif cell >= 0.25:
            bar += f'{fg(FAINT)}{_rain_char()}'
        else:
            bar += f'{fg(GHOST)}\u2500'
    bar += R
    pc = _intensity(used_pct)
    return f'{bar}  {fg(pc)}{int(round(used_pct))}%{R}'

def _matrix_rl(rl, theme):
    """Matrix rate limit with phosphor intensity color."""
    pct = rl['pct']
    if pct is None:
        return ''
    ic = _intensity(pct)
    ts = rl['reset_str']
    if ts:
        return f'{fg(DIM_GRN)}{rl["label"]} {fg(ic)}{pct}%{fg(FAINT)}@{ts}{R}'
    return f'{fg(DIM_GRN)}{rl["label"]} {fg(ic)}{pct}%{R}'

THEME = {
    'sep': f' {fg(FAINT)}\u2502{R} ',
    'grad': [],  # unused — matrix uses intensity-based colors
    'tier': {'opus': BRIGHT, 'sonnet': BRIGHT, 'haiku': BRIGHT},
    'tier_default': BRIGHT,
    'user_chip': _matrix_user,
    'bar_fn': _matrix_bar,
    'rl_fn': _matrix_rl,
    'detached_bold': True,
    'colors': {
        'user': BRIGHT, 'effort': DIM_GRN, 'duration': FAINT,
        'empty_bar': GHOST,
        'rl_label': DIM_GRN, 'rl_reset': FAINT, 'rl_null': GHOST,
        'operation': WHITE, 'worktree': DIM_GRN,
        'branch': NORMAL, 'detached': WHITE,
        'remote_arrow': FAINT, 'remote': FAINT,
        'ahead': BRIGHT, 'behind': BRIGHT,
        'dirty': NORMAL, 'stash': DIM_GRN, 'path': BRIGHT,
    },
    'line2_prefix': f'{fg(DIM_GRN)}>{R} ',
}

def render(ctx):
    random.seed(int(datetime.now().timestamp() * 1000) % 100000)
    return render_standard(ctx, THEME)
