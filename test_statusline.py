#!/usr/bin/env python3
"""Comprehensive test suite for the Claude Code statusline script."""

import json
import os
import subprocess
import re
import time
import unittest
from datetime import datetime, timedelta

SCRIPT = os.path.expanduser("~/.claude/statusline-command.sh")
STATE_FILE = os.path.expanduser("~/.claude/statusline-state.json")
LOG_FILE = os.path.expanduser("~/.claude/rate-limit-log.jsonl")

# ANSI escape stripper
ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def strip_ansi(s):
    return ANSI_RE.sub("", s)


def reset_state():
    """Reset state and log files to clean slate before each test."""
    with open(STATE_FILE, "w") as f:
        f.write("{}")
    with open(LOG_FILE, "w") as f:
        f.write("")


def run_statusline(data: dict) -> str:
    """Pipe JSON data into the statusline script, return raw stdout."""
    proc = subprocess.run(
        ["bash", SCRIPT],
        input=json.dumps(data).encode("utf-8"),
        capture_output=True,
        timeout=15,
    )
    return proc.stdout.decode("utf-8")


def make_input(
    model_id="claude-opus-4-6",
    display_name="Claude Opus 4.6 (1M context)",
    context_used_pct=10.0,
    context_window_size=1_000_000,
    cost_usd=0.0,
    lines_added=0,
    lines_removed=0,
    five_hour_pct=None,
    five_hour_resets_at=None,
    seven_day_pct=None,
    seven_day_resets_at=None,
):
    """Build a well-formed input dict for the statusline script."""
    d = {
        "model": {"id": model_id, "display_name": display_name},
        "context_window": {
            "used_percentage": context_used_pct,
            "context_window_size": context_window_size,
        },
        "cost": {
            "total_cost_usd": cost_usd,
            "total_lines_added": lines_added,
            "total_lines_removed": lines_removed,
        },
        "rate_limits": {},
    }
    if five_hour_pct is not None:
        rl5 = {"used_percentage": five_hour_pct}
        if five_hour_resets_at is not None:
            rl5["resets_at"] = five_hour_resets_at
        d["rate_limits"]["five_hour"] = rl5
    if seven_day_pct is not None:
        rl7 = {"used_percentage": seven_day_pct}
        if seven_day_resets_at is not None:
            rl7["resets_at"] = seven_day_resets_at
        d["rate_limits"]["seven_day"] = rl7
    return d


def read_log_entries():
    """Read all entries from the rate-limit log file."""
    entries = []
    try:
        with open(LOG_FILE) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except FileNotFoundError:
        pass
    return entries


class TestModelAbbreviation(unittest.TestCase):
    """1. Model name abbreviation for all known models."""

    def setUp(self):
        reset_state()

    def test_opus_4_6(self):
        out = strip_ansi(run_statusline(make_input(
            model_id="claude-opus-4-6", display_name="Claude Opus 4.6 (1M context)"
        )))
        self.assertIn("Op4.6", out)

    def test_opus_4_5(self):
        out = strip_ansi(run_statusline(make_input(
            model_id="claude-opus-4-5", display_name="Claude Opus 4.5"
        )))
        self.assertIn("Op4.5", out)

    def test_sonnet_4_6(self):
        out = strip_ansi(run_statusline(make_input(
            model_id="claude-sonnet-4-6", display_name="Claude Sonnet 4.6"
        )))
        self.assertIn("So4.6", out)

    def test_sonnet_4_5(self):
        out = strip_ansi(run_statusline(make_input(
            model_id="claude-sonnet-4-5", display_name="Claude Sonnet 4.5"
        )))
        self.assertIn("So4.5", out)

    def test_sonnet_4_0(self):
        out = strip_ansi(run_statusline(make_input(
            model_id="claude-sonnet-4-0", display_name="Claude Sonnet 4"
        )))
        self.assertIn("So4", out)

    def test_haiku_4_5(self):
        out = strip_ansi(run_statusline(make_input(
            model_id="claude-haiku-4-5", display_name="Claude Haiku 4.5"
        )))
        self.assertIn("Ha4.5", out)

    def test_haiku_3_5(self):
        out = strip_ansi(run_statusline(make_input(
            model_id="claude-haiku-3-5", display_name="Claude Haiku 3.5"
        )))
        self.assertIn("Ha3.5", out)

    def test_unknown_model_fallback(self):
        """Unknown model ID falls back to stripping 'Claude ' prefix and parenthetical."""
        out = strip_ansi(run_statusline(make_input(
            model_id="claude-future-9-9", display_name="Claude Future 9.9 (beta)"
        )))
        # Should strip "Claude " and "(beta)", leaving "Future" truncated to 6 chars
        self.assertIn("Future", out)
        self.assertNotIn("Claude", out)
        self.assertNotIn("(beta)", out)

    def test_context_size_1M(self):
        out = strip_ansi(run_statusline(make_input(context_window_size=1_000_000)))
        self.assertIn("1M", out)

    def test_context_size_200k(self):
        out = strip_ansi(run_statusline(make_input(context_window_size=200_000)))
        self.assertIn("200k", out)

    def test_context_size_zero(self):
        """Context size 0 should not produce a size label."""
        out = strip_ansi(run_statusline(make_input(context_window_size=0)))
        self.assertNotIn("0k", out)
        self.assertNotIn("0M", out)


