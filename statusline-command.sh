#!/usr/bin/env bash
# Claude Code rainbow status line
# https://github.com/thereprocase/claude-statusline

PYTHONIOENCODING=utf-8 python -c "
import sys, json, os, tempfile, random
from datetime import datetime

# ── Parse input ──────────────────────────────────────────────────────────────
data = json.load(sys.stdin)
model      = data.get('model', {}).get('display_name', 'Claude')
model_id   = data.get('model', {}).get('id', '')

# Model family key used to namespace rate-limit state and log entries.
if   'opus'   in model_id: model_family = 'opus'
elif 'haiku'  in model_id: model_family = 'haiku'
else:                       model_family = 'sonnet'
cw         = data.get('context_window', {})
used_pct   = cw.get('used_percentage')
cw_size    = cw.get('context_window_size', 0)

# Corruption level: 0.0 at <=55%, ~0.9 at 65%, exponentially worse to 3.0 at 100%
# Power curve: 3.0 * t^0.8 where t = linear 0..1 over 55-100%
linear_t = max(0.0, (used_pct - 55) / 45) if used_pct is not None else 0.0
corruption = 3.0 * linear_t ** 0.8 if linear_t > 0 else 0.0
random.seed(int(datetime.now().timestamp() * 1000) % 100000)

# ── ANSI codes ───────────────────────────────────────────────────────────────
R     = '\033[0m'
DIM   = '\033[2m'
BOLD  = '\033[1m'
SEP   = f' {DIM}\u2502{R} '

def fg(c):
    return f'\033[38;5;{c}m'

# ── Sherwin-Williams Colormix Foresight 2025 'SHIFT' palette ─────────────────
# 18 colors sampled from the DesignHouse SHIFT forecast overview page. Tuned
# for readability on black terminals: the 6 dark earth tones in the forecast
# (Kindred, Restore, Prosperity, Dark Cloud, Equilibrium, Green Build) are
# kept out of the active rotation — they collapse into the background on
# black. The 12 luminous colors drive every gradient, tier badge, and rainbow
# in this statusline.
SHIFT = {
    'onward':       (225, 230, 236),  # pale ice blue — lightest coolest
    'fractal':      (232, 224, 221),  # off-white
    'aqualogic':    (208, 221, 212),  # pale mint
    'manifest':     (226, 198, 210),  # pale rose
    'stratum':      (209, 201, 190),  # warm sand neutral
    'frequency':    (207, 200, 182),  # champagne
    'activate':     (167,  46,  47),  # signal red
    'fortifind':    (172, 106,  88),  # terracotta
    'interstellar': (214, 160, 105),  # copper shimmer
    'alt':          (200, 220,  73),  # neon yellow-green
    'bills':        (121, 192, 148),  # minted green
    'dopamine':     ( 63, 113, 169),  # electric blue
}

def _rgb_to_256(r, g, b):
    \"\"\"Nearest xterm-256 index for an (r,g,b) triple — exhaustive search
    over the 6x6x6 cube plus the grayscale ramp. Uses squared RGB distance
    with a green bias (roughly matches perceived luminance weighting).\"\"\"
    _cube_levels = (0, 95, 135, 175, 215, 255)
    best_i, best_d = 16, 10 ** 9
    for ri, rv in enumerate(_cube_levels):
        for gi, gv in enumerate(_cube_levels):
            for bi, bv in enumerate(_cube_levels):
                d = (r - rv) ** 2 + 2 * (g - gv) ** 2 + (b - bv) ** 2
                if d < best_d:
                    best_d = d
                    best_i = 16 + 36 * ri + 6 * gi + bi
    for gi in range(24):
        gv = 8 + gi * 10
        d = (r - gv) ** 2 + 2 * (g - gv) ** 2 + (b - gv) ** 2
        if d < best_d:
            best_d = d
            best_i = 232 + gi
    return best_i

S = {k: _rgb_to_256(*v) for k, v in SHIFT.items()}

# ── 'Buddy' sunset rainbow ──────────────────────────────────────────────────
# Sampled from the buddy CLI's rainbow '/buddy' header (which I can't edit).
# This is a warmer, pastel ROYGBV arc. Blended into the text rainbow and the
# expanded per-char palette so the statusline harmonizes with the buddy UI.
BUDDY = {
    'red':    (230,  93,  85),
    'orange': (245, 139,  87),
    'gold':   (250, 195,  95),
    'green':  (145, 200, 130),
    'blue':   (130, 170, 220),
    'violet': (155, 130, 200),
}
B = {k: _rgb_to_256(*v) for k, v in BUDDY.items()}

