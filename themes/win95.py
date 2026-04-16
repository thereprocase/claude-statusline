"""Win95 theme — Windows 95 system tray. Teal title bars, silver bevels, that gray."""

from core import R, DIM, BOLD, fg, bg

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
RAISED_L = '\u2590'  # ▐
RAISED_R = '\u258C'  # ▌

SEP = f' {fg(DK_GRAY)}\u2502{R} '

def _button(text, color=TEAL):
    """Win95-style raised button."""
    return f'{fg(SILVER)}{RAISED_L}{bg(color)}{fg(WHITE)}{BOLD}{text}{R}{fg(DK_GRAY)}{RAISED_R}{R}'

def _status_color(pct):
    if pct >= 85: return WIN_RED
    if pct >= 60: return WIN_YELLOW
    if pct >= 30: return WIN_GREEN
    return TEAL

def render(ctx):
    config = ctx['config']
    used_pct = ctx['used_pct']
    parts = []

    # Start button energy
    if config.get('show_user', True) and ctx['user_short']:
        parts.append(_button(ctx['user_short'].upper(), TEAL))

    # Model in title bar style
    m = ctx['model_name']
    sz = ctx['cw_str']
    label = f'{m} {sz}' if sz else m
    parts.append(_button(label, NAVY))

    if ctx['effort']:
        parts.append(f'{fg(DK_GRAY)}{ctx["effort"]}{R}')

    # Context — progress bar style
    if used_pct is not None:
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
        parts.append(f'{bar}  {fg(pc)}{int(round(used_pct))}%{R}')

    # Rate limits — system tray percentage
    for rl in ctx['rate_limits']:
        pct = rl['pct']
        if pct is None:
            parts.append(f'{fg(DK_GRAY)}{rl["label"]} --{R}')
            continue
        sc = _status_color(pct)
        ts = rl['reset_str']
        if ts:
            parts.append(f'{fg(GRAY)}{rl["label"]} {fg(sc)}{pct}%{fg(DK_GRAY)}@{ts}{R}')
        else:
            parts.append(f'{fg(GRAY)}{rl["label"]} {fg(sc)}{pct}%{R}')

    # Clock in system tray
    parts.append(f'{fg(DK_GRAY)}{ctx["session_dur"]}{R}')

    line1 = SEP.join(parts)

    # Line 2 — address bar style
    git = ctx['git']
    l2 = []
    if git['operation']:
        l2.append(f'{BOLD}{fg(WIN_RED)}{git["operation"]}{R}')
    if git['worktree']:
        l2.append(f'{fg(GRAY)}[{git["worktree"]}]{R}')
    if git['branch']:
        br_label = git['branch']
        if git['repo_name']:
            br_label = f'{git["repo_name"]}/{br_label}'
        if git['detached']:
            l2.append(f'{fg(WIN_RED)}{br_label} det{R}')
        else:
            l2.append(f'{fg(WHITE)}{br_label}{R}')
        if git['remote_short']:
            l2.append(f'{fg(DK_GRAY)}\u2192{git["remote_short"]}{R}')
        ab = ''
        if git['ahead']:  ab += f'{fg(WIN_GREEN)}\u2191{git["ahead"]}{R}'
        if git['behind']: ab += f'{fg(WIN_RED)}\u2193{git["behind"]}{R}'
        if ab: l2.append(ab)
    if git['dirty']:
        l2.append(f'{fg(WIN_YELLOW)}+{git["dirty"]}{R}')
    if git['stash']:
        l2.append(f'{fg(GRAY)}\u2691{git["stash"]}{R}')

    path = ctx['path_display']
    if path:
        l2.append(f'{fg(SILVER)}{path}{R}')

    # Address bar prefix — derive drive letter from cwd when possible
    _cwd = ctx.get('cwd', '')
    if len(_cwd) >= 2 and _cwd[1] == ':':
        _drive = _cwd[0].upper()
    elif _cwd.startswith('/') and len(_cwd) >= 3 and _cwd[2] == '/':
        # Git Bash /c/... style
        _drive = _cwd[1].upper()
    else:
        _drive = 'C'
    prefix = f'{fg(GRAY)}{_drive}:\\>{R} '
    line2 = prefix + ' '.join(l2) if l2 else ''

    return f'{line1}\n{line2}' if line2 else line1
