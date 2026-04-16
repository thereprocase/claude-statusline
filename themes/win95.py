"""Win95 theme — Windows 95 system tray. Teal title bars, silver bevels, that gray."""

from core import R, BOLD, fg, bg, render_standard

# ── Windows 95 system palette ───────────────────────────────────────────────
TEAL       = 30    # title bar teal
SILVER     = 250   # 3D bevel highlight
GRAY       = 247   # window background gray
DK_GRAY    = 240   # shadow / inactive
NAVY       = 18    # desktop / selected text bg
WHITE      = 15
BLACK      = 16
WIN_RED    = 160   # error / close button
WIN_GREEN  = 28    # OK / success
WIN_YELLOW = 178   # warning

# The 3D bevel effect characters
RAISED_L = '\u2590'  # right half block
RAISED_R = '\u258C'  # left half block

def _button(text, color=TEAL):
    """Win95-style raised button."""
    return f'{fg(SILVER)}{RAISED_L}{bg(color)}{fg(WHITE)}{BOLD}{text}{R}{fg(DK_GRAY)}{RAISED_R}{R}'

def _status_color(pct):
    if pct >= 85: return WIN_RED
    if pct >= 60: return WIN_YELLOW
    if pct >= 30: return WIN_GREEN
    return TEAL

def _win95_user(text, theme):
    return _button(text.upper(), TEAL)

def _win95_model(label, tier_color, theme):
    return _button(label, NAVY)

def _win95_bar(used_pct, theme):
    """Win95 progress bar: bracket-enclosed, 2-level fill."""
    N = 10
    fill = used_pct / 100 * N
    bar = f'{fg(DK_GRAY)}[{R}'
    for i in range(N):
        cell = fill - i
        if cell >= 0.5:
            bar += f'{fg(TEAL)}\u2588'
        else:
            bar += f'{fg(GRAY)}\u2591'
    bar += f'{fg(DK_GRAY)}]{R}'
    pc = _status_color(used_pct)
    return f'{bar}  {fg(pc)}{int(round(used_pct))}%{R}'

def _win95_rl(rl, theme):
    """Win95 rate limit with threshold-based status color."""
    pct = rl['pct']
    if pct is None:
        return f'{fg(DK_GRAY)}{rl["label"]} --{R}'
    sc = _status_color(pct)
    ts = rl['reset_str']
    if ts:
        return f'{fg(GRAY)}{rl["label"]} {fg(sc)}{pct}%{fg(DK_GRAY)}@{ts}{R}'
    return f'{fg(GRAY)}{rl["label"]} {fg(sc)}{pct}%{R}'

THEME = {
    'sep': f' {fg(DK_GRAY)}\u2502{R} ',
    'grad': [],  # unused — win95 uses threshold-based colors
    'tier': {'opus': NAVY, 'sonnet': NAVY, 'haiku': NAVY},
    'tier_default': NAVY,
    'user_chip': _win95_user,
    'model_chip': _win95_model,
    'bar_fn': _win95_bar,
    'rl_fn': _win95_rl,
    'colors': {
        'user': WHITE, 'effort': DK_GRAY, 'duration': DK_GRAY,
        'empty_bar': GRAY,
        'rl_label': GRAY, 'rl_reset': DK_GRAY, 'rl_null': DK_GRAY,
        'operation': WIN_RED, 'worktree': GRAY,
        'branch': WHITE, 'detached': WIN_RED,
        'remote_arrow': DK_GRAY, 'remote': DK_GRAY,
        'ahead': WIN_GREEN, 'behind': WIN_RED,
        'dirty': WIN_YELLOW, 'stash': GRAY, 'path': SILVER,
    },
    'line2_prefix': f'{fg(GRAY)}C:\\>{R} ',
}

def _win95_prefix(ctx):
    """Derive drive letter from cwd for the Win95 address bar prompt."""
    cwd = ctx.get('cwd', '')
    if len(cwd) >= 2 and cwd[1] == ':':
        drive = cwd[0].upper()
    elif cwd.startswith('/') and len(cwd) >= 3 and cwd[2] == '/':
        drive = cwd[1].upper()  # Git Bash /c/... style
    else:
        drive = 'C'
    return f'{fg(GRAY)}{drive}:\\>{R} '

def render(ctx):
    THEME['line2_prefix'] = _win95_prefix(ctx)
    return render_standard(ctx, THEME)
