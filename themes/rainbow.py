"""Rainbow theme — Sherwin-Williams SHIFT palette with corruption glitch effects."""

import random
from datetime import datetime
from core import R, DIM, BOLD, fg

# ── Palettes ────────────────────────────────────────────────────────────────
S = {'onward': 254, 'fractal': 254, 'aqualogic': 188, 'manifest': 252,
     'stratum': 251, 'frequency': 251, 'activate': 124, 'fortifind': 131,
     'interstellar': 179, 'alt': 185, 'bills': 108, 'dopamine': 61}
B = {'red': 167, 'orange': 209, 'gold': 215, 'green': 114, 'blue': 110, 'violet': 104}

GRADIENT = [61, 67, 67, 72, 108, 114, 149, 149, 185, 185,
            179, 179, 173, 173, 137, 131, 131, 131, 131, 124]

CHAR_COLORS = {
    'a': 61, 'b': 67, 'c': 68, 'd': 74, 'e': 110, 'f': 146, 'g': 152,
    'h': 188, 'i': 253, 'j': 254, 'k': 252, 'l': 151, 'm': 115, 'n': 109,
    'o': 108, 'p': 114, 'q': 150, 'r': 149, 's': 185, 't': 221, 'u': 215,
    'v': 222, 'w': 186, 'x': 187, 'y': 251, 'z': 181, '0': 180, '1': 179,
    '2': 173, '3': 209, '4': 137, '5': 131, '6': 167, '7': 125, '8': 124,
    '9': 132, '!': 138, '#': 174, '$': 175, '%': 182, '&': 140, "'": 104,
    '*': 103, '+': 61, '-': 67, '/': 68, '=': 74, '?': 110, '^': 146,
    '_': 152, '`': 188, '{': 253, '|': 254, '}': 252, '~': 151, '.': 115,
}

SEP = f' {DIM}\u2502{R} '

# ── Corruption / glitch engine ──────────────────────────────────────────────
GLITCH_BLOCKS = list('\u2580\u2584\u259A\u259E\u259B\u259C\u259F\u2599')
GLITCH_LINE   = list('\u2573\u256C\u256B\u256A\u2569\u2566\u2560\u2563\u253C')
GLITCH_ALL    = GLITCH_BLOCKS + GLITCH_LINE
BLINK   = '\033[5m'
REVERSE = '\033[7m'

def _gradient_color(pct):
    return min(int(pct / 100 * 19), 19)

def _glitch_char(level):
    gc = fg(random.choice(GRADIENT[-6:]))
    gch = random.choice(GLITCH_ALL)
    if level > 1.5 and random.random() < 0.3:
        gc = REVERSE + gc
    return f'{gc}{gch}{R}'

def _corrupt_text(text, level):
    if level <= 0:
        return text
    out = ''
    in_esc = False
    for ch in text:
        if ch == '\033':
            in_esc = True
        if in_esc:
            out += ch
            if ch == 'm':
                in_esc = False
            continue
        if random.random() < level * 0.25 and ch.strip():
            out += _glitch_char(level)
        else:
            if random.random() < level * 0.2 and ch.strip():
                out += f'{fg(random.choice(GRADIENT[-5:]))}{ch}{R}'
            else:
                out += ch
        if random.random() < level * 0.12 and ch.strip():
            out += _glitch_char(level)
    return out

