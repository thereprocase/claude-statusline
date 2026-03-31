#!/usr/bin/env bash
# Claude Code rainbow status line
# https://github.com/YOUR_USERNAME/claude-statusline

PYTHONIOENCODING=utf-8 python -c "
import sys, json, os, tempfile
from datetime import datetime

# ── Parse input ──────────────────────────────────────────────────────────────
data = json.load(sys.stdin)
model      = data.get('model', {}).get('display_name', 'Claude')
model_id   = data.get('model', {}).get('id', '')
cw         = data.get('context_window', {})
used_pct   = cw.get('used_percentage')
cw_size    = cw.get('context_window_size', 0)
cost_data  = data.get('cost', {})
cost_usd   = cost_data.get('total_cost_usd')
lines_add  = cost_data.get('total_lines_added')
lines_rem  = cost_data.get('total_lines_removed')

# ── ANSI codes ───────────────────────────────────────────────────────────────
R     = '\033[0m'
DIM   = '\033[2m'
BOLD  = '\033[1m'
GREEN = '\033[38;5;114m'
RED   = '\033[38;5;203m'
GOLD  = '\033[38;5;220m'
SEP   = f' {DIM}\u2502{R} '

# Cyan → green → yellow → orange → red (stays red at 80-100%, not magenta)
GRADIENT = [
    51, 50, 49, 48, 47, 83, 119, 155, 191, 227,
    226, 220, 214, 208, 202, 196, 196, 196, 196, 196,
]
THRESHOLDS = [30, 55, 75, 99]

def fg(c):
    return f'\033[38;5;{c}m'

def gradient_color(pct, total=20):
    return min(int(pct / 100 * (total - 1)), total - 1)

# ── Ensure storage dir exists ────────────────────────────────────────────────
claude_dir = os.path.expanduser('~/.claude')
os.makedirs(claude_dir, exist_ok=True)
state_file = os.path.join(claude_dir, 'statusline-state.json')
log_file   = os.path.join(claude_dir, 'rate-limit-log.jsonl')

def safe_read_json(path):
    try:
        with open(path) as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except Exception:
        return {}

def safe_write_json(path, obj):
    # Close raw fd immediately after mkstemp to prevent fd leak if open() raises.
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

def rebuild_logged_windows(log_path):
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

def fmt_reset(epoch):
    \"\"\"Format a reset timestamp. Returns '' for invalid or already-past epochs.\"\"\"
    try:
        t = datetime.fromtimestamp(float(epoch))
    except Exception:
        return ''
    now = datetime.now()
    if t <= now:
        return ''
    h = t.hour % 12 or 12
    ap = 'am' if t.hour < 12 else 'pm'  # avoid strftime('%p') — empty on some Windows locales
    time_s = f'{h}{ap}'
    if t.date() != now.date():
        days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
        return f'{days[t.weekday()]} {time_s}'
    return time_s

def count_monthly_crossings_from_log(log_path):
    \"\"\"Full log scan for monthly counts. Only called on state loss or month rollover.\"\"\"
    prefix = datetime.now().strftime('%Y-%m')
    five_h, seven_d = 0, 0
    try:
        with open(log_path) as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    e = json.loads(raw)
                except Exception:
                    continue
                if not e.get('ts', '').startswith(prefix):
                    continue
                w = e.get('window')
                if w == 'five_hour':   five_h += 1
                elif w == 'seven_day': seven_d += 1
    except FileNotFoundError:
        pass
    return five_h, seven_d

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
parts = [f'{BOLD}{m} {sz}{R}' if sz else f'{BOLD}{m}{R}']

# ── Context bar ──────────────────────────────────────────────────────────────
if used_pct is not None:
    N = 20
    fill = used_pct / 100 * N
    full = int(fill)
    frac = fill - full
    # Index 0 handled as dim dash below (0% cell = empty, not a space character)
    blocks = ['', '\u258f', '\u258e', '\u258d', '\u258c', '\u258b', '\u258a', '\u2589']

    bar = ''
    for i in range(N):
        c = fg(GRADIENT[i])
        if   i < full:  bar += f'{c}\u2588'
        elif i == full: bar += f'{c}{blocks[int(frac * 8)]}' if int(frac * 8) > 0 else f'{DIM}\u2500'
        else:           bar += f'{DIM}\u2500'
    bar += R

    pc = fg(GRADIENT[min(full, N - 1)])
    parts.append(f'{bar} {pc}{used_pct:.1f}%{R}')