class TestContextBar(unittest.TestCase):
    """2. Context bar at 0%, 50%, 100%."""

    def setUp(self):
        reset_state()

    def _count_full_blocks(self, raw_out):
        """Count full block characters in the raw output."""
        return raw_out.count("\u2588")

    def test_0_percent(self):
        out = run_statusline(make_input(context_used_pct=0.0))
        plain = strip_ansi(out)
        self.assertIn("0.0%", plain)
        # At 0%, no full blocks in the bar (only dashes)
        # The bar section is 20 chars of blocks/dashes
        # Full blocks should be 0
        self.assertEqual(self._count_full_blocks(out), 0)

    def test_50_percent(self):
        out = run_statusline(make_input(context_used_pct=50.0))
        plain = strip_ansi(out)
        self.assertIn("50.0%", plain)
        # At 50%, 10 full blocks
        self.assertEqual(self._count_full_blocks(out), 10)

    def test_100_percent(self):
        out = run_statusline(make_input(context_used_pct=100.0))
        plain = strip_ansi(out)
        self.assertIn("100.0%", plain)
        # At 100%, 20 full blocks
        self.assertEqual(self._count_full_blocks(out), 20)

    def test_25_percent(self):
        out = run_statusline(make_input(context_used_pct=25.0))
        plain = strip_ansi(out)
        self.assertIn("25.0%", plain)
        self.assertEqual(self._count_full_blocks(out), 5)


class TestRateLimits(unittest.TestCase):
    """3. Rate limits — 5h and 7d percentages display, reset times format."""

    def setUp(self):
        reset_state()

    def test_five_hour_displayed(self):
        out = strip_ansi(run_statusline(make_input(five_hour_pct=42.0)))
        self.assertIn("42%", out)

    def test_seven_day_displayed(self):
        out = strip_ansi(run_statusline(make_input(seven_day_pct=18.0)))
        self.assertIn("18%", out)

    def test_both_displayed(self):
        out = strip_ansi(run_statusline(make_input(five_hour_pct=42.0, seven_day_pct=18.0)))
        self.assertIn("42%", out)
        self.assertIn("18%", out)

    def test_reset_time_today(self):
        """Reset time today (in the future) should show just hour+am/pm."""
        now = datetime.now()
        # Use a time 4 hours from now so it's always in the future when the test runs
        target = now + timedelta(hours=4)
        target = target.replace(minute=0, second=0, microsecond=0)
        epoch = target.timestamp()
        h = target.hour % 12 or 12
        ap = "am" if target.hour < 12 else "pm"
        expected = f"{h}{ap}"
        out = strip_ansi(run_statusline(make_input(
            five_hour_pct=20.0, five_hour_resets_at=epoch
        )))
        self.assertIn(expected, out)

    def test_reset_time_future_day(self):
        """Reset time on a different day should show weekday + time."""
        now = datetime.now()
        target = now + timedelta(days=2)
        target = target.replace(hour=9, minute=0, second=0, microsecond=0)
        epoch = target.timestamp()
        out = strip_ansi(run_statusline(make_input(
            five_hour_pct=20.0, five_hour_resets_at=epoch
        )))
        day_abbrev = target.strftime("%a").lower()
        self.assertIn(day_abbrev, out)
        self.assertIn("9am", out)


