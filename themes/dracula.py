"""Dracula theme — the beloved dark palette. Purple, pink, cyan, green on dark."""

from core import R, fg, render_standard

# ── Dracula palette (official hex -> xterm-256) ─────────────────────────────
BG         = 236   # #282a36 background
FG_COLOR   = 253   # #f8f8f2 foreground
COMMENT    = 103   # #6272a4 comment
CYAN_D     = 81    # #8be9fd cyan
GREEN_D    = 84    # #50fa7b green
ORANGE_D   = 215   # #ffb86c orange
PINK       = 212   # #ff79c6 pink
PURPLE     = 141   # #bd93f9 purple
RED_D      = 203   # #ff5555 red
YELLOW_D   = 228   # #f1fa8c yellow

THEME = {
    'sep': f' {fg(COMMENT)}\u2502{R} ',
    'grad': [
        CYAN_D, CYAN_D, CYAN_D, CYAN_D, GREEN_D,
        GREEN_D, GREEN_D, YELLOW_D, YELLOW_D, YELLOW_D,
        ORANGE_D, ORANGE_D, ORANGE_D, PINK, PINK,
        RED_D, RED_D, RED_D, RED_D, RED_D,
    ],
    'tier': {'opus': PURPLE, 'sonnet': CYAN_D, 'haiku': GREEN_D},
    'tier_default': PURPLE,
    'colors': {
        'user': PINK, 'effort': COMMENT, 'duration': COMMENT,
        'empty_bar': COMMENT,
        'rl_label': COMMENT, 'rl_reset': COMMENT, 'rl_null': COMMENT,
        'operation': RED_D, 'worktree': PURPLE,
        'branch': GREEN_D, 'detached': RED_D,
        'remote_arrow': COMMENT, 'remote': PURPLE,
        'ahead': GREEN_D, 'behind': RED_D,
        'dirty': ORANGE_D, 'stash': PURPLE, 'path': FG_COLOR,
    },
}

def render(ctx):
    return render_standard(ctx, THEME)
