"""Catppuccin theme — Mocha variant. Warm pastels on dark. Cozy."""

from core import R, fg, render_standard

# ── Catppuccin Mocha palette (official hex -> xterm-256) ────────────────────
ROSEWATER  = 224   # #f5e0dc
FLAMINGO   = 217   # #f2cdcd
PINK       = 211   # #f5c2e7
MAUVE      = 141   # #cba6f7
RED        = 203   # #f38ba8
MAROON     = 174   # #eba0ac
PEACH      = 209   # #fab387
YELLOW     = 222   # #f9e2af
GREEN      = 115   # #a6e3a1
TEAL       = 116   # #94e2d5
SKY        = 117   # #89dceb
SAPPHIRE   = 74    # #74c7ec
BLUE       = 111   # #89b4fa
LAVENDER   = 147   # #b4befe
TEXT       = 254   # #cdd6f4
SUBTEXT1   = 249   # #bac2de
SUBTEXT0   = 245   # #a6adc8
OVERLAY2   = 243   # #9399b2
OVERLAY1   = 240   # #7f849c
OVERLAY0   = 238   # #6c7086
SURFACE2   = 236   # #585b70
SURFACE1   = 235   # #45475a
SURFACE0   = 234   # #313244
BASE       = 233   # #1e1e2e
MANTLE     = 232   # #181825
CRUST      = 16    # #11111b

THEME = {
    'sep': f' {fg(OVERLAY0)}\u2502{R} ',
    'grad': [
        BLUE, BLUE, SAPPHIRE, SAPPHIRE, TEAL,
        GREEN, GREEN, YELLOW, YELLOW, YELLOW,
        PEACH, PEACH, PEACH, MAROON, MAROON,
        RED, RED, RED, RED, RED,
    ],
    'tier': {'opus': MAUVE, 'sonnet': BLUE, 'haiku': GREEN},
    'tier_default': MAUVE,
    'colors': {
        'user': FLAMINGO, 'effort': OVERLAY1, 'duration': SURFACE2,
        'empty_bar': SURFACE2,
        'rl_label': OVERLAY0, 'rl_reset': OVERLAY0, 'rl_null': SURFACE2,
        'operation': RED, 'worktree': MAUVE,
        'branch': GREEN, 'detached': RED,
        'remote_arrow': OVERLAY0, 'remote': LAVENDER,
        'ahead': TEAL, 'behind': MAROON,
        'dirty': PEACH, 'stash': MAUVE, 'path': TEXT,
    },
}

def render(ctx):
    return render_standard(ctx, THEME)