class TestCostAndLines(unittest.TestCase):
    """4. Cost and lines display when present, hidden when zero/null."""

    def setUp(self):
        reset_state()

    def test_cost_displayed(self):
        out = strip_ansi(run_statusline(make_input(cost_usd=1.23)))
        self.assertIn("$1.23", out)

    def test_cost_zero_hidden(self):
        out = strip_ansi(run_statusline(make_input(cost_usd=0.0)))
        self.assertNotIn("$0.00", out)

    def test_cost_none_hidden(self):
        d = make_input()
        d["cost"]["total_cost_usd"] = None
        out = strip_ansi(run_statusline(d))
        self.assertNotIn("$", out)

    def test_lines_displayed(self):
        out = strip_ansi(run_statusline(make_input(lines_added=50, lines_removed=10)))
        self.assertIn("+50", out)
        self.assertIn("-10", out)

    def test_lines_zero_hidden(self):
        out = strip_ansi(run_statusline(make_input(lines_added=0, lines_removed=0)))
        self.assertNotIn("+0", out)
        self.assertNotIn("-0", out)

    def test_lines_null_hidden(self):
        d = make_input()
        d["cost"]["total_lines_added"] = None
        d["cost"]["total_lines_removed"] = None
        out = strip_ansi(run_statusline(d))
        # Should not contain any +/- lines indicator
        self.assertNotRegex(out, r"\+\d+.*-\d+")


class TestThresholdCrossings(unittest.TestCase):
    """5. Crossing thresholds logs exactly once per crossing."""

    def setUp(self):
        reset_state()

    def _resets_at(self):
        return (datetime.now() + timedelta(hours=3)).timestamp()

    def test_cross_30(self):
        run_statusline(make_input(five_hour_pct=31.0, five_hour_resets_at=self._resets_at()))
        entries = read_log_entries()
        thresholds = [e["threshold"] for e in entries if e["window"] == "five_hour"]
        self.assertIn(30, thresholds)
        self.assertEqual(thresholds.count(30), 1)

    def test_cross_55(self):
        ra = self._resets_at()
        run_statusline(make_input(five_hour_pct=56.0, five_hour_resets_at=ra))
        entries = read_log_entries()
        thresholds = [e["threshold"] for e in entries if e["window"] == "five_hour"]
        self.assertIn(30, thresholds)
        self.assertIn(55, thresholds)

    def test_cross_75(self):
        ra = self._resets_at()
        run_statusline(make_input(five_hour_pct=80.0, five_hour_resets_at=ra))
        entries = read_log_entries()
        thresholds = [e["threshold"] for e in entries if e["window"] == "five_hour"]
        self.assertIn(30, thresholds)
        self.assertIn(55, thresholds)
        self.assertIn(75, thresholds)

    def test_cross_99(self):
        ra = self._resets_at()
        run_statusline(make_input(five_hour_pct=99.5, five_hour_resets_at=ra))
        entries = read_log_entries()
        thresholds = [e["threshold"] for e in entries if e["window"] == "five_hour"]
        self.assertEqual(sorted(thresholds), [30, 55, 75, 99])

    def test_seven_day_thresholds(self):
        ra = self._resets_at()
        run_statusline(make_input(seven_day_pct=80.0, seven_day_resets_at=ra))
        entries = read_log_entries()
        thresholds = [e["threshold"] for e in entries if e["window"] == "seven_day"]
        self.assertIn(30, thresholds)
        self.assertIn(55, thresholds)
        self.assertIn(75, thresholds)