def _lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))

def _build_gradient(stops, total=20):
    \"\"\"Piecewise-linear RGB gradient through stop colors → xterm-256 list.\"\"\"
    n = len(stops) - 1
    out = []
    for i in range(total):
        t = i / (total - 1)
        seg = min(int(t * n), n - 1)
        local = t * n - seg
        out.append(_rgb_to_256(*_lerp(stops[seg], stops[seg + 1], local)))
    return out

# Cool → hot 20-step gradient for the context bar and rate-limit percent.
# Anchored on the SHIFT palette's saturated colors only — the pastels
# (onward, fractal, aqualogic, manifest, stratum, frequency) are reserved
# for text/chrome, where they'd otherwise wash out against black in a bar.
_GRAD_STOPS = [
    SHIFT['dopamine'],      #   0% — electric blue, calm
    SHIFT['bills'],         #  25% — minted green
    SHIFT['alt'],           #  50% — neon yellow-green
    SHIFT['interstellar'],  #  75% — copper
    SHIFT['fortifind'],     #  90% — terracotta
    SHIFT['activate'],      # 100% — signal red, alarm
]
GRADIENT = _build_gradient(_GRAD_STOPS, total=20)
THRESHOLDS = [95]

def gradient_color(pct, total=20):
    return min(int(pct / 100 * (total - 1)), total - 1)

# Six-color text rainbow for path alias / nickname rendering. This is the
# buddy CLI's own '/buddy' arc so the statusline alias visually rhymes with
# the buddy UI the user can't modify.
RAINBOW = [
    B['red'],
    B['orange'],
    B['gold'],
    B['green'],
    B['blue'],
    B['violet'],
]

def rainbow_text(text):
    \"\"\"Apply SHIFT rainbow gradient across characters of text.\"\"\"
    if not text:
        return text
    n = len(text)
    out = ''
    for i, ch in enumerate(text):
        ci = int(i / max(n - 1, 1) * (len(RAINBOW) - 1))
        out += f'{fg(RAINBOW[ci])}{ch}'
    return out + R

# ── Glitch / corruption engine (single-row only — no combining chars) ───────
GLITCH_BLOCKS = list('\u2580\u2584\u259A\u259E\u259B\u259C\u259F\u2599')
GLITCH_LINE   = list('\u2573\u256C\u256B\u256A\u2569\u2566\u2560\u2563\u253C')
GLITCH_ALL    = GLITCH_BLOCKS + GLITCH_LINE
BLINK   = '\033[5m'
REVERSE = '\033[7m'
STRIKE  = '\033[9m'

def glitch_char(level):
    \"\"\"Return a random inline glitch character with color.\"\"\"
    gc = fg(random.choice(GRADIENT[-6:]))
    gch = random.choice(GLITCH_ALL)
    # At high corruption, add ANSI effects
    if level > 1.5 and random.random() < 0.3:
        gc = REVERSE + gc
    return f'{gc}{gch}{R}'

def corrupt_text(text, level):
    \"\"\"Corrupt visible characters in text, preserving ANSI sequences.
    All effects stay within a single terminal row — no combining chars.\"\"\"
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
        # Replace char with a glitch block
        if random.random() < level * 0.25 and ch.strip():
            out += glitch_char(level)
        else:
            # Color wobble on the original char
            if random.random() < level * 0.2 and ch.strip():
                out += f'{fg(random.choice(GRADIENT[-5:]))}{ch}{R}'
            else:
                out += ch
        # Insert extra glitch char after
        if random.random() < level * 0.12 and ch.strip():
            out += glitch_char(level)
    return out

# ── Ensure storage dir exists ────────────────────────────────────────────────
claude_dir = os.path.expanduser('~/.claude')
os.makedirs(claude_dir, exist_ok=True)
state_file  = os.path.join(claude_dir, 'statusline-state.json')
log_file    = os.path.join(claude_dir, 'rate-limit-log.jsonl')
config_file = os.path.join(claude_dir, 'statusline-config.json')

def safe_read_json(path):
    try:
        with open(path) as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except Exception:
        return {}