# ── Render ──────────────────────────────────────────────────────────────────
def render(ctx):
    used_pct = ctx['used_pct']
    config = ctx['config']

    # Corruption level
    linear_t = max(0.0, (used_pct - 55) / 45) if used_pct is not None else 0.0
    corruption = 3.0 * linear_t ** 0.8 if linear_t > 0 else 0.0
    random.seed(int(datetime.now().timestamp() * 1000) % 100000)

    # Model tier color
    _is_1m = ctx['cw_size'] >= 1_000_000
    if ctx['model_family'] == 'opus':
        tier_color = 104 if _is_1m else 60
    elif ctx['model_family'] == 'sonnet':
        tier_color = 61 if _is_1m else 60
    else:
        tier_color = 185

    # ── Build parts ─────────────────────────────────────────────────────────
    parts = []
    sacred_indices = set()

    # User initials
    if config.get('show_user', True) and ctx['user_short']:
        colored = ''
        for ch in ctx['user_short']:
            c = CHAR_COLORS.get(ch.lower())
            if c is not None:
                colored += f'{BOLD}{fg(c)}{ch}{R}'
            else:
                colored += f'{DIM}{ch}{R}'
        parts.append(colored)

    # Model
    m = ctx['model_name']
    sz = ctx['cw_str']
    parts.append(f'{BOLD}{fg(tier_color)}{m} {sz}{R}' if sz else f'{BOLD}{fg(tier_color)}{m}{R}')

    # Effort
    if ctx['effort']:
        parts.append(f'{DIM}{fg(S["manifest"])}{ctx["effort"]}{R}')

    # ── Context bar (BEFORE rate limits) ────────────────────────────────────
    if used_pct is not None:
        N = 10
        fill = used_pct / 100 * N
        bar = ''
        for i in range(N):
            c = fg(GRADIENT[i])
            cell = fill - i

            is_filled = cell >= 0.25
            glitch_this = corruption > 0 and is_filled and random.random() < corruption * 0.7

            if glitch_this:
                gch = random.choice(GLITCH_ALL)
                if corruption > 0.4 and random.random() < corruption * 0.5:
                    c = fg(random.choice(GRADIENT))
                if corruption > 0.7 and random.random() < corruption * 0.3:
                    c = REVERSE + c
                if corruption > 0.9 and random.random() < min(0.8, corruption * 0.2):
                    c = BLINK + c
                bar += f'{c}{gch}'
            elif cell >= 1.0:  bar += f'{c}\u2588'
            elif cell >= 0.75: bar += f'{c}\u2593'
            elif cell >= 0.5:  bar += f'{c}\u2592'
            elif cell >= 0.25: bar += f'{c}\u2591'
            else:
                if corruption > 0.3 and random.random() < corruption * 0.3:
                    bar += f'{fg(random.choice(GRADIENT[-5:]))}{random.choice(GLITCH_ALL)}'
                else:
                    bar += f'{DIM}\u2500'
        bar += R

        overflow = ''
        if corruption > 0.3:
            n_leak = random.randint(0, int(corruption * 5))
            for _ in range(n_leak):
                overflow += _glitch_char(corruption)
            overflow += R if overflow else ''

        pc = fg(GRADIENT[min(int(fill), N - 1)])
        pct_str = f'{int(round(used_pct))}%'
        if corruption > 0.2:
            pct_str = _corrupt_text(pct_str, corruption * 0.4)
        parts.append(f'{bar}{overflow}  {pc}{pct_str}{R}')

    # ── Rate limits ─────────────────────────────────────────────────────────
    for rl in ctx['rate_limits']:
        label = rl['label']
        pct = rl['pct']
        if pct is None:
            parts.append(f'{DIM}{label} --{R}')
            continue
        rc = fg(GRADIENT[_gradient_color(pct)])
        ts = rl['reset_str']
        if ts:
            c_ts = _corrupt_text(ts, corruption * 0.5) if corruption > 0.2 else ts
            parts.append(f'{DIM}{label} {R}{rc}{pct}%{R}{DIM}@{c_ts}{R}')
        else:
            parts.append(f'{DIM}{label} {R}{rc}{pct}%{R}')
        sacred_indices.add(len(parts) - 1)

    # Session duration
    parts.append(f'{DIM}{ctx["session_dur"]}{R}')

    # ── Line 2: git + path ──────────────────────────────────────────────────
    git = ctx['git']
    line2_parts = []
    git_bits = []

    if git['operation']:
        git_bits.append(f'{BOLD}{fg(S["activate"])}{git["operation"]}{R}')
    if git['worktree']:
        git_bits.append(f'{DIM}{fg(S["fractal"])}[{git["worktree"]}]{R}')
    if git['branch']:
        bc = fg(S['aqualogic'])
        if git['detached']:
            git_bits.append(f'{DIM}{fg(S["activate"])}{git["branch"]} det{R}')
        else:
            git_bits.append(f'{DIM}{bc}{git["branch"]}{R}')
        if git['remote_short']:
            git_bits.append(f'{DIM}{fg(S["stratum"])}\u2192{git["remote_short"]}{R}')
        ab = ''
        if git['ahead']:
            ab += f'{fg(S["interstellar"])}\u2191{git["ahead"]}{R}'
        if git['behind']:
            ab += f'{fg(S["activate"])}\u2193{git["behind"]}{R}'
        if ab:
            git_bits.append(ab)
    if git['dirty']:
        git_bits.append(f'{DIM}{fg(S["interstellar"])}+{git["dirty"]}{R}')
    if git['stash']:
        git_bits.append(f'{DIM}{fg(S["dopamine"])}\u2691{git["stash"]}{R}')

    if git_bits:
        line2_parts.append(' '.join(git_bits))

    path = ctx['path_display']
    if path:
        line2_parts.append(f'{fg(S["aqualogic"])}{path}{R}')

    line2 = SEP.join(line2_parts)

    # ── Corruption pass ─────────────────────────────────────────────────────
    if corruption > 0.3:
        bar_idx = len(parts) - 1
        for idx in range(len(parts)):
            if idx == bar_idx or idx in sacred_indices:
                continue
            dist = abs(idx - bar_idx)
            part_level = corruption * max(0, 1.0 - dist * 0.25)
            if part_level > 0.3:
                parts[idx] = _corrupt_text(parts[idx], part_level * 0.4)
        if line2:
            line2 = _corrupt_text(line2, corruption * 0.3)
        sep_level = corruption * 0.4
        glitch_sep = _corrupt_text(SEP, sep_level)
        if corruption > 0.8:
            result = parts[0]
            for p in parts[1:]:
                s = _corrupt_text(SEP, sep_level + random.uniform(0, 0.2))
                result += s + p
            line1 = result
        else:
            line1 = glitch_sep.join(parts)
    else:
        line1 = SEP.join(parts)

    return f'{line1}\n{line2}' if line2 else line1