class TestNoDoubleCount(unittest.TestCase):
    """6. Running twice with same data and same resets_at produces only one log entry per threshold."""

    def setUp(self):
        reset_state()

    def test_no_duplicate_on_second_run(self):
        ra = (datetime.now() + timedelta(hours=3)).timestamp()
        inp = make_input(five_hour_pct=60.0, five_hour_resets_at=ra)
        run_statusline(inp)
        run_statusline(inp)
        entries = read_log_entries()
        five_h = [e for e in entries if e["window"] == "five_hour"]
        # Should have exactly 2 entries: threshold 30 and 55, each once
        thresholds = [e["threshold"] for e in five_h]
        self.assertEqual(sorted(thresholds), [30, 55])

    def test_no_duplicate_on_many_runs(self):
        ra = (datetime.now() + timedelta(hours=3)).timestamp()
        inp = make_input(five_hour_pct=99.5, five_hour_resets_at=ra)
        for _ in range(5):
            run_statusline(inp)
        entries = read_log_entries()
        five_h = [e for e in entries if e["window"] == "five_hour"]
        thresholds = [e["threshold"] for e in five_h]
        self.assertEqual(sorted(thresholds), [30, 55, 75, 99])


class TestStateRecovery(unittest.TestCase):
    """7. Delete state file between runs, re-run with same data, verify no double-count."""

    def setUp(self):
        reset_state()

    def test_rebuild_prevents_duplicates(self):
        ra = (datetime.now() + timedelta(hours=3)).timestamp()
        inp = make_input(five_hour_pct=80.0, five_hour_resets_at=ra)

        # First run: creates log entries and state
        run_statusline(inp)
        entries_before = read_log_entries()
        count_before = len(entries_before)

        # Delete state file but keep log
        with open(STATE_FILE, "w") as f:
            f.write("{}")

        # Second run: should rebuild from log and NOT duplicate entries
        run_statusline(inp)
        entries_after = read_log_entries()
        count_after = len(entries_after)

        self.assertEqual(count_before, count_after,
                         f"Expected no new entries after state loss. Before: {count_before}, After: {count_after}")


class TestReArming(unittest.TestCase):
    """8. Rate drops below threshold then rises above again = new log entry."""

    def setUp(self):
        reset_state()

    def test_rearm_same_window_no_duplicate(self):
        """Within the same resets_at window, a threshold is logged only once even
        if the rate drops below and rises above again (logged_windows dedup)."""
        ra = (datetime.now() + timedelta(hours=3)).timestamp()

        # Step 1: rise above 30 threshold
        run_statusline(make_input(five_hour_pct=35.0, five_hour_resets_at=ra))
        entries1 = read_log_entries()
        count_30_first = sum(1 for e in entries1 if e["threshold"] == 30 and e["window"] == "five_hour")
        self.assertEqual(count_30_first, 1)

        # Step 2: drop below 30 (re-arms the armed flag)
        run_statusline(make_input(five_hour_pct=20.0, five_hour_resets_at=ra))

        # Step 3: rise above 30 again -- armed fires, but logged_windows dedup prevents duplicate
        run_statusline(make_input(five_hour_pct=35.0, five_hour_resets_at=ra))
        entries3 = read_log_entries()
        count_30_total = sum(1 for e in entries3 if e["threshold"] == 30 and e["window"] == "five_hour")
        self.assertEqual(count_30_total, 1, "Same resets_at window: threshold 30 should log only once")

    def test_new_reset_window_fires_immediately(self):
        """A new resets_at value re-arms all thresholds automatically so crossings
        in the new window are logged without requiring a rate drop first."""
        ra1 = (datetime.now() + timedelta(hours=3)).timestamp()
        ra2 = (datetime.now() + timedelta(hours=8)).timestamp()

        run_statusline(make_input(five_hour_pct=60.0, five_hour_resets_at=ra1))
        entries1 = read_log_entries()
        five_h_1 = [e for e in entries1 if e["window"] == "five_hour"]
        self.assertEqual(len(five_h_1), 2, "First window: thresholds 30 and 55")

        # New reset window with same high percentage — window rollover re-arms thresholds
        run_statusline(make_input(five_hour_pct=60.0, five_hour_resets_at=ra2))
        entries2 = read_log_entries()
        five_h_2 = [e for e in entries2 if e["window"] == "five_hour"]
        self.assertEqual(len(five_h_2), 4, "New window fires immediately: 2 more entries for ra2")

        # Verify new entries have the new resets_at key
        ra2_entries = [e for e in five_h_2 if e["resets_at"] == str(int(ra2))]
        self.assertEqual(sorted(e["threshold"] for e in ra2_entries), [30, 55])

        # Running again in the same window does not duplicate
        run_statusline(make_input(five_hour_pct=60.0, five_hour_resets_at=ra2))
        entries3 = read_log_entries()
        five_h_3 = [e for e in entries3 if e["window"] == "five_hour"]
        self.assertEqual(len(five_h_3), 4, "Same window: dedup prevents re-logging")


