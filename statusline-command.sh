#!/usr/bin/env bash
# Claude Code rainbow status line
# https://github.com/thereprocase/claude-statusline

PYTHONIOENCODING=utf-8 python -c "
import sys, json, os, re, tempfile, random, subprocess
from datetime import datetime, timedelta

# ── Parse input ──────────────────────────────────────────────────────────────
data = json.load(sys.stdin)
model      = data.get('model', {}).get('display_name', 'Claude')
model_id   = data.get('model', {}).get('id', '')

if   'opus'   in model_id: model_family = 'opus'
elif 'haiku'  in model_id: model_family = 'haiku'
else:                       model_family = 'sonnet'
cw         = data.get('context_window', {})
used_pct   = cw.get('used_percentage')
cw_size    = cw.get('context_window_size', 0)
cwd        = data.get('cwd', '')

# Corruption: 0.0 at <=55%, power curve to 3.0 at 100%
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

# ── Precomputed xterm-256 palettes ───────────────────────────────────────────
# Generated from Sherwin-Williams Colormix 2025 'SHIFT' + buddy sunset rainbow.
# RGB originals and _rgb_to_256 computation preserved in git history.
S = {'onward': 254, 'fractal': 254, 'aqualogic': 188, 'manifest': 252,
     'stratum': 251, 'frequency': 251, 'activate': 124, 'fortifind': 131,
     'interstellar': 179, 'alt': 185, 'bills': 108, 'dopamine': 61}
B = {'red': 167, 'orange': 209, 'gold': 215, 'green': 114, 'blue': 110, 'violet': 104}

# Cool-to-hot 20-step gradient for context bar and rate-limit coloring.
GRADIENT = [61, 67, 67, 72, 108, 114, 149, 149, 185, 185,
            179, 179, 173, 173, 137, 131, 131, 131, 131, 124]
THRESHOLDS = [95]

def gradient_color(pct, total=20):
    return min(int(pct / 100 * (total - 1)), total - 1)

# Per-char email color map (precomputed from closed-loop SHIFT+buddy palette).
CHAR_COLORS = {
    'a': 61, 'b': 67, 'c': 68, 'd': 74, 'e': 110, 'f': 146, 'g': 152,
    'h': 188, 'i': 253, 'j': 254, 'k': 252, 'l': 151, 'm': 115, 'n': 109,
    'o': 108, 'p': 114, 'q': 150, 'r': 149, 's': 185, 't': 221, 'u': 215,
    'v': 222, 'w': 186, 'x': 187, 'y': 251, 'z': 181, '0': 180, '1': 179,
    '2': 173, '3': 209, '4': 137, '5': 131, '6': 167, '7': 125, '8': 124,
    '9': 132, '!': 138, '#': 174, '\$': 175, '%': 182, '&': 140, \"'\": 104,
    '*': 103, '+': 61, '-': 67, '/': 68, '=': 74, '?': 110, '^': 146,
    '_': 152, '\`': 188, '{': 253, '|': 254, '}': 252, '~': 151, '.': 115,
}

# ── Glitch / corruption engine ───────────────────────────────────────────────
GLITCH_BLOCKS = list('\u2580\u2584\u259A\u259E\u259B\u259C\u259F\u2599')
GLITCH_LINE   = list('\u2573\u256C\u256B\u256A\u2569\u2566\u2560\u2563\u253C')
GLITCH_ALL    = GLITCH_BLOCKS + GLITCH_LINE
BLINK   = '\033[5m'
REVERSE = '\033[7m'

def glitch_char(level):
    gc = fg(random.choice(GRADIENT[-6:]))
    gch = random.choice(GLITCH_ALL)
    if level > 1.5 and random.random() < 0.3:
        gc = REVERSE + gc
    return f'{gc}{gch}{R}'

def corrupt_text(text, level):
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
            out += glitch_char(level)
        else:
            if random.random() < level * 0.2 and ch.strip():
                out += f'{fg(random.choice(GRADIENT[-5:]))}{ch}{R}'
            else:
                out += ch
        if random.random() < level * 0.12 and ch.strip():
            out += glitch_char(level)
    return out

# ── Storage helpers ──────────────────────────────────────────────────────────
claude_dir = os.path.expanduser('~/.claude')
os.makedirs(claude_dir, exist_ok=True)
state_file  = os.path.join(claude_dir, 'statusline-state.json')
log_file    = os.path.join(claude_dir, 'rate-limit-log.jsonl')

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
    \"\"\"Format a reset timestamp. Returns '' for invalid or already-past epochs.\"\"\"
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
    m = re.sub(r'^Claude\s+', '', m)
    m = re.sub(r'\s*\(.*?\)', '', m).strip()[:6]

sz = f'{cw_size // 1_000_000}M' if cw_size >= 1_000_000 else (f'{cw_size // 1_000}k' if cw_size >= 1_000 else '')

# Tier color: Opus->violet, Sonnet->blue, Haiku->yellow-green. 1M brighter.
_is_1m = cw_size >= 1_000_000
if model_family == 'opus':
    _tier_color = 104 if _is_1m else 60
elif model_family == 'sonnet':
    _tier_color = 61 if _is_1m else 60
else:
    _tier_color = 185

# ── Account email -> colored initials ────────────────────────────────────────
def _find_claude_account():
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

# ── Build line 1 parts ──────────────────────────────────────────────────────
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

# Effort level (if exposed in statusline data)
_effort = data.get('effort')
if _effort:
    _ec = fg(S['manifest'])
    parts.append(f'{DIM}{_ec}{_effort}{R}')

