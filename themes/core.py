"""Shared statusline core — parsing, storage, git info, rate limits, session tracking.

Themes import `build_context()` which returns a dict with everything needed to render.
"""

import sys
import json
import os
import re
import tempfile
import subprocess
from datetime import datetime, timedelta

# ── ANSI helpers (shared across themes) ─────────────────────────────────────
R    = '\033[0m'
DIM  = '\033[2m'
BOLD = '\033[1m'

def fg(c):
    return f'\033[38;5;{c}m'

def bg(c):
    return f'\033[48;5;{c}m'

# ── Storage ─────────────────────────────────────────────────────────────────
_claude_dir = os.path.expanduser('~/.claude')
os.makedirs(_claude_dir, exist_ok=True)
STATE_FILE = os.path.join(_claude_dir, 'statusline-state.json')
LOG_FILE   = os.path.join(_claude_dir, 'rate-limit-log.jsonl')
CONFIG_FILE = os.path.join(_claude_dir, 'statusline-config.json')

def safe_read_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except Exception:
        return {}

def safe_write_json(path, obj):
    try:
        fd, tmp = tempfile.mkstemp(dir=_claude_dir, suffix='.tmp', prefix='sl_')
        os.close(fd)
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(obj, f)
            os.replace(tmp, path)
        except Exception:
            try: os.unlink(tmp)
            except Exception: pass
    except Exception:
        pass

def safe_append_line(path, line):
    try:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass

# ── Config (user preferences from /statusline skill) ───────────────────────
DEFAULT_CONFIG = {
    'model_format': 'short',     # 'short', 'long', 'full'
    'show_user': True,
    'date_format': 'short',      # 'short', 'long'
    'auto_hide_reset': True,
}

def load_config():
    cfg = dict(DEFAULT_CONFIG)
    user = safe_read_json(CONFIG_FILE)
    for k in DEFAULT_CONFIG:
        if k in user:
            cfg[k] = user[k]
    return cfg

# ── Rate limit log helpers ──────────────────────────────────────────────────
THRESHOLDS = [95]

def _rebuild_logged_windows(log_path, family=None):
    result = {'five_hour': {}, 'seven_day': {}}
    try:
        with open(log_path, encoding='utf-8') as f:
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

def fmt_reset(epoch, day_only=False, uppercase=False):
    """Format a reset timestamp as a compact time string."""
    try:
        t = datetime.fromtimestamp(float(epoch))
    except Exception:
        return ''
    now = datetime.now()
    if t <= now:
        return ''
    if uppercase:
        days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
    else:
        days = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
    h = t.hour % 12 or 12
    ap = ('A' if uppercase else 'a') if t.hour < 12 else ('P' if uppercase else 'p')
    time_s = f'{h}{ap}'
    if t.date() != now.date():
        if day_only:
            return days[t.weekday()]
        return f'{days[t.weekday()]}{time_s}'
    if day_only:
        return ''
    return time_s

def fmt_reset_long(epoch, day_only=False, uppercase=False):
    """Longer format for reset times."""
    try:
        t = datetime.fromtimestamp(float(epoch))
    except Exception:
        return ''
    now = datetime.now()
    if t <= now:
        return ''
    if uppercase:
        days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
    else:
        days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    h = t.hour % 12 or 12
    mn = t.minute
    ap = ('AM' if uppercase else 'am') if t.hour < 12 else ('PM' if uppercase else 'pm')
    time_s = f'{h}:{mn:02d}{ap}'
    if t.date() != now.date():
        if day_only:
            return days[t.weekday()]
        return f'{days[t.weekday()]} {time_s}'
    if day_only:
        return ''
    return time_s

# ── Model abbreviation ──────────────────────────────────────────────────────
_SHORT = {
    'claude-opus-4-6': 'Op46', 'claude-opus-4-5': 'Op45',
    'claude-sonnet-4-6': 'Sn46', 'claude-sonnet-4-5': 'Sn45', 'claude-sonnet-4-0': 'Sn4',
    'claude-haiku-4-5': 'Hk45', 'claude-haiku-3-5': 'Hk35',
}
_LONG = {
    'claude-opus-4-6': 'Opus 4.6', 'claude-opus-4-5': 'Opus 4.5',
    'claude-sonnet-4-6': 'Sonnet 4.6', 'claude-sonnet-4-5': 'Sonnet 4.5', 'claude-sonnet-4-0': 'Sonnet 4',
    'claude-haiku-4-5': 'Haiku 4.5', 'claude-haiku-3-5': 'Haiku 3.5',
}

