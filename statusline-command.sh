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

# Model family key used to namespace rate-limit state and log entries.
# Keeps Sonnet and Opus buckets separate — they have distinct rate limit pools.
if   'opus'   in model_id: model_family = 'opus'
elif 'haiku'  in model_id: model_family = 'haiku'
else:                       model_family = 'sonnet'
cw         = data.get('context_window', {})
used_pct   = cw.get('used_percentage')
cw_size    = cw.get('context_window_size', 0)
cur_usage  = cw.get('current_usage', {})
cost_data  = data.get('cost', {})
cost_usd   = cost_data.get('total_cost_usd')

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

def rebuild_logged_windows(log_path, family=None):
    \"\"\"Reconstruct crossing history from log when state is lost.
    Filters entries by model family. Legacy entries (no 'model' key) are
    attributed to opus only.\"\"\"
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
    ap = 'a' if t.hour < 12 else 'p'
    time_s = f'{h}{ap}'
    if t.date() != now.date():
        days = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
        return f'{days[t.weekday()]}{time_s}'
    return time_s

def count_monthly_crossings_from_log(log_path, family=None):
    \"\"\"Count crossings for the current month. Reads log in reverse and stops
    as soon as entries fall before the current month — avoids scanning the
    full log history on state loss or month rollover.\"\"\"
    prefix = datetime.now().strftime('%Y-%m')
    five_h, seven_d = 0, 0
    try:
        with open(log_path) as f:
            lines = f.readlines()
        for raw in reversed(lines):
            raw = raw.strip()
            if not raw:
                continue
            try:
                e = json.loads(raw)
            except Exception:
                continue
            ts = e.get('ts', '')
            if ts and ts < prefix:
                break  # log is append-only; nothing older can match
            if not ts.startswith(prefix):
                continue
            entry_model = e.get('model')
            if family is not None and entry_model is not None and entry_model != family:
                continue
            if family is not None and entry_model is None and family != 'opus':
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
    parts.append(f'{bar} {pc}{used_pct:.0f}%{R}')

# ── Per-turn token counter ────────────────────────────────────────────────────
tok_in  = cur_usage.get('input_tokens', 0)
tok_out = cur_usage.get('output_tokens', 0)
if tok_in or tok_out:
    parts.append(f'{DIM}\u2191{R}{tok_in} {DIM}\u2193{R}{tok_out}')

# ── Rate limits and threshold tracking ──────────────────────────────────────
# Processed independently of context window so rate limits are always tracked
# even when context_window.used_percentage is absent.
state = safe_read_json(state_file)
state_dirty = False
state_lost = len(state) == 0
rebuilt = rebuild_logged_windows(log_file, model_family) if state_lost else None

# Monthly count cache — recount from log only on state loss or month rollover,
# then increment in-place as new crossings are detected this render.
current_month = datetime.now().strftime('%Y-%m')
# Per-model monthly cache key keeps Sonnet/Opus/Haiku counts separate.
monthly_key_name = f'monthly_key_{model_family}'
monthly_5h_name  = f'monthly_5h_{model_family}'
monthly_7d_name  = f'monthly_7d_{model_family}'
if state_lost or state.get(monthly_key_name) != current_month:
    fh_init, sd_init = count_monthly_crossings_from_log(log_file, model_family)
    state[monthly_key_name] = current_month
    state[monthly_5h_name]  = fh_init
    state[monthly_7d_name]  = sd_init
    state_dirty = True

for key in ['five_hour', 'seven_day']:
    rl_data = data.get('rate_limits', {}).get(key, {})
    rl = rl_data.get('used_percentage')
    if rl is None:
        continue

    label = '5h' if key == 'five_hour' else '7d'
    rc = fg(GRADIENT[gradient_color(rl)])
    resets_at = rl_data.get('resets_at')
    ts = fmt_reset(resets_at) if resets_at is not None else ''
    parts.append(f'{rc}{round(rl)}%{R}{DIM}{ts}{R}' if ts else f'{rc}{round(rl)}%{R}')

    # ── Threshold crossing logic ─────────────────────────────────────────────
    try:
        rk = str(int(float(resets_at))) if resets_at is not None else 'unknown'
    except Exception:
        rk = 'unknown'
    # Namespace all per-window state keys by model family so Sonnet and Opus
    # thresholds don't interfere with each other.
    lk     = f'{model_family}_{key}_logged'
    rk_key = f'{model_family}_{key}_last_rk'
    logged = (rebuilt.get(key, {}) if rebuilt else state.get(lk, {}))

    # Re-arm all thresholds when the reset window rolls over (new resets_at).
    # Without this, a disarmed flag from the old window suppresses crossings
    # in the new window until the rate first drops below the threshold.
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
                mk = monthly_5h_name if key == 'five_hour' else monthly_7d_name
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

if state_dirty:
    safe_write_json(state_file, state)

# ── Cost ─────────────────────────────────────────────────────────────────────
if cost_usd and cost_usd > 0:
    parts.append(f'{GOLD}\u0024{cost_usd:.2f}{R}')

# ── Monthly crossing counters (per model family) ─────────────────────────────
fh = state.get(monthly_5h_name, 0)
sd = state.get(monthly_7d_name, 0)
dc = fg(GRADIENT[min(int(fh / 30 * 19), 19)])
wc = fg(GRADIENT[min(int(sd / 4 * 19), 19)])
parts.append(f'{dc}{fh}x{R}{DIM}/{R}{wc}{sd}x{R}')

print(SEP.join(parts), end='')
" <<< "$(cat)"
