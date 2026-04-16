"""Skittles theme — taste the rainbow. Every segment a different candy color."""

import random
from datetime import datetime
from core import R, DIM, BOLD, fg

# ── Skittles bag ────────────────────────────────────────────────────────────
RED    = 196   # strawberry
ORANGE = 208   # orange
YELLOW = 226   # lemon
GREEN  = 46    # green apple
PURPLE = 129   # grape

CANDY = [RED, ORANGE, YELLOW, GREEN, PURPLE]

# Extended candy bowl for variety
WILD   = [199, 213, 87, 51, 171, 220, 118, 39, 201, 226]

# Context bar: full Skittles rainbow gradient
BAR_COLORS = [GREEN, GREEN, 118, YELLOW, YELLOW, 220, ORANGE, ORANGE, 202, RED,
              RED, 197, 197, 199, 199, 199, 199, 199, 199, 199]

SEP_CHARS = ['\u2022', '\u25CF', '\u25C6', '\u2605', '\u2736']

def _candy_sep():
    c = random.choice(CANDY)
    s = random.choice(SEP_CHARS)
    return f' {fg(c)}{s}{R} '

def _rainbow_text(text):
    """Each character a different candy color."""
    out = ''
    for i, ch in enumerate(text):
        if ch == ' ':
            out += ' '
        else:
            out += f'{BOLD}{fg(CANDY[i % len(CANDY)])}{ch}{R}'
    return out

def _wild_text(text):
    """Each character from the extended candy bowl."""
    out = ''
    for ch in text:
        if ch == ' ':
            out += ' '
        else:
            out += f'{fg(random.choice(WILD))}{ch}{R}'
    return out

def _grad_color(pct):
    return BAR_COLORS[min(int(pct / 100 * (len(BAR_COLORS) - 1)), len(BAR_COLORS) - 1)]

def render(ctx):
    random.seed(int(datetime.now().timestamp() * 1000) % 100000)
    config = ctx['config']
    used_pct = ctx['used_pct']
    parts = []

    # User — each letter a candy color
    if config.get('show_user', True) and ctx['user_short']:
        parts.append(_rainbow_text(ctx['user_short']))

    # Model — grape purple bold
    m = ctx['model_name']
    sz = ctx['cw_str']
    label = f'{m} {sz}' if sz else m
    parts.append(f'{BOLD}{fg(PURPLE)}{label}{R}')

    # Effort
    if ctx['effort']:
        parts.append(f'{fg(YELLOW)}{ctx["effort"]}{R}')

    # Context bar — Skittles colored fills
    if used_pct is not None:
        N = 10
        fill = used_pct / 100 * N
        bar = ''
        for i in range(N):
            c = BAR_COLORS[i * 2]
            cell = fill - i
            if cell >= 1.0:   bar += f'{fg(c)}\u2588'
            elif cell >= 0.5: bar += f'{fg(c)}\u2593'
            elif cell >= 0.25:bar += f'{fg(c)}\u2591'
            else:             bar += f'{DIM}\u2500'
        bar += R
        pc = _grad_color(used_pct)
        parts.append(f'{bar}  {BOLD}{fg(pc)}{int(round(used_pct))}%{R}')

    # Rate limits — alternating candy colors
    for i, rl in enumerate(ctx['rate_limits']):
        candy = CANDY[i % len(CANDY)]
        pct = rl['pct']
        if pct is None:
            parts.append(f'{fg(candy)}{rl["label"]}{R} {DIM}--{R}')
            continue
        rc = _grad_color(pct)
        ts = rl['reset_str']
        if ts:
            parts.append(f'{fg(candy)}{rl["label"]} {fg(rc)}{pct}%{fg(ORANGE)}@{ts}{R}')
        else:
            parts.append(f'{fg(candy)}{rl["label"]} {fg(rc)}{pct}%{R}')

    # Duration — lemon
    parts.append(f'{fg(YELLOW)}{ctx["session_dur"]}{R}')

    line1 = _candy_sep().join(parts)

    # Line 2 — wild candy everywhere
    git = ctx['git']
    l2 = []
    if git['operation']:
        l2.append(f'{BOLD}{fg(RED)}{git["operation"]}{R}')
    if git['worktree']:
        l2.append(_rainbow_text(f'[{git["worktree"]}]'))
    if git['branch']:
        if git['detached']:
            l2.append(f'{BOLD}{fg(RED)}{git["branch"]} det{R}')
        else:
            l2.append(_rainbow_text(git['branch']))
        if git['remote_short']:
            l2.append(f'{fg(GREEN)}\u2192{_wild_text(git["remote_short"])}{R}')
        ab = ''
        if git['ahead']:
            ab += f'{fg(GREEN)}\u25B2{git["ahead"]}{R}'
        if git['behind']:
            ab += f'{fg(RED)}\u25BC{git["behind"]}{R}'
        if ab:
            l2.append(ab)
    if git['dirty']:
        l2.append(f'{fg(ORANGE)}+{git["dirty"]}{R}')
    if git['stash']:
        l2.append(f'{fg(PURPLE)}\u2691{git["stash"]}{R}')

    path = ctx['path_display']
    if path:
        l2.append(_wild_text(path))

    line2 = _candy_sep().join(l2) if l2 else ''
    return f'{line1}\n{line2}' if line2 else line1