def _abbreviate_model(model_id, display_name, fmt):
    """Return model name in requested format: 'short', 'long', or 'full'."""
    if fmt == 'full':
        return display_name
    table = _SHORT if fmt == 'short' else _LONG
    for prefix, short in table.items():
        if model_id.startswith(prefix):
            return short
    # Fallback
    m = re.sub(r'^Claude\s+', '', display_name)
    m = re.sub(r'\s*\(.*?\)', '', m).strip()
    if fmt == 'short':
        return m[:5]
    return m

# ── Account discovery ───────────────────────────────────────────────────────
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
            mo = re.search(r'"emailAddress"\s*:\s*"([^"]+)"', txt)
            if mo:
                return mo.group(1)
        except Exception:
            continue
    return ''

# ── Git info ────────────────────────────────────────────────────────────────
def _collect_git(cwd):
    """Collect all git state. Returns a dict; empty if not in a git repo."""
    git = {
        'branch': '', 'detached': False, 'dirty': 0,
        'ahead': 0, 'behind': 0, 'stash': 0,
        'remote_short': '', 'worktree': '',
        'operation': '',
    }

    def _run(args):
        try:
            return subprocess.check_output(
                args, cwd=cwd or None, stderr=subprocess.DEVNULL, timeout=2
            ).decode('utf-8', errors='replace').strip()
        except Exception:
            return ''

    br = _run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
    if not br:
        return git

    det = (br == 'HEAD')
    if det:
        sha = _run(['git', 'rev-parse', '--short', 'HEAD'])
        br = sha or br
    git['branch'] = br
    git['detached'] = det

    # Remote tracking
    if br and not det:
        ups = _run(['git', 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{upstream}'])
        if ups and '/' in ups:
            rem, rbr = ups.split('/', 1)
            rurl = _run(['git', 'remote', 'get-url', rem])
            hs, own = _parse_remote(rurl) if rurl else ('', '')
            if hs and own:
                git['remote_short'] = f'{hs}:{own}' if rbr == br else f'{hs}:{own}#{rbr}'
            else:
                git['remote_short'] = rem if rbr == br else ups
        else:
            # No upstream configured — signal "local only" so themes can display it
            git['remote_short'] = 'local'

        # Ahead/behind
        ab = _run(['git', 'rev-list', '--left-right', '--count', 'HEAD...@{upstream}'])
        parts = ab.split()
        if len(parts) == 2:
            git['ahead'], git['behind'] = int(parts[0]), int(parts[1])

    # Git dir info (worktree, operations, stash)
    gd_raw = _run(['git', 'rev-parse', '--git-dir', '--git-common-dir'])
    lines = gd_raw.split('\n')
    gitdir_rel = lines[0] if len(lines) >= 1 else ''
    common_rel = lines[1] if len(lines) >= 2 else gitdir_rel

    def _abs(gd):
        if not gd:
            return ''
        return gd if os.path.isabs(gd) else os.path.abspath(os.path.join(cwd or '.', gd))

    gd = _abs(gitdir_rel)
    cgd = _abs(common_rel)

    # Worktree
    if gd and cgd and os.path.normpath(gd) != os.path.normpath(cgd):
        git['worktree'] = os.path.basename(os.path.normpath(gd))

    # Operation
    if gd:
        for check, label in [
            (['rebase-merge'], 'REBASE'), (['rebase-apply'], 'REBASE'),
            (['MERGE_HEAD'], 'MERGE'), (['CHERRY_PICK_HEAD'], 'PICK'),
            (['REVERT_HEAD'], 'REVERT'), (['BISECT_LOG'], 'BISECT'),
        ]:
            if os.path.exists(os.path.join(gd, check[0])):
                git['operation'] = label
                break

    # Stash
    if cgd:
        try:
            sl = os.path.join(cgd, 'logs', 'refs', 'stash')
            if os.path.exists(sl):
                with open(sl, encoding='utf-8') as f:
                    git['stash'] = sum(1 for _ in f)
        except Exception:
            pass

    # Dirty
    gs = _run(['git', 'status', '--porcelain'])
    git['dirty'] = len(gs.splitlines()) if gs else 0

    return git

def _parse_remote(url):
    u = url.strip()
    if u.endswith('.git'):
        u = u[:-4]
    host, path = '', ''
    if u.startswith('git@') or (u.startswith('ssh://') and '@' in u):
        s = u[6:] if u.startswith('ssh://') else u[4:]
        if '@' in s:
            s = s.split('@', 1)[1]
        if ':' in s:
            host, path = s.split(':', 1)
        elif '/' in s:
            host, path = s.split('/', 1)
    elif '://' in u:
        s = u.split('://', 1)[1]
        if '@' in s.split('/', 1)[0]:
            s = s.split('@', 1)[1]
        if '/' in s:
            host, path = s.split('/', 1)
    host = host.split(':', 1)[0]
    hs = {'github.com': 'gh', 'gitlab.com': 'gl', 'bitbucket.org': 'bb'}.get(
        host, host.split('.', 1)[0] if host else '')
    owner = path.split('/', 1)[0] if path else ''
    return hs, owner

# ── Path truncation ─────────────────────────────────────────────────────────
def _truncate_path(cwd, max_len=75):
    norm = cwd.replace(os.sep, '/')
    if len(norm) <= max_len:
        return norm
    if len(norm) >= 3 and norm[1] == ':' and norm[2] == '/':
        drive = norm[:3]
        rest = norm[3:]
    else:
        drive = ''
        rest = norm
    segs = rest.split('/')
    first_abbrev = segs[0][:2] if segs else ''
    prefix = f'{drive}{first_abbrev}...'
    budget = max_len - len(prefix)
    tail_parts = []
    for seg in reversed(segs[1:]):
        candidate = '/' + seg
        needed = len(candidate) + sum(len(p) for p in tail_parts)
        if needed > budget and tail_parts:
            break
        tail_parts.insert(0, candidate)
    return prefix + ''.join(tail_parts)

# ── Rate limit processing ──────────────────────────────────────────────────
def _process_rate_limits(data, model_family, state, state_lost, rebuilt, config):
    """Process rate limits. Returns (rl_info_list, state_dirty).

    Each item in rl_info_list:
        {'key': 'five_hour', 'label': '5h', 'pct': 42, 'reset_str': '3p', 'resets_at': epoch}
    """
    auto_hide = config.get('auto_hide_reset', True)
    use_long_fmt = config.get('date_format') == 'long'
    formatter = fmt_reset_long if use_long_fmt else fmt_reset

    results = []
    dirty = False

    for key in ['five_hour', 'seven_day']:
        label = '5h' if key == 'five_hour' else '7d'
        rl_data = data.get('rate_limits', {}).get(key, {})
        rl = rl_data.get('used_percentage')
        resets_at = rl_data.get('resets_at')

        info = {'key': key, 'label': label, 'pct': None, 'reset_str': '', 'resets_at': resets_at}

        if rl is None:
            results.append(info)
            continue

        rl_i = int(round(rl))
        info['pct'] = rl_i

        # Reset time display
        ts = ''
        if resets_at is not None:
            try:
                reset_dt = datetime.fromtimestamp(float(resets_at))
                secs_left = (reset_dt - datetime.now()).total_seconds()
            except Exception:
                secs_left = float('inf')

            if auto_hide:
                if key == 'five_hour':
                    if rl_i >= 50 or secs_left <= 1800:
                        ts = formatter(resets_at)
                else:
                    if rl_i >= 80 or secs_left <= 43200:
                        ts = formatter(resets_at)
                    else:
                        ts = formatter(resets_at, day_only=True)
            else:
                # Always show reset time
                ts = formatter(resets_at)

        info['reset_str'] = ts
        results.append(info)

        # ── Threshold crossing logging (side effect, same for all themes) ──
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
            dirty = True
        state[rk_key] = rk
        dirty = True

        for th in THRESHOLDS:
            ak = f'{model_family}_{key}_armed_{th}'
            if state_lost:
                already = th in logged.get(rk, [])
                armed = not already if rl >= th else True
            else:
                armed = state.get(ak, True)

            if rl >= th and armed:
                if th not in logged.get(rk, []):
                    entry = json.dumps({'ts': datetime.now().isoformat(), 'model': model_family,
                                        'window': key, 'pct': rl, 'threshold': th, 'resets_at': rk})
                    safe_append_line(LOG_FILE, entry)
                    logged.setdefault(rk, []).append(th)
                state[ak] = False
            elif rl < th and not armed:
                state[ak] = True

        if len(logged) > 10:
            for k in sorted(logged.keys())[:-10]:
                del logged[k]
        state[lk] = logged
        state[key] = rl

    return results, dirty

# ── Session tracking ────────────────────────────────────────────────────────
def _track_session(data, state):
    now_ts = datetime.now().timestamp()
    sid = data.get('session_id', '')
    sess = state.get('session_start', {})
    dirty = False
    if sess.get('sid') != sid:
        sess = {'sid': sid, 'ts': now_ts}
        state['session_start'] = sess
        dirty = True
    elapsed = now_ts - sess.get('ts', now_ts)
    if elapsed >= 3600:
        dur = f'{int(elapsed // 3600)}h{int(elapsed % 3600 // 60):02d}m'
    elif elapsed >= 60:
        dur = f'{int(elapsed // 60)}m{int(elapsed % 60):02d}s'
    else:
        dur = f'{int(elapsed)}s'
    return dur, elapsed, dirty

# ── Log rotation ────────────────────────────────────────────────────────────
def _rotate_log():
    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 4096:
            cutoff = (datetime.now() - timedelta(days=60)).isoformat()
            with open(LOG_FILE, encoding='utf-8') as f:
                lines = f.readlines()
            kept = []
            for ln in lines:
                try:
                    if json.loads(ln).get('ts', '') >= cutoff:
                        kept.append(ln)
                except Exception:
                    pass
            if len(kept) < len(lines):
                with open(LOG_FILE, 'w', encoding='utf-8') as f:
                    f.writelines(kept)
    except Exception:
        pass

# ── Main entry point ────────────────────────────────────────────────────────
def build_context():
    """Read stdin JSON, collect all state, return a context dict for themes."""
    data = json.load(sys.stdin)

    model_display = data.get('model', {}).get('display_name', 'Claude')
    model_id = data.get('model', {}).get('id', '')

    if   'opus'   in model_id: model_family = 'opus'
    elif 'haiku'  in model_id: model_family = 'haiku'
    else:                       model_family = 'sonnet'

    cw = data.get('context_window', {})
    used_pct = cw.get('used_percentage')
    cw_size = cw.get('context_window_size', 0)
    cwd = data.get('cwd', '')

    config = load_config()

    # Model name
    model_name = _abbreviate_model(model_id, model_display, config['model_format'])
    cw_str = f'{cw_size // 1_000_000}M' if cw_size >= 1_000_000 else (
        f'{cw_size // 1_000}k' if cw_size >= 1_000 else '')

    # User
    email = _find_claude_account()
    user_short = (email.split('@', 1)[0] if email else '')[:2]

    # State
    state = safe_read_json(STATE_FILE)
    state_dirty = False
    state_lost = len(state) == 0
    rebuilt = _rebuild_logged_windows(LOG_FILE, model_family) if state_lost else None

    # Rate limits
    rate_limits, rl_dirty = _process_rate_limits(data, model_family, state, state_lost, rebuilt, config)
    state_dirty = state_dirty or rl_dirty

    # Session
    session_dur, session_elapsed, sess_dirty = _track_session(data, state)
    state_dirty = state_dirty or sess_dirty

    # Git
    git = _collect_git(cwd)

    # Path
    path_display = _truncate_path(cwd) if cwd else ''

    # Effort
    effort = data.get('effort')

    # Persist
    _rotate_log()
    if state_dirty:
        safe_write_json(STATE_FILE, state)

    return {
        'model_name': model_name,
        'model_id': model_id,
        'model_family': model_family,
        'model_display': model_display,
        'cw_size': cw_size,
        'cw_str': cw_str,
        'used_pct': used_pct,
        'cwd': cwd,
        'path_display': path_display,
        'email': email,
        'user_short': user_short,
        'effort': effort,
        'rate_limits': rate_limits,
        'session_dur': session_dur,
        'session_elapsed': session_elapsed,
        'git': git,
        'config': config,
    }