def safe_write_json(path, obj):
    try:
        fd, tmp = tempfile.mkstemp(dir=claude_dir, suffix='.tmp', prefix='sl_')
        os.close(fd)
        try:
            with open(tmp, 'w') as f:
                json.dump(obj, f)
            os.replace(tmp, path)
        except Exception:
            try: os.unlink(tmp)
            except Exception: pass
    except Exception:
        pass

def safe_append_line(path, line):
    try:
        with open(path, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass

def rebuild_logged_windows(log_path, family=None):
    \"\"\"Reconstruct crossing history from log when state is lost.\"\"\"
    result = {'five_hour': {}, 'seven_day': {}}
    try:
        with open(log_path) as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    e = json.loads(raw)
                    entry_model = e.get('model')
                    if family is not None and entry_model is not None and entry_model != family:
                        continue
                    if family is not None and entry_model is None and family != 'opus':
                        continue
                    w, rk, th = e.get('window', ''), e.get('resets_at', ''), e.get('threshold')
                    if w in result and rk and th is not None:
                        result[w].setdefault(rk, [])
                        if th not in result[w][rk]:
                            result[w][rk].append(th)
                except Exception:
                    continue
    except FileNotFoundError:
        pass
    return result

def fmt_reset(epoch, day_only=False):
    \"\"\"Format a reset timestamp. Returns '' for invalid or already-past epochs.
    If day_only=True and the reset is not today, returns just the day name.\"\"\"
    try:
        t = datetime.fromtimestamp(float(epoch))
    except Exception:
        return ''
    now = datetime.now()
    if t <= now:
        return ''
    days = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
    h = t.hour % 12 or 12
    ap = 'a' if t.hour < 12 else 'p'
    time_s = f'{h}{ap}'
    if t.date() != now.date():
        if day_only:
            return days[t.weekday()]
        return f'{days[t.weekday()]}{time_s}'
    if day_only:
        return ''
    return time_s

# ── Model abbreviation ───────────────────────────────────────────────────────
SHORT = {
    'claude-opus-4-6': 'Op4.6', 'claude-opus-4-5': 'Op4.5',
    'claude-sonnet-4-6': 'So4.6', 'claude-sonnet-4-5': 'So4.5', 'claude-sonnet-4-0': 'So4',
    'claude-haiku-4-5': 'Ha4.5', 'claude-haiku-3-5': 'Ha3.5',
}
m = model
for prefix, short in SHORT.items():
    if model_id.startswith(prefix):
        m = short
        break
else:
    import re
    m = re.sub(r'^Claude\s+', '', m)
    m = re.sub(r'\s*\(.*?\)', '', m).strip()[:6]

sz = f'{cw_size // 1_000_000}M' if cw_size >= 1_000_000 else (f'{cw_size // 1_000}k' if cw_size >= 1_000 else '')

# Flat tier color applied uniformly across the full model+size segment.
# 1M and 200k contexts get distinct hues. Tier families map to ROYGBIV
# descending by power: Opus→violet, Sonnet→blue, Haiku→yellow-green.
# Interstellar's copper rounds to xterm-179 mustard on black (baby-poop),
# so Opus takes buddy violet instead — premium, distinct, on-palette.
_is_1m = cw_size >= 1_000_000
if model_family == 'opus':
    _tier_color = B['violet'] if _is_1m else _rgb_to_256(115, 85, 155)
elif model_family == 'sonnet':
    _tier_color = S['dopamine'] if _is_1m else _rgb_to_256(70, 100, 140)
else:  # haiku
    _tier_color = S['alt']

# Claude account email → first 3 chars of local-part.
# .claude.json lives either inside CLAUDE_CONFIG_DIR (account-switcher layout)
# or one level up (default layout where CLAUDE_CONFIG_DIR=~/.claude).
def _find_claude_account():
    import re
    cfg_dir = os.environ.get('CLAUDE_CONFIG_DIR') or os.path.expanduser('~/.claude')
    candidates = [
        os.path.join(cfg_dir, '.claude.json'),
        os.path.join(os.path.dirname(cfg_dir.rstrip(os.sep).rstrip('/')), '.claude.json'),
    ]
    for p in candidates:
        try:
            with open(p, 'r', encoding='utf-8') as f:
                txt = f.read()
            mo = re.search(r'\"emailAddress\"\s*:\s*\"([^\"]+)\"', txt)
            if mo:
                return mo.group(1)
        except Exception:
            continue
    return ''

email = _find_claude_account()
user = (email.split('@', 1)[0] if email else '')[:3]

# Permanent per-char color map: every legal dot-atom email local-part char
# gets a UNIQUE xterm-256 color drawn from an expanded SHIFT palette — a
# smooth closed loop through all 12 luminous base colors, densely sampled
# and deduped. Every character lands on its own color, every color stays
# recognizably on-palette.
_LEGAL_EMAIL_CHARS = \"abcdefghijklmnopqrstuvwxyz0123456789!#\$%&'*+-/=?^_\`{|}~.\"

# Closed-loop traversal through both palettes — SHIFT + buddy — hue-ordered
# for smooth interpolation. Per-char email colors sample from this combined
# loop, so initials blend DNA from the Colormix forecast and the buddy CLI.
_LOOP_RGB = [
    SHIFT['dopamine'],     # electric blue
    BUDDY['blue'],         # pastel sky
    SHIFT['onward'],       # pale ice
    SHIFT['aqualogic'],    # pale mint
    SHIFT['bills'],        # minted green
    BUDDY['green'],        # pastel leaf
    SHIFT['alt'],           # neon yellow-green
    BUDDY['gold'],          # warm gold
    SHIFT['frequency'],     # champagne
    SHIFT['stratum'],       # warm sand
    SHIFT['fractal'],       # off-white
    SHIFT['interstellar'],  # copper
    BUDDY['orange'],        # pastel orange
    SHIFT['fortifind'],     # terracotta
    BUDDY['red'],           # pastel red
    SHIFT['activate'],      # signal red
    SHIFT['manifest'],      # rose
    BUDDY['violet'],        # twilight violet
]
_LOOP_RGB.append(_LOOP_RGB[0])  # close the loop

def _expand_palette(target_count):
    \"\"\"Densely sample the SHIFT loop, dedupe xterm-256 hits, return at least
    target_count unique color indices. Starts at 8 steps/segment, doubles
    until we have enough uniques.\"\"\"
    steps = 8
    while True:
        uniques, seen = [], set()
        for seg in range(len(_LOOP_RGB) - 1):
            a, b = _LOOP_RGB[seg], _LOOP_RGB[seg + 1]
            for k in range(steps):
                t = k / steps
                idx = _rgb_to_256(*_lerp(a, b, t))
                if idx not in seen:
                    seen.add(idx)
                    uniques.append(idx)
        if len(uniques) >= target_count or steps > 128:
            return uniques
        steps *= 2

_EXPANDED = _expand_palette(len(_LEGAL_EMAIL_CHARS))

# Deterministic spread: stride through the expanded palette with a step
# coprime to its length so consecutive chars land on maximally separated hues.
_stride = max(1, len(_EXPANDED) // len(_LEGAL_EMAIL_CHARS)) or 1
# Nudge stride up by 1 if it divides the length evenly (to stay coprime-ish).
if _stride > 1 and len(_EXPANDED) % _stride == 0:
    _stride += 1
CHAR_COLORS = {}
_used = set()
for _i, _ch in enumerate(_LEGAL_EMAIL_CHARS):
    _pos = (_i * _stride) % len(_EXPANDED)
    # Linear probe if stride collision somehow occurs
    _probe = 0
    while _EXPANDED[(_pos + _probe) % len(_EXPANDED)] in _used and _probe < len(_EXPANDED):
        _probe += 1
    _color = _EXPANDED[(_pos + _probe) % len(_EXPANDED)]
    _used.add(_color)
    CHAR_COLORS[_ch] = _color

parts = []
if user:
    colored = ''
    for _ch in user:
        _c = CHAR_COLORS.get(_ch.lower())
        if _c is not None:
            colored += f'{BOLD}{fg(_c)}{_ch}{R}'
        else:
            colored += f'{DIM}{_ch}{R}'
    parts.append(colored)
parts.append(f'{BOLD}{fg(_tier_color)}{m} {sz}{R}' if sz else f'{BOLD}{fg(_tier_color)}{m}{R}')

# ── Working directory ────────────────────────────────────────────────────────
# Config file: ~/.claude/statusline-config.json
#   {
#     "path_aliases": { "D:/ClauDe": "ClauDe" },
#     "path_depth": 3,
#     "rainbow_aliases": true
#   }
# path_aliases:    map directory prefixes to short nicknames (longest prefix wins)
# path_depth:      max directory segments to show (default 3)
# rainbow_aliases: apply rainbow gradient to the alias portion (default true)
cwd = data.get('cwd', '')
if cwd:
    config = safe_read_json(config_file)
    aliases = config.get('path_aliases', {})
    path_depth = config.get('path_depth', 3)
    do_rainbow = config.get('rainbow_aliases', True)

    # Normalize to forward slashes for cross-platform matching
    norm_cwd = cwd.replace(os.sep, '/')

    # Find longest matching alias prefix
    best_alias, best_prefix = None, ''
    for raw_path, nickname in aliases.items():
        norm_path = raw_path.replace(os.sep, '/').rstrip('/')
        if norm_cwd == norm_path or norm_cwd.startswith(norm_path + '/'):
            if len(norm_path) > len(best_prefix):
                best_alias, best_prefix = nickname, norm_path

    if best_alias is not None:
        remainder = norm_cwd[len(best_prefix):].lstrip('/')
        r_segs = remainder.split('/') if remainder else []
        # Alias counts as one segment toward path_depth
        max_r = max(path_depth - 1, 0)
        elided = len(r_segs) > max_r
        if elided:
            r_segs = r_segs[-max_r:]
        # When segments are elided: show drive + abbreviated alias + ellipsis
        if elided:
            # Extract drive prefix from original path (e.g. "D:/" from "D:/ClauDe")
            drive = ''
            if len(best_prefix) >= 2 and best_prefix[1] == ':':
                drive = best_prefix[:3]  # "D:/"
            abbrev = best_alias[0] if best_alias else best_alias
            alias_part = f\"{fg(S['alt'])}{abbrev}{R}\" if do_rainbow else f'{BOLD}{abbrev}{R}'
            alias_part = f'{DIM}{drive}{R}{alias_part}'
        else:
            alias_part = rainbow_text(best_alias) if do_rainbow else f'{BOLD}{best_alias}{R}'
        if r_segs:
            sep = f'{DIM}\u2026/{R}' if elided else f'{DIM}/{R}'
            short_cwd = f'{alias_part}{sep}{\"/\".join(r_segs)}{R}'
        else:
            short_cwd = alias_part
    else:
        # Default: ~ substitution, then trim to path_depth segments
        home = os.path.expanduser('~').replace(os.sep, '/')
        if norm_cwd.startswith(home):
            norm_cwd = '~' + norm_cwd[len(home):]
        segs = norm_cwd.split('/')
        elided = len(segs) > path_depth
        if elided:
            segs = segs[-path_depth:]
        prefix = f'{DIM}\u2026/{R}' if elided else ''
        short_cwd = f'{prefix}{\"/\".join(segs)}{R}'

    parts.append(short_cwd)

# ── Context bar ──────────────────────────────────────────────────────────────
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
            # Color wobble at medium corruption
            if corruption > 0.4 and random.random() < corruption * 0.5:
                c = fg(random.choice(GRADIENT))
            # ANSI chaos at high corruption
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
            # Empty cells: at high corruption, ghosts appear in the void
            if corruption > 0.3 and random.random() < corruption * 0.3:
                bar += f'{fg(random.choice(GRADIENT[-5:]))}{random.choice(GLITCH_ALL)}'
            else:
                bar += f'{DIM}\u2500'
    bar += R

    # Overflow: glitch chars that leak past the bar boundary
    overflow = ''
    if corruption > 0.3:
        n_leak = random.randint(0, int(corruption * 5))
        for _ in range(n_leak):
            overflow += glitch_char(corruption)
        overflow += R if overflow else ''

    pc = fg(GRADIENT[min(int(fill), N - 1)])
    pct_str = f'{int(round(used_pct))}%'
    if corruption > 0.2:
        pct_str = corrupt_text(pct_str, corruption * 0.4)
    parts.append(f'{bar}{overflow} {pc}{pct_str}{R}')

# ── Rate limits and threshold tracking ──────────────────────────────────────
sacred_indices = set()   # parts indices that must not be corrupted in final pass
state = safe_read_json(state_file)
state_dirty = False
state_lost = len(state) == 0
rebuilt = rebuild_logged_windows(log_file, model_family) if state_lost else None

for key in ['five_hour', 'seven_day']:
    label = '5h' if key == 'five_hour' else '7d'
    rl_data = data.get('rate_limits', {}).get(key, {})
    rl = rl_data.get('used_percentage')

    if rl is None:
        parts.append(f'{DIM}{label} --{R}')
        continue

    rc = fg(GRADIENT[gradient_color(rl)])
    resets_at = rl_data.get('resets_at')
    rl_i = int(round(rl))

    # Tiered detail: show reset time when usage is high OR reset is near
    #   5h: show when >=50% OR within 30 min of reset
    #   7d: show full time when >=80% OR within 12h; day-only otherwise
    ts = ''
    if resets_at is not None:
        try:
            reset_dt = datetime.fromtimestamp(float(resets_at))
            secs_left = (reset_dt - datetime.now()).total_seconds()
        except Exception:
            secs_left = float('inf')
        if key == 'five_hour':
            if rl_i >= 50 or secs_left <= 1800:
                ts = fmt_reset(resets_at)
        else:
            if rl_i >= 80 or secs_left <= 43200:
                ts = fmt_reset(resets_at)
            else:
                ts = fmt_reset(resets_at, day_only=True)

    if ts:
        # Corrupt the reset time hint, but never the percentage
        c_ts = corrupt_text(ts, corruption * 0.5) if corruption > 0.2 else ts
        parts.append(f'{DIM}{label} {R}{rc}{rl_i}%{R}{DIM}@{c_ts}{R}')
    else:
        parts.append(f'{DIM}{label} {R}{rc}{rl_i}%{R}')
    # Mark rate-limit parts as sacred (index tracked for final-output pass)
    sacred_indices.add(len(parts) - 1)

    # ── Threshold crossing logging (silent — no display) ─────────────────────
    try:
        rk = str(int(float(resets_at))) if resets_at is not None else 'unknown'
    except Exception:
        rk = 'unknown'
    lk     = f'{model_family}_{key}_logged'
    rk_key = f'{model_family}_{key}_last_rk'
    logged = (rebuilt.get(key, {}) if rebuilt else state.get(lk, {}))

    if not state_lost and rk != state.get(rk_key):
        for th in THRESHOLDS:
            state[f'{model_family}_{key}_armed_{th}'] = True
        state_dirty = True
    state[rk_key] = rk
    state_dirty = True

    for th in THRESHOLDS:
        ak = f'{model_family}_{key}_armed_{th}'
        if state_lost:
            already = th in logged.get(rk, [])
            armed = not already if rl >= th else True
        else:
            armed = state.get(ak, True)

        if rl >= th and armed:
            if th not in logged.get(rk, []):
                entry = json.dumps({'ts': datetime.now().isoformat(), 'model': model_family, 'window': key, 'pct': rl, 'threshold': th, 'resets_at': rk})
                safe_append_line(log_file, entry)
                logged.setdefault(rk, []).append(th)
            state[ak] = False
        elif rl < th and not armed:
            state[ak] = True

    if len(logged) > 10:
        for k in sorted(logged.keys())[:-10]:
            del logged[k]
    state[lk] = logged
    state[key] = rl

if state_dirty:
    safe_write_json(state_file, state)

# ── Final output (corruption spreads to everything at high levels) ───────────
if corruption > 0.3:
    # Corrupt other parts based on proximity to the bar (user, model, cwd, bar)
    bar_idx = 3 if len(parts) > 3 else len(parts) - 1
    for idx in range(len(parts)):
        if idx == bar_idx or idx in sacred_indices:
            continue  # bar already corrupted; rate-limit %s are sacred
        # Distance from bar determines corruption intensity
        dist = abs(idx - bar_idx)
        part_level = corruption * max(0, 1.0 - dist * 0.25)
        # Only start corrupting neighbors at medium corruption
        if part_level > 0.3:
            parts[idx] = corrupt_text(parts[idx], part_level * 0.4)
    # Corrupt the separators themselves
    sep_level = corruption * 0.4
    glitch_sep = corrupt_text(SEP, sep_level)
    # At extreme corruption, the separator mutates per-join
    if corruption > 0.8:
        result = parts[0]
        for p in parts[1:]:
            s = corrupt_text(SEP, sep_level + random.uniform(0, 0.2))
            result += s + p
        print(result, end='')
    else:
        print(glitch_sep.join(parts), end='')
else:
    print(SEP.join(parts), end='')
" <<< "$(cat)"
