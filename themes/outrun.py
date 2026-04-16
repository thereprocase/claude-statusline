"""Outrun theme — synthwave sunset. Hot pink, electric cyan, chrome, neon purple."""

from core import R, fg, render_standard

# ── Synthwave palette ───────────────────────────────────────────────────────
HOT_PINK    = 199   # neon magenta
ELECTRIC    = 51    # electric cyan
CHROME      = 252   # bright chrome/silver
NEON_PURPLE = 135   # deep neon purple
SUNSET_ORG  = 208   # sunset orange
SUNSET_RED  = 196   # horizon red
GRID        = 93    # the perspective grid purple
DARK_CHROME = 243   # muted chrome
VOID        = 236   # dark background reference
LASER       = 201   # laser pink

THEME = {
    'sep': f' {fg(GRID)}\u2502{R} ',
    'grad': [
        ELECTRIC, ELECTRIC, ELECTRIC, 45, 44,
        CHROME, CHROME, SUNSET_ORG, SUNSET_ORG, SUNSET_ORG,
        HOT_PINK, HOT_PINK, HOT_PINK, LASER, LASER,
        SUNSET_RED, SUNSET_RED, SUNSET_RED, SUNSET_RED, SUNSET_RED,
    ],
    'rl_grad': [
        ELECTRIC, ELECTRIC, ELECTRIC, ELECTRIC, CHROME,
        CHROME, CHROME, SUNSET_ORG, SUNSET_ORG, SUNSET_ORG,
        HOT_PINK, HOT_PINK, HOT_PINK, HOT_PINK, LASER,
        LASER, SUNSET_RED, SUNSET_RED, SUNSET_RED, SUNSET_RED,
    ],
    'tier': {'opus': HOT_PINK, 'sonnet': ELECTRIC, 'haiku': SUNSET_ORG},
    'tier_default': ELECTRIC,
    'colors': {
        'user': CHROME, 'effort': DARK_CHROME, 'duration': GRID,
        'empty_bar': GRID,
        'rl_label': GRID, 'rl_reset': NEON_PURPLE, 'rl_null': GRID,
        'operation': SUNSET_RED, 'worktree': NEON_PURPLE,
        'branch': ELECTRIC, 'detached': SUNSET_RED,
        'remote_arrow': GRID, 'remote': NEON_PURPLE,
        'ahead': ELECTRIC, 'behind': HOT_PINK,
        'dirty': SUNSET_ORG, 'stash': NEON_PURPLE, 'path': CHROME,
    },
    'branch_bold': True,
    'detached_bold': True,
    'line2_prefix': f'{fg(GRID)}\u2500\u2500{R} ',
}

def render(ctx):
    return render_standard(ctx, THEME)
