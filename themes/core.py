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
    mn = t.minute
    ap = ('A' if uppercase else 'a') if t.hour < 12 else ('P' if uppercase else 'p')
    # Anthropic 5h windows start from first request, so they end mid-hour.
    # Always show minutes — dropping them silently rounds the real reset time.
    time_s = f'{h}:{mn:02d}{ap}'
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
# Parse `claude-<family>-<major>-<minor>` programmatically so new versions
# (opus-4-7, sonnet-5-0) and even new families (e.g. mythos) render without
# code changes. Known families get a curated 2-char prefix; unknown families
# derive one from their name.
_FAMILY_MAP = {
    'opus':   ('Op', 'Opus'),
    'sonnet': ('Sn', 'Sonnet'),
    'haiku':  ('Hk', 'Haiku'),
}
_MODEL_RE = re.compile(r'^claude-([a-z]+)-(\d+)-(\d+)')

def _abbreviate_model(model_id, display_name, fmt):
    """Return model name in requested format: 'short', 'long', or 'full'.

    Derives short/long names from the model id via regex, so any future
    `claude-<family>-<major>-<minor>` id works without a patch. Convention:
    when minor is 0, drop it (`Sn4`, `Sonnet 4` — not `Sn40`/`Sonnet 4.0`).
    For unknown families the short prefix is the first two letters of the
    family name capitalized (e.g. mythos → `My51`, `Mythos 5.1`).
    """
    if fmt == 'full':
        return display_name

    m = _MODEL_RE.match(model_id) if model_id else None
    if m:
        family, major, minor = m.group(1), m.group(2), m.group(3)
        if family in _FAMILY_MAP:
            short_prefix, long_name = _FAMILY_MAP[family]
        else:
            short_prefix = family[:2].capitalize() if family else '??'
            long_name = family.capitalize() if family else 'Claude'
        if minor == '0':
            return f'{short_prefix}{major}' if fmt == 'short' else f'{long_name} {major}'
        if fmt == 'short':
            return f'{short_prefix}{major}{minor}'
        return f'{long_name} {major}.{minor}'

    # Malformed id — fall back to parsing the display name
    name = re.sub(r'^Claude\s+', '', display_name)
    name = re.sub(r'\s*\(.*?\)', '', name).strip()
    if fmt == 'short':
        return name[:5]
    return name

# ── Account discovery ───────────────────────────────────────────────────────
_cached_account = None  # account never changes within a process lifetime

def _find_claude_account():
    global _cached_account
    if _cached_account is not None:
        return _cached_account
    cfg_dir = os.environ.get('CLAUDE_CONFIG_DIR') or os.path.expanduser('~/.claude')
    candidates = [
        os.path.join(cfg_dir, '.claude.json'),
        os.path.join(os.path.dirname(cfg_dir.rstrip(os.sep).rstrip('/')), '.claude.json'),
    ]
    result = ''
    for p in candidates:
        try:
            with open(p, 'r', encoding='utf-8') as f:
                txt = f.read()
            mo = re.search(r'"emailAddress"\s*:\s*"([^"]+)"', txt)
            if mo:
                result = mo.group(1)
                break
        except Exception:
            continue
    _cached_account = result
    return result