# ── Rate limits and threshold tracking ──────────────────────────────────────
# Processed independently of context window so rate limits are always tracked
# even when context_window.used_percentage is absent.
state = safe_read_json(state_file)
state_before = json.dumps(state, sort_keys=True)
state_lost = len(state) == 0
rebuilt = rebuild_logged_windows(log_file) if state_lost else None

# Monthly count cache — recount from log only on state loss or month rollover,
# then increment in-place as new crossings are detected this render.
current_month = datetime.now().strftime('%Y-%m')
if state_lost or state.get('monthly_key') != current_month:
    fh_init, sd_init = count_monthly_crossings_from_log(log_file)
    state['monthly_key'] = current_month
    state['monthly_5h']  = fh_init
    state['monthly_7d']  = sd_init

for key in ['five_hour', 'seven_day']:
    rl_data = data.get('rate_limits', {}).get(key, {})
    rl = rl_data.get('used_percentage')
    if rl is None:
        continue

    label = '5h' if key == 'five_hour' else '7d'
    rc = fg(GRADIENT[gradient_color(rl)])
    resets_at = rl_data.get('resets_at')
    ts = fmt_reset(resets_at) if resets_at is not None else ''
    parts.append(f'{DIM}{label}:{R}{rc}{rl:.0f}%{R} {DIM}{ts}{R}' if ts else f'{DIM}{label}:{R}{rc}{rl:.0f}%{R}')

    # ── Threshold crossing logic ─────────────────────────────────────────────
    try:
        rk = str(int(float(resets_at))) if resets_at is not None else 'unknown'
    except Exception:
        rk = 'unknown'
    lk   = f'{key}_logged'
    rk_key = f'{key}_last_rk'
    logged = (rebuilt.get(key, {}) if rebuilt else state.get(lk, {}))

    # Re-arm all thresholds when the reset window rolls over (new resets_at).
    # Without this, a disarmed flag from the old window suppresses crossings
    # in the new window until the rate first drops below the threshold.
    if not state_lost and rk != state.get(rk_key):
        for th in THRESHOLDS:
            state[f'{key}_armed_{th}'] = True
    state[rk_key] = rk

    for th in THRESHOLDS:
        ak = f'{key}_armed_{th}'
        if state_lost:
            already = th in logged.get(rk, [])
            armed = not already if rl >= th else True
        else:
            armed = state.get(ak, True)

        if rl >= th and armed:
            if th not in logged.get(rk, []):
                entry = json.dumps({'ts': datetime.now().isoformat(), 'window': key, 'pct': rl, 'threshold': th, 'resets_at': rk})
                safe_append_line(log_file, entry)
                logged.setdefault(rk, []).append(th)
                mk = 'monthly_5h' if key == 'five_hour' else 'monthly_7d'
                state[mk] = state.get(mk, 0) + 1
            state[ak] = False
        elif rl < th and not armed:
            state[ak] = True

    # Prune old windows from state (keep last 10)
    if len(logged) > 10:
        for k in sorted(logged.keys())[:-10]:
            del logged[k]
    state[lk] = logged
    state[key] = rl

# Only write state if something actually changed this render
if json.dumps(state, sort_keys=True) != state_before:
    safe_write_json(state_file, state)

# ── Cost ─────────────────────────────────────────────────────────────────────
if cost_usd and cost_usd > 0:
    parts.append(f'{GOLD}\u0024{cost_usd:.2f}{R}')

# ── Lines changed ────────────────────────────────────────────────────────────
if lines_add is not None and lines_rem is not None and (lines_add > 0 or lines_rem > 0):
    parts.append(f'{GREEN}+{lines_add}{R}{DIM}/{R}{RED}-{lines_rem}{R}')

# ── Monthly crossing counters ────────────────────────────────────────────────
fh = state.get('monthly_5h', 0)
sd = state.get('monthly_7d', 0)
dc = fg(GRADIENT[min(int(fh / 30 * 19), 19)])
wc = fg(GRADIENT[min(int(sd / 4 * 19), 19)])
parts.append(f'{DIM}5h:{R}{dc}{fh}x{R}{DIM}/7d:{R}{wc}{sd}x{R}')

print(SEP.join(parts), end='')
" <<< "$(cat)"
