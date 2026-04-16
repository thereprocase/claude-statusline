"""C64 theme — Commodore 64. Light blue on dark blue. READY."""

from core import R, BOLD, fg, render_standard

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

def _c64_color(pct):
    if pct >= 90: return RED
    if pct >= 70: return ORANGE
    if pct >= 50: return YELLOW
    if pct >= 30: return GREEN
    return LIGHT_BLUE

def _c64_user(text, theme):
    return f'{BOLD}{fg(WHITE)}{text.upper()}{R}'

def _c64_model(label, tier_color, theme):
    return f'{BOLD}{fg(tier_color)}{label.upper()}{R}'

def _c64_bar(used_pct, theme):
    """C64 3-level block character bar with position-based color."""
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
    return f'{bar}  {fg(pc)}{int(round(used_pct))}%{R}'

def _c64_rl(rl, theme):
    """C64 rate limit with threshold-based color."""
    pct = rl['pct']
    if pct is None:
        return f'{fg(DK_GREY)}{rl["label"]} --{R}'
    rc = _c64_color(pct)
    ts = rl['reset_str']
    if ts:
        return f'{fg(LIGHT_BLUE)}{rl["label"]} {fg(rc)}{pct}%{fg(DK_GREY)}@{ts}{R}'
    return f'{fg(LIGHT_BLUE)}{rl["label"]} {fg(rc)}{pct}%{R}'

THEME = {
    'sep': f' {fg(DARK_BLUE)}\u2502{R} ',
    'grad': [],  # unused — c64 uses threshold-based colors
    'tier': {'opus': CYAN, 'sonnet': CYAN, 'haiku': CYAN},
    'tier_default': CYAN,
    'user_chip': _c64_user,
    'model_chip': _c64_model,
    'bar_fn': _c64_bar,
    'rl_fn': _c64_rl,
    'det_suffix': ' DET',
    'colors': {
        'user': WHITE, 'effort': DK_GREY, 'duration': DK_GREY,
        'empty_bar': DARK_BLUE,
        'rl_label': LIGHT_BLUE, 'rl_reset': DK_GREY, 'rl_null': DK_GREY,
        'operation': RED, 'worktree': GREEN,
        'branch': LIGHT_GRN, 'detached': RED,
        'remote_arrow': DK_GREY, 'remote': DK_GREY,
        'ahead': GREEN, 'behind': RED,
        'dirty': YELLOW, 'stash': GREY, 'path': LIGHT_BLUE,
    },
    'line2_prefix': f'{fg(LIGHT_BLUE)}READY.{R} ',
}

def render(ctx):
    return render_standard(ctx, THEME)
