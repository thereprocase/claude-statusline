"""Buddy theme — the /buddy toast gradient. Sunset warmth from Claude's terminal pet."""

from core import R, fg, render_standard

# ── Buddy sunset palette (the 6 colors from the /buddy toast bar) ───────────
RED    = 167   # warm sunset red
ORANGE = 209   # sunset orange
GOLD   = 215   # golden hour
GREEN  = 114   # twilight green
BLUE   = 110   # dusk blue
VIOLET = 104   # evening violet

# The full sunset sequence for gradients
SUNSET = [VIOLET, BLUE, GREEN, GOLD, ORANGE, RED]
# Reversed for context (cool start, hot end)
SUNRISE = [BLUE, BLUE, GREEN, GREEN, GOLD, GOLD, ORANGE, ORANGE, RED, RED,
           RED, RED, RED, RED, RED, RED, RED, RED, RED, RED]

# Extended tints for variety
WARM_WHITE = 223  # sunset-lit cloud
DUSK       = 60   # deep twilight
HAZE       = 138  # purple haze

def _rainbow_text(text, colors=None):
    """Paint text with the sunset sequence."""
    if colors is None:
        colors = SUNSET
    out = ''
    for i, ch in enumerate(text):
        if ch == ' ':
            out += ' '
        else:
            out += f'{fg(colors[i % len(colors)])}{ch}'
    return out + R

def _buddy_user(text, theme):
    return _rainbow_text(text, [GOLD, ORANGE])

THEME = {
    'sep': f' {fg(DUSK)}\u2502{R} ',
    'grad': SUNRISE,
    'tier': {'opus': VIOLET, 'sonnet': BLUE, 'haiku': GOLD},
    'tier_default': VIOLET,
    'colors': {
        'user': GOLD, 'effort': HAZE, 'duration': DUSK,
        'empty_bar': DUSK,
        'rl_label': HAZE, 'rl_reset': DUSK, 'rl_null': DUSK,
        'operation': RED, 'worktree': VIOLET,
        'branch': GREEN, 'detached': RED,
        'remote_arrow': DUSK, 'remote': BLUE,
        'ahead': GREEN, 'behind': ORANGE,
        'dirty': GOLD, 'stash': VIOLET, 'path': WARM_WHITE,
    },
    'user_chip': _buddy_user,
    'line2_prefix': (f'{fg(VIOLET)}\u2588{fg(BLUE)}\u2588{fg(GREEN)}\u2588'
                     f'{fg(GOLD)}\u2588{fg(ORANGE)}\u2588{fg(RED)}\u2588{R} '),
}

def render(ctx):
    return render_standard(ctx, THEME)
