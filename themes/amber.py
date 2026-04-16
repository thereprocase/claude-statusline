"""Amber theme — warm phosphor CRT. HP 2622, Wyse 50, early PCs. That golden glow."""

from core import R, fg, render_standard, _phosphor_bar, _phosphor_rl

# ── P3 Amber Phosphor palette ──────────────────────────────────────────────
BRIGHT  = 220   # full intensity amber
NORMAL  = 178   # standard intensity
DK_AMB  = 136   # dim amber
FAINT   = 94    # barely visible
SHADOW  = 236   # CRT off

THEME = {
    'sep': f' {fg(FAINT)}\u2502{R} ',
    'grad': [],  # unused — phosphor bar uses intensity colors directly
    'tier': {'opus': BRIGHT, 'sonnet': BRIGHT, 'haiku': BRIGHT},
    'tier_default': BRIGHT,
    'text_xform': str.upper,
    'bar_fn': _phosphor_bar,
    'rl_fn': _phosphor_rl,
    'detached_bold': True,
    'colors': {
        'user': BRIGHT, 'effort': DK_AMB, 'duration': FAINT,
        'empty_bar': SHADOW,
        'bar_bright': BRIGHT, 'bar_normal': NORMAL, 'bar_dim': DK_AMB, 'bar_faint': FAINT,
        'rl_label': DK_AMB, 'rl_reset': FAINT, 'rl_null': FAINT,
        'operation': BRIGHT, 'worktree': NORMAL,
        'branch': NORMAL, 'detached': BRIGHT,
        'remote_arrow': FAINT, 'remote': FAINT,
        'ahead': NORMAL, 'behind': BRIGHT,
        'dirty': NORMAL, 'stash': DK_AMB, 'path': BRIGHT,
    },
    'line2_prefix': f'{fg(DK_AMB)}>{R} ',
}

def render(ctx):
    return render_standard(ctx, THEME)