class TestMonthlyFiltering(unittest.TestCase):
    """9. Only current month entries count in the crossing count display."""

    def setUp(self):
        reset_state()

    def test_old_month_entries_ignored_in_display(self):
        # Manually write a log entry with last month's timestamp
        last_month = datetime.now().replace(day=1) - timedelta(days=1)
        old_entry = json.dumps({
            "ts": last_month.isoformat(),
            "window": "five_hour",
            "pct": 50,
            "threshold": 30,
            "resets_at": "old_reset"
        })
        with open(LOG_FILE, "w") as f:
            f.write(old_entry + "\n")
        # Reset state so it doesn't know about the old entry
        with open(STATE_FILE, "w") as f:
            f.write("{}")

        # Run with no rate limits to just read display
        out = strip_ansi(run_statusline(make_input(context_used_pct=10.0)))

        # The crossing counters should show 0x for both windows, e.g. "5h:0x/7d:0x"
        self.assertIn("5h:0x", out, f"Expected '5h:0x' in output: {out!r}")

    def test_current_month_entries_counted(self):
        ra = (datetime.now() + timedelta(hours=3)).timestamp()
        # Generate some crossings
        run_statusline(make_input(five_hour_pct=80.0, five_hour_resets_at=ra))

        # Now run again to see the count
        out = strip_ansi(run_statusline(make_input(
            five_hour_pct=80.0, five_hour_resets_at=ra
        )))

        # Should show 3 five_hour crossings (30, 55, 75) as "5h:3x"
        matches = re.findall(r"5h:(\d+)x", out)
        self.assertGreaterEqual(len(matches), 1,
                                f"Could not find 5h crossing count in output: {out!r}")
        self.assertEqual(int(matches[0]), 3, f"Expected 3 five_hour crossings, got {matches[0]}")


class TestMissingData(unittest.TestCase):
    """10. Graceful handling when fields are missing from input."""

    def setUp(self):
        reset_state()

    def test_no_rate_limits_key(self):
        d = make_input(context_used_pct=10.0)
        del d["rate_limits"]
        out = strip_ansi(run_statusline(d))
        # Should still output model name and context bar
        self.assertIn("Op4.6", out)
        self.assertIn("10.0%", out)

    def test_no_cost_key(self):
        d = make_input(context_used_pct=10.0)
        del d["cost"]
        out = strip_ansi(run_statusline(d))
        self.assertIn("Op4.6", out)

    def test_no_context_window_key(self):
        d = make_input()
        del d["context_window"]
        out = strip_ansi(run_statusline(d))
        self.assertIn("Op4.6", out)
        # No bar or percentage should appear
        self.assertNotIn("%", out.split("Op4.6")[-1].split("\u2502")[0] if "\u2502" in out else "")

    def test_no_model_key(self):
        d = make_input()
        del d["model"]
        out = strip_ansi(run_statusline(d))
        # Should fallback to "Claude"
        self.assertIn("Claude", out)

    def test_empty_rate_limits(self):
        d = make_input(context_used_pct=10.0)
        d["rate_limits"] = {}
        out = strip_ansi(run_statusline(d))
        self.assertIn("Op4.6", out)

    def test_completely_empty_input(self):
        """Minimal input: just an empty dict."""
        out = run_statusline({})
        plain = strip_ansi(out)
        # Should at least produce the model fallback "Claude"
        self.assertIn("Claude", plain)

    def test_rate_limit_without_resets_at(self):
        """Rate limit percentage present but no resets_at timestamp."""
        out = strip_ansi(run_statusline(make_input(five_hour_pct=40.0)))
        self.assertIn("40%", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