# ── Rate limits and threshold tracking ──────────────────────────────────────
sacred_indices = set()
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
        c_ts = corrupt_text(ts, corruption * 0.5) if corruption > 0.2 else ts
        parts.append(f'{DIM}{label} {R}{rc}{rl_i}%{R}{DIM}@{c_ts}{R}')
    else:
        parts.append(f'{DIM}{label} {R}{rc}{rl_i}%{R}')
    sacred_indices.add(len(parts) - 1)

    # Threshold crossing logging
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

# ── Context bar (rightmost on line 1) ────────────────────────────────────────
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
            overflow += glitch_char(corruption)
        overflow += R if overflow else ''

    pc = fg(GRADIENT[min(int(fill), N - 1)])
    pct_str = f'{int(round(used_pct))}%'
    if corruption > 0.2:
        pct_str = corrupt_text(pct_str, corruption * 0.4)
    parts.append(f'{bar}{overflow} {pc}{pct_str}{R}')

# ── Session duration (end of line 1) ────────────────────────────────────────
_now_ts = datetime.now().timestamp()
_sess = state.get('session_start', {})
# Gap > 5 minutes between renders means new session
if _now_ts - _sess.get('last_seen', 0) > 300:
    _sess = {'ts': _now_ts}
_sess['last_seen'] = _now_ts
state['session_start'] = _sess
state_dirty = True
_elapsed = _now_ts - _sess.get('ts', _now_ts)
if _elapsed >= 3600:
    _dur = f'{int(_elapsed // 3600)}h{int(_elapsed % 3600 // 60)}m'
elif _elapsed >= 60:
    _dur = f'{int(_elapsed // 60)}m'
else:
    _dur = f'{int(_elapsed)}s'
parts.append(f'{DIM}{_dur}{R}')

# ── Log rotation (keep 2 months) ────────────────────────────────────────────
try:
    if os.path.exists(log_file) and os.path.getsize(log_file) > 4096:
        cutoff = (datetime.now() - timedelta(days=60)).isoformat()
        with open(log_file) as f:
            lines = f.readlines()
        kept = []
        for ln in lines:
            try:
                if json.loads(ln).get('ts', '') >= cutoff:
                    kept.append(ln)
            except Exception:
                pass
        if len(kept) < len(lines):
            with open(log_file, 'w') as f:
                f.writelines(kept)
except Exception:
    pass

if state_dirty:
    safe_write_json(state_file, state)

# ── Build line 2: git branch │ path ──────────────────────────────────────────
_br = ''
try:
    _br = subprocess.check_output(
        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
        cwd=cwd or None, stderr=subprocess.DEVNULL, timeout=2
    ).decode().strip()
except Exception:
    pass

path_line = ''
if cwd:
    norm_cwd = cwd.replace(os.sep, '/')
    MAX_PATH_LEN = 75

    if len(norm_cwd) <= MAX_PATH_LEN:
        path_line = f'{DIM}{norm_cwd}{R}'
    else:
        if len(norm_cwd) >= 3 and norm_cwd[1] == ':' and norm_cwd[2] == '/':
            drive = norm_cwd[:3]
            rest = norm_cwd[3:]
        else:
            drive = ''
            rest = norm_cwd

        segs = rest.split('/')
        first_abbrev = segs[0][:2] if segs else ''
        prefix = f'{drive}{first_abbrev}...'

        budget = MAX_PATH_LEN - len(prefix)
        tail_parts = []
        for seg in reversed(segs[1:]):
            candidate = '/' + seg
            needed = len(candidate) + sum(len(p) for p in tail_parts)
            if needed > budget and tail_parts:
                break
            tail_parts.insert(0, candidate)

        truncated = prefix + ''.join(tail_parts)
        path_line = f'{DIM}{truncated}{R}'

_dirty = 0
try:
    _gs = subprocess.check_output(
        ['git', 'status', '--porcelain'],
        cwd=cwd or None, stderr=subprocess.DEVNULL, timeout=2
    ).decode().strip()
    _dirty = len(_gs.splitlines()) if _gs else 0
except Exception:
    pass

line2_parts = []
if _br:
    _bc = fg(S['aqualogic'])
    if _dirty:
        _dc = fg(S['interstellar'])
        line2_parts.append(f'{DIM}{_bc}{_br} {_dc}+{_dirty}{R}')
    else:
        line2_parts.append(f'{DIM}{_bc}{_br}{R}')
if path_line:
    line2_parts.append(path_line)
line2 = SEP.join(line2_parts)

# ── Final output ─────────────────────────────────────────────────────────────
if corruption > 0.3:
    bar_idx = len(parts) - 1
    for idx in range(len(parts)):
        if idx == bar_idx or idx in sacred_indices:
            continue
        dist = abs(idx - bar_idx)
        part_level = corruption * max(0, 1.0 - dist * 0.25)
        if part_level > 0.3:
            parts[idx] = corrupt_text(parts[idx], part_level * 0.4)
    if line2:
        line2 = corrupt_text(line2, corruption * 0.3)
    sep_level = corruption * 0.4
    glitch_sep = corrupt_text(SEP, sep_level)
    if corruption > 0.8:
        result = parts[0]
        for p in parts[1:]:
            s = corrupt_text(SEP, sep_level + random.uniform(0, 0.2))
            result += s + p
        line1 = result
    else:
        line1 = glitch_sep.join(parts)
else:
    line1 = SEP.join(parts)

output = f'{line1}\n{line2}' if line2 else line1
print(output, end='')
" <<< "$(cat)"
