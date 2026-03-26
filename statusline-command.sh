#!/usr/bin/env bash
# Claude Code status line — rainbow heat bar + cost + lines changed

PYTHONIOENCODING=utf-8 python -c "
import sys, json

data = json.load(sys.stdin)

model = data.get('model', {}).get('display_name', 'Claude')
cw = data.get('context_window', {})
used_pct = cw.get('used_percentage')
cw_size = cw.get('context_window_size', 0)
cost_data = data.get('cost', {})
cost_usd = cost_data.get('total_cost_usd')
lines_add = cost_data.get('total_lines_added')
lines_rem = cost_data.get('total_lines_removed')

R = '\033[0m'
DIM = '\033[2m'
BOLD = '\033[1m'
GREEN = '\033[38;5;114m'
RED = '\033[38;5;203m'
GOLD = '\033[38;5;220m'
SEP = f' {DIM}\u2502{R} '

# Short model names keyed by model ID, with fallback
model_id = data.get('model', {}).get('id', '')
SHORT = {
    'claude-opus-4-6':        'Op4.6',
    'claude-opus-4-5':        'Op4.5',
    'claude-sonnet-4-6':      'So4.6',
    'claude-sonnet-4-5':      'So4.5',
    'claude-sonnet-4-0':      'So4',
    'claude-haiku-4-5':       'Ha4.5',
    'claude-haiku-3-5':       'Ha3.5',
}
# Match on prefix (IDs often have date suffixes like -20251001)
m = model  # fallback to display_name
for prefix, short in SHORT.items():
    if model_id.startswith(prefix):
        m = short
        break
else:
    # Generic fallback: strip 'Claude', parentheticals, keep first 6 chars
    import re
    m = re.sub(r'^Claude\s+', '', m)
    m = re.sub(r'\s*\(.*?\)', '', m).strip()[:6]

# Context window size
if cw_size >= 1_000_000:
    sz = f'{cw_size // 1_000_000}M'
elif cw_size >= 1_000:
    sz = f'{cw_size // 1_000}k'
else:
    sz = ''

model_label = f'{BOLD}{m} {sz}{R}' if sz else f'{BOLD}{m}{R}'

# Gradient: cool cyan -> green -> yellow -> orange -> red -> magenta
gradient = [
    51, 50, 49, 48, 47, 83, 119, 155, 191, 227,
    226, 220, 214, 208, 202, 196, 197, 198, 199, 200,
]

def fg(c): return f'\033[38;5;{c}m'

parts = [model_label]

if used_pct is not None:
    total = 20
    fill_exact = used_pct / 100 * total
    full = int(fill_exact)
    frac = fill_exact - full
    partials = [' ', '\u258f', '\u258e', '\u258d', '\u258c', '\u258b', '\u258a', '\u2589', '\u2588']

    bar = ''
    for i in range(total):
        color = fg(gradient[i])
        if i < full:
            bar += f'{color}\u2588'
        elif i == full:
            bar += f'{color}{partials[int(frac * 8)]}'
        else:
            bar += f'{DIM}\u2500'
    bar += R

    tip = min(full, total - 1)
    pc = fg(gradient[tip])
    parts.append(f'{bar} {pc}{used_pct:.1f}%{R}')

    # Rate limits with reset times
    from datetime import datetime
    def fmt_reset(epoch):
        t = datetime.fromtimestamp(epoch)
        now = datetime.now()
        h = t.hour % 12 or 12
        ap = t.strftime('%p').lower()
        time_s = str(h) + ap
        if t.date() != now.date():
            day = t.strftime('%a').lower()
            return day + ' ' + time_s
        return time_s

    # Rate limit exceedance logging
    import os
    state_file = os.path.expanduser('~/.claude/statusline-state.json')
    log_file = os.path.expanduser('~/.claude/rate-limit-log.jsonl')
    try:
        with open(state_file) as f: state = json.load(f)
    except Exception: state = {}

    for key in ['five_hour', 'seven_day']:
        rl_data = data.get('rate_limits', {}).get(key, {})
        rl = rl_data.get('used_percentage')
        if rl is not None:
            ri = min(int(rl / 100 * (total - 1)), total - 1)
            rc = fg(gradient[ri])
            resets_at = rl_data.get('resets_at')
            if resets_at:
                ts = fmt_reset(resets_at)
                parts.append(f'{rc}{rl:.0f}% {DIM}{ts}{R}')
            else:
                parts.append(f'{rc}{rl:.0f}%{R}')

            # Log upward crossings at 30%, 55%, 75% — each independently armed
            for thresh in [30, 55, 75]:
                armed_key = key + '_armed_' + str(thresh)
                armed = state.get(armed_key, True)  # armed by default
                if rl >= thresh and armed:
                    entry = json.dumps({'ts': datetime.now().isoformat(), 'window': key, 'pct': rl, 'threshold': thresh})
                    try:
                        with open(log_file, 'a') as lf: lf.write(entry + '\n')
                    except Exception: pass
                    state[armed_key] = False  # disarm until reset
                elif rl < thresh and not armed:
                    state[armed_key] = True  # re-arm
            state[key] = rl

    try:
        with open(state_file, 'w') as f: json.dump(state, f)
    except Exception: pass

# Session cost
if cost_usd is not None and cost_usd > 0:
    parts.append(f'{GOLD}\u0024{cost_usd:.2f}{R}')

# Lines changed
if lines_add is not None and lines_rem is not None and (lines_add > 0 or lines_rem > 0):
    parts.append(f'{GREEN}+{lines_add}{R}{DIM}/{R}{RED}-{lines_rem}{R}')

# Threshold crossing counts from log
try:
    import os
    from datetime import datetime as dt2
    log_file = os.path.expanduser('~/.claude/rate-limit-log.jsonl')
    now = dt2.now()
    month_prefix = now.strftime('%Y-%m')
    five_h_crosses = 0
    seven_d_crosses = 0
    try:
        with open(log_file) as lf:
            for line in lf:
                e = json.loads(line)
                ts = e.get('ts', '')
                if not ts.startswith(month_prefix):
                    continue
                if e.get('window') == 'five_hour':
                    five_h_crosses += 1
                elif e.get('window') == 'seven_day':
                    seven_d_crosses += 1
    except FileNotFoundError:
        pass
    di = min(int(five_h_crosses / 30 * (len(gradient) - 1)), len(gradient) - 1)
    wi = min(int(seven_d_crosses / 4 * (len(gradient) - 1)), len(gradient) - 1)
    dc = fg(gradient[di])
    wc = fg(gradient[wi])
    parts.append(f'{dc}\u2191{five_h_crosses}{R}{DIM}/{R}{wc}\u2191{seven_d_crosses}{R}')
except Exception:
    pass

print(SEP.join(parts), end='')
" <<< "$(cat)"
