#!/usr/bin/env bash
# Claude Code rainbow status line
# https://github.com/thereprocase/claude-statusline

PYTHONIOENCODING=utf-8 python -c "
import sys, json, os, tempfile
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

# ── ANSI codes ───────────────────────────────────────────────────────────────
R     = '\033[0m'
DIM   = '\033[2m'
BOLD  = '\033[1m'
SEP   = f' {DIM}\u2502{R} '

# Cyan → green → yellow → orange → red
GRADIENT = [
    51, 50, 49, 48, 47, 83, 119, 155, 191, 227,
    226, 220, 214, 208, 202, 196, 196, 196, 196, 196,
]
THRESHOLDS = [95]

def fg(c):
    return f'\033[38;5;{c}m'

def gradient_color(pct, total=20):
    return min(int(pct / 100 * (total - 1)), total - 1)

def rainbow_text(text):
    \"\"\"Apply rainbow gradient across characters of text.\"\"\"
    if not text:
        return text
    # Spread the full gradient across the string length
    n = len(text)
    # Use a curated rainbow: red, orange, yellow, green, cyan, blue, violet
    RAINBOW = [196, 208, 220, 118, 51, 75, 141]
    out = ''
    for i, ch in enumerate(text):
        ci = int(i / max(n - 1, 1) * (len(RAINBOW) - 1))
        out += f'{fg(RAINBOW[ci])}{ch}'
    return out + R

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
parts = [f'{DIM}{m} {sz}{R}' if sz else f'{DIM}{m}{R}']

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
            alias_part = f'{fg(51)}{abbrev}{R}' if do_rainbow else f'{BOLD}{abbrev}{R}'
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
        if   cell >= 1.0:  bar += f'{c}\u2588'
        elif cell >= 0.75: bar += f'{c}\u2593'
        elif cell >= 0.5:  bar += f'{c}\u2592'
        elif cell >= 0.25: bar += f'{c}\u2591'
        else:              bar += f'{DIM}\u2500'
    bar += R

    pc = fg(GRADIENT[min(int(fill), N - 1)])
    parts.append(f'{bar} {pc}{int(round(used_pct))}%{R}')

# ── Rate limits and threshold tracking ──────────────────────────────────────
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
        parts.append(f'{DIM}{label} {R}{rc}{rl_i}%{R}{DIM}@{ts}{R}')
    else:
        parts.append(f'{DIM}{label} {R}{rc}{rl_i}%{R}')

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

print(SEP.join(parts), end='')
" <<< "$(cat)"
