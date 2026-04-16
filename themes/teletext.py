"""Teletext theme — Ceefax/Oracle. Blocky colored headers on black. Page 100."""

from core import R, DIM, BOLD, fg, bg

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

SEP = f' {fg(TT_CYAN)}\u2502{R} '

def _tt_block(text, color):
    """Teletext double-height style header block."""
    return f'{bg(color)}{fg(TT_WHITE)}{BOLD} {text} {R}'

def _tt_color(pct):
    if pct >= 85: return TT_RED
    if pct >= 60: return TT_YELLOW
    if pct >= 30: return TT_GREEN
    return TT_CYAN

def render(ctx):
    config = ctx['config']
    used_pct = ctx['used_pct']
    parts = []

    # Page number style user
    if config.get('show_user', True) and ctx['user_short']:
        parts.append(f'{fg(TT_WHITE)}{ctx["user_short"].upper()}{R}')

    # Model as header block
    m = ctx['model_name'].upper()
    sz = ctx['cw_str']
    label = f'{m} {sz}' if sz else m
    parts.append(_tt_block(label, HEADER_BG))

    if ctx['effort']:
        parts.append(f'{fg(TT_YELLOW)}{ctx["effort"]}{R}')

    # Context bar — teletext graphics characters
    if used_pct is not None:
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
        parts.append(f'{bar}  {pct_str}')

    for rl in ctx['rate_limits']:
        pct = rl['pct']
        if pct is None:
            parts.append(f'{fg(TT_BLUE)}{rl["label"]} --{R}')
            continue
        rc = _tt_color(pct)
        ts = rl['reset_str']
        if ts:
            parts.append(f'{fg(TT_CYAN)}{rl["label"]} {fg(rc)}{pct}%{fg(TT_BLUE)}@{ts}{R}')
        else:
            parts.append(f'{fg(TT_CYAN)}{rl["label"]} {fg(rc)}{pct}%{R}')

    parts.append(f'{fg(TT_BLUE)}{ctx["session_dur"]}{R}')

    line1 = SEP.join(parts)

    # Line 2 — subpage navigation feel
    git = ctx['git']
    l2 = []
    if git['operation']:
        l2.append(_tt_block(git['operation'], TT_RED))
    if git['worktree']:
        l2.append(f'{fg(TT_MAGENTA)}[{git["worktree"]}]{R}')
    if git['branch']:
        if git['detached']:
            l2.append(f'{fg(TT_RED)}{git["branch"]} DET{R}')
        else:
            l2.append(f'{fg(TT_GREEN)}{git["branch"]}{R}')
        if git['remote_short']:
            l2.append(f'{fg(TT_BLUE)}\u2192{fg(TT_CYAN)}{git["remote_short"]}{R}')
        ab = ''
        if git['ahead']:  ab += f'{fg(TT_GREEN)}\u25B2{git["ahead"]}{R}'
        if git['behind']: ab += f'{fg(TT_RED)}\u25BC{git["behind"]}{R}'
        if ab: l2.append(ab)
    if git['dirty']:
        l2.append(f'{fg(TT_YELLOW)}+{git["dirty"]}{R}')
    if git['stash']:
        l2.append(f'{fg(TT_MAGENTA)}\u2691{git["stash"]}{R}')

    path = ctx['path_display']
    if path:
        l2.append(f'{fg(TT_WHITE)}{path}{R}')

    prefix = f'{fg(TT_YELLOW)}p100{R} '
    line2 = prefix + ' '.join(l2) if l2 else ''

    return f'{line1}\n{line2}' if line2 else line1
