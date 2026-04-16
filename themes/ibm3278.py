"""IBM 3278 theme — green phosphor CRT terminal. The mainframe is watching."""

from core import R, fg, render_standard, _phosphor_bar, _phosphor_rl

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
        'user': BRIGHT, 'effort': DK_GRN, 'duration': FAINT,
        'empty_bar': SHADOW,
        'bar_bright': BRIGHT, 'bar_normal': NORMAL, 'bar_dim': DK_GRN, 'bar_faint': FAINT,
        'rl_label': DK_GRN, 'rl_reset': FAINT, 'rl_null': FAINT,
        'operation': BRIGHT, 'worktree': NORMAL,
        'branch': NORMAL, 'detached': BRIGHT,
        'remote_arrow': FAINT, 'remote': FAINT,
        'ahead': NORMAL, 'behind': BRIGHT,
        'dirty': NORMAL, 'stash': DK_GRN, 'path': BRIGHT,
    },
    'line2_prefix': f'{fg(DK_GRN)}==>{R} ',
}

def render(ctx):
    return render_standard(ctx, THEME)