# ── Git info ────────────────────────────────────────────────────────────────
def _collect_git(cwd):
    """Collect all git state. Returns a dict; empty if not in a git repo."""
    git = {
        'branch': '', 'detached': False, 'dirty': 0,
        'ahead': 0, 'behind': 0, 'stash': 0,
        'remote_short': '', 'worktree': '',
        'operation': '', 'repo_name': '',
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

    # Repo name from toplevel directory
    toplevel = _run(['git', 'rev-parse', '--show-toplevel'])
    if toplevel:
        git['repo_name'] = os.path.basename(os.path.normpath(toplevel))

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
    if u.startswith('ssh://'):
        # ssh://[user@]host[:port]/owner/repo — split on first '/' after stripping user@
        s = u[6:]  # strip 'ssh://'
        if '@' in s:
            s = s.split('@', 1)[1]  # strip user@
        if '/' in s:
            host, path = s.split('/', 1)
            host = host.split(':', 1)[0]  # strip optional :port
    elif u.startswith('git@'):
        # git@host:owner/repo (SCP syntax — no port)
        s = u[4:]
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
    host = host.split(':', 1)[0]  # defensive strip of any remaining :port
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
                    if rl_i >= 50 or secs_left <= 1800:  # 30 minutes
                        ts = formatter(resets_at)
                else:
                    if rl_i >= 80 or secs_left <= 43200:  # 12 hours
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

        if state_lost or rk != state.get(rk_key):
            # New reset window detected — re-arm all thresholds
            for th in THRESHOLDS:
                state[f'{model_family}_{key}_armed_{th}'] = True
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
                dirty = True
            elif rl < th and not armed:
                state[ak] = True
                dirty = True

        if len(logged) > 10:
            for k in sorted(logged.keys())[:-10]:
                del logged[k]
        prev_logged = state.get(lk, {})
        if logged != prev_logged:
            state[lk] = logged
            dirty = True
        prev_rl = state.get(key)
        if prev_rl != rl:
            state[key] = rl
            dirty = True

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
def _rotate_log(state):
    """Trim old entries from the rate-limit log. Returns True if state was mutated.

    Skips the full read-parse-rewrite cycle unless:
      - File exceeds 4096 bytes, AND
      - At least 300 seconds have passed since the last rotation.
    """
    try:
        if not (os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 4096):  # 4 KB threshold
            return False
        now_ts = datetime.now().timestamp()
        last = state.get('last_rotation_ts', 0)
        if now_ts - last < 300:  # 5-minute cooldown between rotations
            return False
        cutoff = (datetime.now() - timedelta(days=60)).isoformat()  # 60-day retention window
        with open(LOG_FILE) as f:
            lines = f.readlines()
        kept = []
        for ln in lines:
            try:
                if json.loads(ln).get('ts', '') >= cutoff:
                    kept.append(ln)
            except Exception:
                pass
        if len(kept) < len(lines):
            with open(LOG_FILE, 'w') as f:
                f.writelines(kept)
        state['last_rotation_ts'] = now_ts
        return True
    except Exception:
        return False

# ── Main entry point ────────────────────────────────────────────────────────
def build_context(data=None):
    """Read stdin JSON (or accept pre-parsed dict), collect all state, return a context dict for themes."""
    if data is None:
        try:
            data = json.load(sys.stdin)
        except Exception:
            # Return a minimal safe fallback so themes can render a degraded statusline
            return {
                'error': True,
                'model_name': '???', 'model_id': '', 'model_family': 'sonnet',
                'model_display': 'Claude',
                'cw_size': 0, 'cw_str': '', 'used_pct': None,
                'cwd': '', 'path_display': '',
                'email': '', 'user_short': '',
                'effort': None,
                'rate_limits': [],
                'session_dur': '0s', 'session_elapsed': 0,
                'git': {
                    'branch': '', 'detached': False, 'dirty': 0,
                    'ahead': 0, 'behind': 0, 'stash': 0,
                    'remote_short': '', 'worktree': '', 'operation': '',
                },
                'config': dict(DEFAULT_CONFIG),
            }

    model_display = data.get('model', {}).get('display_name', 'Claude')
    model_id = data.get('model', {}).get('id', '')

    # Extract family from `claude-<family>-<major>-<minor>` so unknown
    # families (e.g. mythos) flow through instead of being forced to sonnet.
    _fm = _MODEL_RE.match(model_id) if model_id else None
    if _fm:
        model_family = _fm.group(1)
    elif 'opus'  in model_id: model_family = 'opus'
    elif 'haiku' in model_id: model_family = 'haiku'
    else:                     model_family = 'sonnet'

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

    # Rate limits — cache in state so models that don't report (Sonnet) still show the shared pools
    rl_raw = data.get('rate_limits', {})
    if rl_raw:
        state['_cached_rate_limits'] = rl_raw
        state_dirty = True
    else:
        rl_raw = state.get('_cached_rate_limits', {})
        if rl_raw:
            data = {**data, 'rate_limits': rl_raw}
    rate_limits, rl_dirty = _process_rate_limits(data, model_family, state, state_lost, rebuilt, config)
    state_dirty = state_dirty or rl_dirty

    # Session
    session_dur, session_elapsed, sess_dirty = _track_session(data, state)
    state_dirty = state_dirty or sess_dirty

    # Git
    git = _collect_git(cwd)

    # Path
    path_display = _truncate_path(cwd) if cwd else ''

    # Effort — Claude Code 2.1.119+ wraps it as {"level": "..."}; older versions sent a bare string
    effort = data.get('effort')
    if isinstance(effort, dict):
        effort = effort.get('level')

    # Persist
    if _rotate_log(state):
        state_dirty = True
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


# ── Standard render ────────────────────────────────────────────────────────
#
# Shared two-line statusline layout used by themes with the standard structure.
# Themes supply a config dict describing colors, gradients, separators, and
# optional hooks for the pieces that differ.
#
# Required theme config keys:
#   sep          - separator string between line 1 parts
#   colors       - dict mapping semantic names to xterm-256 color ints:
#                    user, effort, duration, empty_bar, rl_label, rl_reset,
#                    operation, worktree, branch, detached, remote_arrow,
#                    remote, ahead, behind, dirty, stash, path
#   grad         - list of 20 ints: context bar + rate limit gradient
#   tier         - dict mapping model family -> color int  (opus/sonnet/haiku)
#   tier_default - fallback tier color int
#
# Optional theme config keys:
#   rl_grad      - separate 20-int gradient for rate limits (defaults to grad)
#   bar_n        - bar cell count (default 10)
#   text_xform   - callable(str) -> str applied to most display text
#   user_chip    - callable(text, theme) -> str for user display
#   model_chip   - callable(label, tier_color, theme) -> str for model
#   bar_fn       - callable(used_pct, theme) -> str for the full bar + pct
#   rl_fn        - callable(rl, theme) -> str for one rate limit entry
#   line2_prefix - str prepended to line 2 (after a space)
#   line2_join   - callable(parts, theme) -> str to join line 2 parts
#                  (default: ' '.join)
#   line2_path_sep - str separator between git info and path on line 2
#                    (default: ' ', same as between git parts)

def _std_grad_color(pct, grad):
    """Look up a gradient color by percentage (0-100)."""
    return grad[min(int(pct / 100 * 19), 19)]


def _std_bar(used_pct, theme):
    """Default context bar: 4-level Unicode block fill with gradient colors."""
    N = theme.get('bar_n', 10)
    grad = theme['grad']
    xf = theme.get('text_xform')
    empty_c = theme['colors']['empty_bar']
    fill = used_pct / 100 * N
    bar = ''
    # Map bar cells to gradient: evenly space N cells across 20-entry gradient
    step = max(1, (len(grad) - 1) // max(N - 1, 1))
    for i in range(N):
        c = grad[min(i * step, len(grad) - 1)]
        cell = fill - i
        if cell >= 1.0:    bar += f'{fg(c)}\u2588'
        elif cell >= 0.75: bar += f'{fg(c)}\u2593'
        elif cell >= 0.5:  bar += f'{fg(c)}\u2592'
        elif cell >= 0.25: bar += f'{fg(c)}\u2591'
        else:              bar += f'{fg(empty_c)}\u2500'
    bar += R
    pc = _std_grad_color(used_pct, grad)
    pct_s = f'{int(round(used_pct))}%'
    if xf:
        pct_s = xf(pct_s)
    return f'{bar}  {fg(pc)}{pct_s}{R}'


def _phosphor_rl(rl, theme):
    """Rate limit formatting for phosphor CRT themes."""
    colors = theme['colors']
    xf = theme.get('text_xform')
    label = rl['label']
    pct = rl['pct']
    if xf:
        label = xf(label)
    if pct is None:
        return ''
    if pct >= 80:   ic = colors['bar_bright']
    elif pct >= 50: ic = colors['bar_normal']
    elif pct >= 20: ic = colors['bar_dim']
    else:           ic = colors['bar_faint']
    ts = rl['reset_str']
    if xf and ts:
        ts = xf(ts)
    if ts:
        return f'{fg(colors["rl_label"])}{label} {fg(ic)}{pct}%{fg(colors["rl_reset"])}@{ts}{R}'
    return f'{fg(colors["rl_label"])}{label} {fg(ic)}{pct}%{R}'


def _phosphor_bar(used_pct, theme):
    """Phosphor CRT bar: 3-level intensity fill with position-based brightness.

    Requires theme colors: bar_bright, bar_normal, bar_dim, bar_faint, empty_bar.
    """
    N = theme.get('bar_n', 10)
    colors = theme['colors']
    xf = theme.get('text_xform')
    fill = used_pct / 100 * N
    bar = ''
    for i in range(N):
        cell = fill - i
        if cell >= 1.0:
            if i >= 8:    bar += f'{fg(colors["bar_bright"])}\u2588'
            elif i >= 5:  bar += f'{fg(colors["bar_normal"])}\u2588'
            else:         bar += f'{fg(colors["bar_dim"])}\u2588'
        elif cell >= 0.5: bar += f'{fg(colors["bar_dim"])}\u2593'
        elif cell >= 0.25:bar += f'{fg(colors["bar_faint"])}\u2591'
        else:             bar += f'{fg(colors["empty_bar"])}\u2500'
    bar += R
    pct = int(round(used_pct))
    # Phosphor intensity for percentage display
    if pct >= 80:   pc = colors['bar_bright']
    elif pct >= 50: pc = colors['bar_normal']
    elif pct >= 20: pc = colors['bar_dim']
    else:           pc = colors['bar_faint']
    pct_s = f'{pct}%'
    if xf:
        pct_s = xf(pct_s)
    return f'{bar}  {fg(pc)}{pct_s}{R}'


def _std_rl(rl, theme):
    """Default rate limit entry formatting."""
    colors = theme['colors']
    rl_grad = theme.get('rl_grad', theme['grad'])
    xf = theme.get('text_xform')
    label = rl['label']
    pct = rl['pct']
    if xf:
        label = xf(label)
    if pct is None:
        return ''
    rc = _std_grad_color(pct, rl_grad)
    ts = rl['reset_str']
    if xf and ts:
        ts = xf(ts)
    if ts:
        return f'{fg(colors["rl_label"])}{label} {fg(rc)}{pct}%{fg(colors["rl_reset"])}@{ts}{R}'
    return f'{fg(colors["rl_label"])}{label} {fg(rc)}{pct}%{R}'


def render_standard(ctx, theme):
    """Render the standard two-line statusline using a theme config dict.

    Returns the same format as any theme's render(): a one- or two-line string.
    """
    config = ctx['config']
    used_pct = ctx['used_pct']
    colors = theme['colors']
    xf = theme.get('text_xform')
    tier_color = theme['tier'].get(ctx['model_family'], theme['tier_default'])

    parts = []

    # User
    if config.get('show_user', True) and ctx['user_short']:
        user_chip_fn = theme.get('user_chip')
        if user_chip_fn:
            parts.append(user_chip_fn(ctx['user_short'], theme))
        else:
            text = xf(ctx['user_short']) if xf else ctx['user_short']
            parts.append(f'{BOLD}{fg(colors["user"])}{text}{R}')

    # Model + context window size
    m = xf(ctx['model_name']) if xf else ctx['model_name']
    sz = ctx['cw_str']
    label = f'{m} {sz}' if sz else m
    model_chip_fn = theme.get('model_chip')
    if model_chip_fn:
        parts.append(model_chip_fn(label, tier_color, theme))
    else:
        parts.append(f'{BOLD}{fg(tier_color)}{label}{R}')

    # Effort
    if ctx['effort']:
        parts.append(f'{fg(colors["effort"])}{ctx["effort"]}{R}')

    # Context bar
    if used_pct is not None:
        bar_fn = theme.get('bar_fn', _std_bar)
        parts.append(bar_fn(used_pct, theme))

    # Rate limits — formatters return '' for windows with no data (e.g. Sonnet has no 5h window)
    rl_fn = theme.get('rl_fn', _std_rl)
    for rl in ctx['rate_limits']:
        s = rl_fn(rl, theme)
        if s:
            parts.append(s)

    # Session duration
    dur = xf(ctx['session_dur']) if xf else ctx['session_dur']
    parts.append(f'{fg(colors["duration"])}{dur}{R}')

    line1 = theme['sep'].join(parts)

    # ── Line 2 ──────────────────────────────────────────────────────────────
    git = ctx['git']
    l2 = []
    if git['operation']:
        op = git['operation']  # already uppercase from core
        op_chip_fn = theme.get('op_chip')
        if op_chip_fn:
            l2.append(op_chip_fn(op, theme))
        else:
            l2.append(f'{BOLD}{fg(colors["operation"])}{op}{R}')
    if git['worktree']:
        wt = xf(git['worktree']) if xf else git['worktree']
        l2.append(f'{fg(colors["worktree"])}[{wt}]{R}')
    if git['branch']:
        br = xf(git['branch']) if xf else git['branch']
        det_suffix = theme.get('det_suffix', ' DET' if xf else ' det')
        det_bold = BOLD if theme.get('detached_bold') else ''
        br_bold = BOLD if theme.get('branch_bold') else ''
        if git['detached']:
            l2.append(f'{det_bold}{fg(colors["detached"])}{br}{det_suffix}{R}')
        else:
            l2.append(f'{br_bold}{fg(colors["branch"])}{br}{R}')
        if git['remote_short']:
            rem = xf(git['remote_short']) if xf else git['remote_short']
            l2.append(f'{fg(colors["remote_arrow"])}\u2192{fg(colors["remote"])}{rem}{R}')
        ahead_ch = theme.get('ahead_char', '\u2191')
        behind_ch = theme.get('behind_char', '\u2193')
        ab = ''
        if git['ahead']:
            ab += f'{fg(colors["ahead"])}{ahead_ch}{git["ahead"]}{R}'
        if git['behind']:
            ab += f'{fg(colors["behind"])}{behind_ch}{git["behind"]}{R}'
        if ab:
            l2.append(ab)
    if git['dirty']:
        l2.append(f'{fg(colors["dirty"])}+{git["dirty"]}{R}')
    if git['stash']:
        l2.append(f'{fg(colors["stash"])}\u2691{git["stash"]}{R}')

    path = ctx['path_display']
    if xf and path:
        path = xf(path)
    path_str = f'{fg(colors["path"])}{path}{R}' if path else ''

    # Join git parts, then optionally separate path with a different separator
    line2_join = theme.get('line2_join')
    path_sep = theme.get('line2_path_sep')
    if line2_join:
        if path_str:
            l2.append(path_str)
        line2 = line2_join(l2, theme)
    elif path_sep and path_str:
        git_str = ' '.join(l2) if l2 else ''
        line2_parts = [p for p in [git_str, path_str] if p]
        line2 = path_sep.join(line2_parts)
    else:
        if path_str:
            l2.append(path_str)
        line2 = ' '.join(l2) if l2 else ''

    prefix = theme.get('line2_prefix', '')
    if prefix and line2:
        line2 = prefix + line2

    return f'{line1}\n{line2}' if line2 else line1
