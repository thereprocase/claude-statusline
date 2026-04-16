"""Teletext theme — Ceefax/Oracle. Blocky colored headers on black. Page 100."""

from core import R, BOLD, fg, bg, render_standard

# ── Teletext palette (the 8 teletext colors mapped to xterm-256) ────────────
# Teletext/Videotex used a strict 8-color palette
TT_RED     = 196
TT_GREEN   = 46
TT_YELLOW  = 226
TT_BLUE    = 21
TT_MAGENTA = 201
TT_CYAN    = 51
TT_WHITE   = 15
TT_BLACK   = 16

# Page header is always white on color block
HEADER_BG  = TT_BLUE
FLASH      = '\033[5m'

def _tt_block(text, color):
    """Teletext double-height style header block."""
    return f'{bg(color)}{fg(TT_WHITE)}{BOLD} {text} {R}'

def _tt_color(pct):
    if pct >= 85: return TT_RED
    if pct >= 60: return TT_YELLOW
    if pct >= 30: return TT_GREEN
    return TT_CYAN

def _tt_user(text, theme):
    return f'{fg(TT_WHITE)}{text.upper()}{R}'

def _tt_model(label, tier_color, theme):
    return _tt_block(label.upper(), HEADER_BG)

def _tt_op(op, theme):
    return _tt_block(op, TT_RED)

def _tt_bar(used_pct, theme):
    """Teletext 2-level bar with flash effect at high usage."""
    N = 10
    fill = used_pct / 100 * N
    bar = ''
    for i in range(N):
        cell = fill - i
        c = _tt_color(i * 10)
        if cell >= 1.0:   bar += f'{fg(c)}\u2588'
        elif cell >= 0.5: bar += f'{fg(c)}\u2584'
        else:             bar += f'{fg(TT_BLUE)}\u2500'
    bar += R
    pc = _tt_color(used_pct)
    pct_str = f'{int(round(used_pct))}%'
    if used_pct >= 90:
        pct_str = f'{FLASH}{fg(TT_RED)}{pct_str}{R}'
    else:
        pct_str = f'{fg(pc)}{pct_str}{R}'
    return f'{bar}  {pct_str}'

def _tt_rl(rl, theme):
    """Teletext rate limit with threshold-based color."""
    pct = rl['pct']
    if pct is None:
        return f'{fg(TT_BLUE)}{rl["label"]} --{R}'
    rc = _tt_color(pct)
    ts = rl['reset_str']
    if ts:
        return f'{fg(TT_CYAN)}{rl["label"]} {fg(rc)}{pct}%{fg(TT_BLUE)}@{ts}{R}'
    return f'{fg(TT_CYAN)}{rl["label"]} {fg(rc)}{pct}%{R}'

THEME = {
    'sep': f' {fg(TT_CYAN)}\u2502{R} ',
    'grad': [],  # unused — teletext uses threshold-based colors
    'tier': {'opus': TT_BLUE, 'sonnet': TT_BLUE, 'haiku': TT_BLUE},
    'tier_default': TT_BLUE,
    'user_chip': _tt_user,
    'model_chip': _tt_model,
    'bar_fn': _tt_bar,
    'rl_fn': _tt_rl,
    'op_chip': _tt_op,
    'det_suffix': ' DET',
    'ahead_char': '\u25B2',
    'behind_char': '\u25BC',
    'colors': {
        'user': TT_WHITE, 'effort': TT_YELLOW, 'duration': TT_BLUE,
        'empty_bar': TT_BLUE,
        'rl_label': TT_CYAN, 'rl_reset': TT_BLUE, 'rl_null': TT_BLUE,
        'operation': TT_RED, 'worktree': TT_MAGENTA,
        'branch': TT_GREEN, 'detached': TT_RED,
        'remote_arrow': TT_BLUE, 'remote': TT_CYAN,
        'ahead': TT_GREEN, 'behind': TT_RED,
        'dirty': TT_YELLOW, 'stash': TT_MAGENTA, 'path': TT_WHITE,
    },
    'line2_prefix': f'{fg(TT_YELLOW)}p100{R} ',
}

def render(ctx):
    return render_standard(ctx, THEME)
