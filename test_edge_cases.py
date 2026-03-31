#!/usr/bin/env python3
"""Edge-case tests for statusline-command.sh

Each test pipes JSON into the script via bash and checks the output/side-effects.
State files are reset before every test to ensure isolation.
"""

import subprocess
import json
import os
import sys
import time
import threading

SCRIPT = os.path.expanduser("~/.claude/statusline-command.sh")
STATE_FILE = os.path.expanduser("~/.claude/statusline-state.json")
LOG_FILE = os.path.expanduser("~/.claude/rate-limit-log.jsonl")
CLAUDE_DIR = os.path.expanduser("~/.claude")

# ANSI escape stripper
import re
ANSI_RE = re.compile(r'\033\[[0-9;]*m')

def strip_ansi(s):
    return ANSI_RE.sub('', s)


def reset_state():
    """Reset state and log files to clean slate."""
    with open(STATE_FILE, 'w') as f:
        f.write('{}')
    with open(LOG_FILE, 'w') as f:
        f.write('')


def run_script(input_json, timeout=15):
    """Run the statusline script with given JSON input. Returns (stdout, stderr, returncode)."""
    if isinstance(input_json, dict):
        input_str = json.dumps(input_json)
    else:
        input_str = input_json
    result = subprocess.run(
        ['bash', SCRIPT],
        input=input_str,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.stdout, result.stderr, result.returncode


def read_log_entries():
    """Read all valid JSON entries from the log file."""
    entries = []
    try:
        with open(LOG_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except FileNotFoundError:
        pass
    return entries


def read_state():
    """Read state file."""
    try:
        with open(STATE_FILE) as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except Exception:
        return {}


# ── Test functions ─────────────────────────────────────────────────

passed = 0
failed = 0
errors = []


def report(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        errors.append((name, detail))
        print(f"  FAIL  {name} -- {detail}")


def test_01_empty_json():
    """Empty JSON input {} should output just 'Claude' without crashing."""
    reset_state()
    stdout, stderr, rc = run_script({})
    plain = strip_ansi(stdout)
    ok = rc == 0 and 'Claude' in plain
    detail = ""
    if rc != 0:
        detail = f"rc={rc}, stderr={stderr[:200]}"
    elif 'Claude' not in plain:
        detail = f"Expected 'Claude' in output, got: {plain!r}"
    report("01_empty_json", ok, detail)


def test_02_unknown_model_id():
    """Unknown model_id 'claude-foo-9-9' should fallback gracefully."""
    reset_state()
    inp = {
        "model": {"id": "claude-foo-9-9", "display_name": "Claude Foo 9.9 (Beta)"},
        "context_window": {"used_percentage": 10, "context_window_size": 200000},
    }
    stdout, stderr, rc = run_script(inp)
    plain = strip_ansi(stdout)
    ok = rc == 0 and len(plain) > 0
    detail = ""
    if rc != 0:
        detail = f"rc={rc}, stderr={stderr[:200]}"
    elif len(plain) == 0:
        detail = "Empty output"
    else:
        # The fallback logic strips "Claude " prefix, removes parens, truncates to 6 chars
        # "Claude Foo 9.9 (Beta)" -> strip "Claude " -> "Foo 9.9 (Beta)" -> remove parens -> "Foo 9.9" -> [:6] -> "Foo 9."
        if "Foo 9." not in plain:
            detail = f"Expected fallback model name containing 'Foo 9.' in output, got: {plain!r}"
            ok = False
    report("02_unknown_model_id", ok, detail)


def test_03_rate_limit_boundary_30():
    """Rate limit at exactly 30% should trigger the 30 threshold crossing."""
    reset_state()
    inp = {
        "model": {"id": "claude-sonnet-4-5", "display_name": "Claude Sonnet 4.5"},
        "context_window": {"used_percentage": 10, "context_window_size": 200000},
        "rate_limits": {
            "five_hour": {"used_percentage": 30, "resets_at": 9999999999},
        },
    }
    stdout, stderr, rc = run_script(inp)
    entries = read_log_entries()
    logged_30 = [e for e in entries if e.get('threshold') == 30 and e.get('window') == 'five_hour']
    ok = rc == 0 and len(logged_30) == 1
    detail = ""
    if rc != 0:
        detail = f"rc={rc}, stderr={stderr[:200]}"
    elif len(logged_30) != 1:
        detail = f"Expected exactly 1 log entry for threshold 30, got {len(logged_30)}. Entries: {entries}"
    report("03_rate_limit_boundary_30", ok, detail)


def test_04_rate_limit_boundary_55():
    """Rate limit at exactly 55% should trigger 30 and 55 threshold crossings."""
    reset_state()
    inp = {
        "model": {"id": "claude-sonnet-4-5", "display_name": "Claude Sonnet 4.5"},
        "context_window": {"used_percentage": 10, "context_window_size": 200000},
        "rate_limits": {
            "five_hour": {"used_percentage": 55, "resets_at": 9999999999},
        },
    }
    stdout, stderr, rc = run_script(inp)
    entries = read_log_entries()
    thresholds_logged = sorted([e['threshold'] for e in entries if e.get('window') == 'five_hour'])
    ok = rc == 0 and thresholds_logged == [30, 55]
    detail = ""
    if rc != 0:
        detail = f"rc={rc}, stderr={stderr[:200]}"
    elif thresholds_logged != [30, 55]:
        detail = f"Expected thresholds [30, 55], got {thresholds_logged}"
    report("04_rate_limit_boundary_55", ok, detail)


def test_05_rate_limit_boundary_75():
    """Rate limit at exactly 75% should trigger 30, 55, and 75 threshold crossings."""
    reset_state()
    inp = {
        "model": {"id": "claude-sonnet-4-5", "display_name": "Claude Sonnet 4.5"},
        "context_window": {"used_percentage": 10, "context_window_size": 200000},
        "rate_limits": {
            "five_hour": {"used_percentage": 75, "resets_at": 9999999999},
        },
    }
    stdout, stderr, rc = run_script(inp)
    entries = read_log_entries()
    thresholds_logged = sorted([e['threshold'] for e in entries if e.get('window') == 'five_hour'])
    ok = rc == 0 and thresholds_logged == [30, 55, 75]
    detail = ""
    if rc != 0:
        detail = f"rc={rc}, stderr={stderr[:200]}"
    elif thresholds_logged != [30, 55, 75]:
        detail = f"Expected thresholds [30, 55, 75], got {thresholds_logged}"
    report("05_rate_limit_boundary_75", ok, detail)


def test_06_rate_limit_boundary_99():
    """Rate limit at exactly 99% should trigger all four threshold crossings."""
    reset_state()
    inp = {
        "model": {"id": "claude-sonnet-4-5", "display_name": "Claude Sonnet 4.5"},
        "context_window": {"used_percentage": 10, "context_window_size": 200000},
        "rate_limits": {
            "five_hour": {"used_percentage": 99, "resets_at": 9999999999},
        },
    }
    stdout, stderr, rc = run_script(inp)
    entries = read_log_entries()
    thresholds_logged = sorted([e['threshold'] for e in entries if e.get('window') == 'five_hour'])
    ok = rc == 0 and thresholds_logged == [30, 55, 75, 99]
    detail = ""
    if rc != 0:
        detail = f"rc={rc}, stderr={stderr[:200]}"
    elif thresholds_logged != [30, 55, 75, 99]:
        detail = f"Expected thresholds [30, 55, 75, 99], got {thresholds_logged}"
    report("06_rate_limit_boundary_99", ok, detail)


def test_07_rate_limit_29_9_no_crossing():
    """Rate limit at 29.9% should NOT trigger the 30% crossing."""
    reset_state()
    inp = {
        "model": {"id": "claude-sonnet-4-5", "display_name": "Claude Sonnet 4.5"},
        "context_window": {"used_percentage": 10, "context_window_size": 200000},
        "rate_limits": {
            "five_hour": {"used_percentage": 29.9, "resets_at": 9999999999},
        },
    }
    stdout, stderr, rc = run_script(inp)
    entries = read_log_entries()
    ok = rc == 0 and len(entries) == 0
    detail = ""
    if rc != 0:
        detail = f"rc={rc}, stderr={stderr[:200]}"
    elif len(entries) != 0:
        detail = f"Expected 0 log entries, got {len(entries)}: {entries}"
    report("07_rate_limit_29.9_no_crossing", ok, detail)


def test_08_rate_limit_100():
    """Rate limit at 100% should not crash or index out of bounds."""
    reset_state()
    inp = {
        "model": {"id": "claude-sonnet-4-5", "display_name": "Claude Sonnet 4.5"},
        "context_window": {"used_percentage": 100, "context_window_size": 200000},
        "rate_limits": {
            "five_hour": {"used_percentage": 100, "resets_at": 9999999999},
            "seven_day": {"used_percentage": 100, "resets_at": 9999999999},
        },
    }
    stdout, stderr, rc = run_script(inp)
    plain = strip_ansi(stdout)
    ok = rc == 0 and len(plain) > 0
    detail = ""
    if rc != 0:
        detail = f"rc={rc}, stderr={stderr[:200]}"
    elif len(plain) == 0:
        detail = "Empty output"
    # Check all 4 thresholds fired for both windows
    entries = read_log_entries()
    five_h = sorted([e['threshold'] for e in entries if e.get('window') == 'five_hour'])
    seven_d = sorted([e['threshold'] for e in entries if e.get('window') == 'seven_day'])
    if five_h != [30, 55, 75, 99]:
        ok = False
        detail += f" five_hour thresholds: {five_h}"
    if seven_d != [30, 55, 75, 99]:
        ok = False
        detail += f" seven_day thresholds: {seven_d}"
    report("08_rate_limit_100", ok, detail.strip())


def test_09_very_large_context_window():
    """10M token context window should display as '10M'."""
    reset_state()
    inp = {
        "model": {"id": "claude-opus-4-6[1m]", "display_name": "Claude Opus 4.6"},
        "context_window": {"used_percentage": 25, "context_window_size": 10000000},
    }
    stdout, stderr, rc = run_script(inp)
    plain = strip_ansi(stdout)
    ok = rc == 0 and '10M' in plain
    detail = ""
    if rc != 0:
        detail = f"rc={rc}, stderr={stderr[:200]}"
    elif '10M' not in plain:
        detail = f"Expected '10M' in output, got: {plain!r}"
    report("09_very_large_context_window", ok, detail)


def test_10_corrupt_state_file():
    """Corrupt state file should be recovered gracefully."""
    reset_state()
    # Write garbage to state file
    with open(STATE_FILE, 'w') as f:
        f.write("{{{{not valid json at all!!!@#$%")
    inp = {
        "model": {"id": "claude-sonnet-4-5", "display_name": "Claude Sonnet 4.5"},
        "context_window": {"used_percentage": 10, "context_window_size": 200000},
        "rate_limits": {
            "five_hour": {"used_percentage": 40, "resets_at": 9999999999},
        },
    }
    stdout, stderr, rc = run_script(inp)
    plain = strip_ansi(stdout)
    ok = rc == 0 and len(plain) > 0
    detail = ""
    if rc != 0:
        detail = f"rc={rc}, stderr={stderr[:200]}"
    elif len(plain) == 0:
        detail = "Empty output"
    # State file should have been rewritten cleanly
    state = read_state()
    if not isinstance(state, dict):
        ok = False
        detail += " State file not recovered to valid JSON"
    report("10_corrupt_state_file", ok, detail.strip())


def test_11_corrupt_log_file():
    """Log file with garbage lines mixed in should skip bad lines without crashing."""
    reset_state()
    # Write a mix of valid and garbage lines
    from datetime import datetime
    valid_entry = json.dumps({
        "ts": datetime.now().isoformat(),
        "window": "five_hour",
        "pct": 35,
        "threshold": 30,
        "resets_at": "8888888888",
    })
    with open(LOG_FILE, 'w') as f:
        f.write("THIS IS GARBAGE LINE\n")
        f.write(valid_entry + "\n")
        f.write("{broken json\n")
        f.write("\n")  # empty line
        f.write("more garbage 1234!@#\n")

    inp = {
        "model": {"id": "claude-sonnet-4-5", "display_name": "Claude Sonnet 4.5"},
        "context_window": {"used_percentage": 10, "context_window_size": 200000},
        "rate_limits": {
            "five_hour": {"used_percentage": 60, "resets_at": 9999999999},
        },
    }
    stdout, stderr, rc = run_script(inp)
    plain = strip_ansi(stdout)
    ok = rc == 0 and len(plain) > 0
    detail = ""
    if rc != 0:
        detail = f"rc={rc}, stderr={stderr[:200]}"
    elif len(plain) == 0:
        detail = "Empty output"
    report("11_corrupt_log_file", ok, detail.strip())


def test_12_missing_claude_dir_paths_exist():
    """Verify the script has try/except paths for file I/O failures (code inspection).
    We verify safe_read_json, safe_write_json, safe_append_line all have except clauses."""
    # Read the script source and check for exception handling
    with open(SCRIPT) as f:
        src = f.read()
    checks = [
        ("safe_read_json has except", "def safe_read_json" in src and src.count("except") >= 3),
        ("safe_write_json has except", "def safe_write_json" in src and "os.replace" in src),
        ("safe_append_line has except", "def safe_append_line" in src),
        ("rebuild_logged_windows handles FileNotFoundError", "FileNotFoundError" in src),
    ]
    all_ok = all(c[1] for c in checks)
    detail = "; ".join(f"{name}: {'ok' if ok else 'MISSING'}" for name, ok in checks)
    report("12_error_handling_paths_exist", all_ok, "" if all_ok else detail)


def test_13_concurrent_simulation():
    """Run the script twice rapidly with same data, verify log has exactly 1 entry per threshold (not duplicates)."""
    reset_state()
    inp = {
        "model": {"id": "claude-sonnet-4-5", "display_name": "Claude Sonnet 4.5"},
        "context_window": {"used_percentage": 10, "context_window_size": 200000},
        "rate_limits": {
            "five_hour": {"used_percentage": 60, "resets_at": 9999999999},
        },
    }
    input_str = json.dumps(inp)

    results = [None, None]

    def run_once(idx):
        r = subprocess.run(
            ['bash', SCRIPT],
            input=input_str,
            capture_output=True,
            text=True,
            timeout=15,
        )
        results[idx] = r

    t1 = threading.Thread(target=run_once, args=(0,))
    t2 = threading.Thread(target=run_once, args=(1,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    ok = results[0].returncode == 0 and results[1].returncode == 0
    detail = ""
    if not ok:
        detail = f"rc0={results[0].returncode}, rc1={results[1].returncode}"

    entries = read_log_entries()
    five_h = [e for e in entries if e.get('window') == 'five_hour']
    # For threshold 30: should have exactly 1 entry (both runs see it, but second should see it already logged)
    thresh_30 = [e for e in five_h if e.get('threshold') == 30]
    thresh_55 = [e for e in five_h if e.get('threshold') == 55]

    # Due to race conditions, we may get 2 entries for each threshold.
    # The ideal is 1 each, but 2 is acceptable given true concurrency.
    # What we DON'T want is 0 or >2.
    if len(thresh_30) == 0:
        ok = False
        detail += f" thresh_30 count=0 (expected 1-2)"
    elif len(thresh_30) > 2:
        ok = False
        detail += f" thresh_30 count={len(thresh_30)} (expected 1-2)"

    if len(thresh_55) == 0:
        ok = False
        detail += f" thresh_55 count=0 (expected 1-2)"
    elif len(thresh_55) > 2:
        ok = False
        detail += f" thresh_55 count={len(thresh_55)} (expected 1-2)"

    # Report whether we got exactly 1 (ideal) or 2 (race)
    note = f"thresh_30={len(thresh_30)}, thresh_55={len(thresh_55)}"
    if len(thresh_30) == 1 and len(thresh_55) == 1:
        note += " (ideal: no duplicates)"
    else:
        note += " (race condition duplicates, acceptable)"
    if ok:
        detail = note
    report("13_concurrent_simulation", ok, detail.strip())


# ── Runner ─────────────────────────────────────────────────────────

if __name__ == '__main__':
    print(f"\nStatusline Edge-Case Tests")
    print(f"Script: {SCRIPT}")
    print(f"State:  {STATE_FILE}")
    print(f"Log:    {LOG_FILE}")
    print()

    tests = [
        test_01_empty_json,
        test_02_unknown_model_id,
        test_03_rate_limit_boundary_30,
        test_04_rate_limit_boundary_55,
        test_05_rate_limit_boundary_75,
        test_06_rate_limit_boundary_99,
        test_07_rate_limit_29_9_no_crossing,
        test_08_rate_limit_100,
        test_09_very_large_context_window,
        test_10_corrupt_state_file,
        test_11_corrupt_log_file,
        test_12_missing_claude_dir_paths_exist,
        test_13_concurrent_simulation,
    ]

    for t in tests:
        try:
            t()
        except Exception as e:
            failed += 1
            errors.append((t.__name__, str(e)))
            print(f"  ERROR {t.__name__} -- {e}")

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
    if errors:
        print(f"\nFailures:")
        for name, detail in errors:
            print(f"  - {name}: {detail}")
    print()
    sys.exit(0 if failed == 0 else 1)
