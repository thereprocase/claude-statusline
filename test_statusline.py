#!/usr/bin/env python3
"""Tests for claude-statusline core engine and themes.

Tests core.py functions directly via import — no shell dispatcher needed.
Run: python -m pytest test_statusline.py  (or python test_statusline.py)
"""

import os
import sys
import json
import re
import time
import unittest
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Import core directly from the themes directory.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'themes'))
import core

# ANSI escape stripper used by render tests.
_ANSI_RE = re.compile(r'\033\[[0-9;]*m')


def strip_ansi(s):
    return _ANSI_RE.sub('', s)


def _future_epoch(seconds=7200):
    """Return an epoch that is `seconds` from now."""
    return (datetime.now() + timedelta(seconds=seconds)).timestamp()


def _past_epoch(seconds=3600):
    """Return an epoch that is `seconds` in the past."""
    return (datetime.now() - timedelta(seconds=seconds)).timestamp()


def _minimal_data(**kwargs):
    """Build the smallest valid data dict that build_context accepts."""
    d = {
        'model': {'id': 'claude-sonnet-4-6', 'display_name': 'Claude Sonnet 4.6'},
        'context_window': {'used_percentage': 10.0, 'context_window_size': 200_000},
        'rate_limits': {},
        'session_id': 'test-session-001',
        'cwd': '/tmp',
    }
    d.update(kwargs)
    return d


# ── 1. _abbreviate_model ────────────────────────────────────────────────────

class TestAbbreviateModel(unittest.TestCase):

    # ── short format: known models ──────────────────────────────────────────

    def test_short_opus_4_6(self):
        self.assertEqual(core._abbreviate_model('claude-opus-4-6', 'Claude Opus 4.6', 'short'), 'Op46')

    def test_short_opus_4_5(self):
        self.assertEqual(core._abbreviate_model('claude-opus-4-5', 'Claude Opus 4.5', 'short'), 'Op45')

    def test_short_sonnet_4_6(self):
        self.assertEqual(core._abbreviate_model('claude-sonnet-4-6', 'Claude Sonnet 4.6', 'short'), 'Sn46')

    def test_short_sonnet_4_5(self):
        self.assertEqual(core._abbreviate_model('claude-sonnet-4-5', 'Claude Sonnet 4.5', 'short'), 'Sn45')

    def test_short_sonnet_4_0(self):
        self.assertEqual(core._abbreviate_model('claude-sonnet-4-0', 'Claude Sonnet 4', 'short'), 'Sn4')

    def test_short_haiku_4_5(self):
        self.assertEqual(core._abbreviate_model('claude-haiku-4-5', 'Claude Haiku 4.5', 'short'), 'Hk45')

    def test_short_haiku_3_5(self):
        self.assertEqual(core._abbreviate_model('claude-haiku-3-5', 'Claude Haiku 3.5', 'short'), 'Hk35')

    # ── short format: startswith matching means dated suffixes resolve ──────

    def test_short_haiku_4_5_with_date_suffix(self):
        # 'claude-haiku-4-5-20251001'.startswith('claude-haiku-4-5') is True
        self.assertEqual(core._abbreviate_model('claude-haiku-4-5-20251001', 'Claude Haiku 4.5', 'short'), 'Hk45')

    def test_short_opus_4_6_with_context_suffix(self):
        # 'claude-opus-4-6[1m]'.startswith('claude-opus-4-6') is True
        self.assertEqual(core._abbreviate_model('claude-opus-4-6[1m]', 'Claude Opus 4.6', 'short'), 'Op46')

    # ── long format: known models ────────────────────────────────────────────

    def test_long_opus_4_6(self):
        self.assertEqual(core._abbreviate_model('claude-opus-4-6', 'Claude Opus 4.6', 'long'), 'Opus 4.6')

    def test_long_sonnet_4_6(self):
        self.assertEqual(core._abbreviate_model('claude-sonnet-4-6', 'Claude Sonnet 4.6', 'long'), 'Sonnet 4.6')

    def test_long_haiku_4_5(self):
        self.assertEqual(core._abbreviate_model('claude-haiku-4-5', 'Claude Haiku 4.5', 'long'), 'Haiku 4.5')

    def test_long_haiku_3_5(self):
        self.assertEqual(core._abbreviate_model('claude-haiku-3-5', 'Claude Haiku 3.5', 'long'), 'Haiku 3.5')

    def test_long_opus_4_5(self):
        self.assertEqual(core._abbreviate_model('claude-opus-4-5', 'Claude Opus 4.5', 'long'), 'Opus 4.5')

    def test_long_sonnet_4_5(self):
        self.assertEqual(core._abbreviate_model('claude-sonnet-4-5', 'Claude Sonnet 4.5', 'long'), 'Sonnet 4.5')

    def test_long_sonnet_4_0(self):
        self.assertEqual(core._abbreviate_model('claude-sonnet-4-0', 'Claude Sonnet 4', 'long'), 'Sonnet 4')

    # ── short format: programmatically-derived future versions ──────────────
    # These aren't in any hardcoded table — they're parsed from the model id.

    def test_short_opus_4_7(self):
        self.assertEqual(core._abbreviate_model('claude-opus-4-7', 'Claude Opus 4.7', 'short'), 'Op47')

    def test_short_opus_4_7_with_context_suffix(self):
        self.assertEqual(core._abbreviate_model('claude-opus-4-7[1m]', 'Claude Opus 4.7', 'short'), 'Op47')

    def test_short_future_opus_5_0(self):
        # minor=0 drops the zero: Op5, not Op50
        self.assertEqual(core._abbreviate_model('claude-opus-5-0', 'Claude Opus 5', 'short'), 'Op5')

    def test_short_future_sonnet_5_3(self):
        self.assertEqual(core._abbreviate_model('claude-sonnet-5-3', 'Claude Sonnet 5.3', 'short'), 'Sn53')

    def test_short_future_haiku_5_0(self):
        self.assertEqual(core._abbreviate_model('claude-haiku-5-0', 'Claude Haiku 5', 'short'), 'Hk5')

    def test_short_future_haiku_5_1_with_date_suffix(self):
        self.assertEqual(core._abbreviate_model('claude-haiku-5-1-20271015', 'Claude Haiku 5.1', 'short'), 'Hk51')

    # ── long format: programmatically-derived future versions ───────────────

    def test_long_opus_4_7(self):
        self.assertEqual(core._abbreviate_model('claude-opus-4-7', 'Claude Opus 4.7', 'long'), 'Opus 4.7')

    def test_long_future_opus_5_0(self):
        # minor=0 drops to bare major: 'Opus 5', not 'Opus 5.0'
        self.assertEqual(core._abbreviate_model('claude-opus-5-0', 'Claude Opus 5', 'long'), 'Opus 5')

    def test_long_future_sonnet_5_3(self):
        self.assertEqual(core._abbreviate_model('claude-sonnet-5-3', 'Claude Sonnet 5.3', 'long'), 'Sonnet 5.3')

    def test_long_future_haiku_5_0(self):
        self.assertEqual(core._abbreviate_model('claude-haiku-5-0', 'Claude Haiku 5', 'long'), 'Haiku 5')

    # ── full format: returns display_name verbatim ───────────────────────────

    def test_full_returns_display_name(self):
        display = 'Claude Opus 4.6 (1M context)'
        self.assertEqual(core._abbreviate_model('claude-opus-4-6', display, 'full'), display)

    def test_full_unknown_model_returns_display_name(self):
        display = 'Claude Future 9.9 (beta)'
        self.assertEqual(core._abbreviate_model('claude-future-9-9', display, 'full'), display)

    # ── unknown family: parsed from model id (first 2 chars capitalized) ────

    def test_short_unknown_family_mythos(self):
        # Hypothetical new family — no code change needed
        result = core._abbreviate_model('claude-mythos-5-1', 'Claude Mythos 5.1', 'short')
        self.assertEqual(result, 'My51')

    def test_long_unknown_family_mythos(self):
        result = core._abbreviate_model('claude-mythos-5-1', 'Claude Mythos 5.1', 'long')
        self.assertEqual(result, 'Mythos 5.1')

    def test_short_unknown_family_minor_zero_drops(self):
        result = core._abbreviate_model('claude-mythos-5-0', 'Claude Mythos 5', 'short')
        self.assertEqual(result, 'My5')

    def test_long_unknown_family_minor_zero_drops(self):
        result = core._abbreviate_model('claude-mythos-5-0', 'Claude Mythos 5', 'long')
        self.assertEqual(result, 'Mythos 5')

    def test_short_unknown_family_future(self):
        # Old test expected 'Futur' via display-name truncation; new behavior
        # parses the id directly → 'Fu99'. Programmatic is better.
        result = core._abbreviate_model('claude-future-9-9', 'Claude Future 9.9 (beta)', 'short')
        self.assertEqual(result, 'Fu99')

    def test_long_unknown_family_future(self):
        result = core._abbreviate_model('claude-future-9-9', 'Claude Future 9.9 (beta)', 'long')
        self.assertEqual(result, 'Future 9.9')

    # ── malformed id: falls through to display-name parsing ──────────────────

    def test_short_malformed_id_uses_display_name(self):
        # id doesn't match claude-<family>-<M>-<N> shape at all
        result = core._abbreviate_model('some-other-model', 'GPT Nano', 'short')
        self.assertEqual(result, 'GPT N')

    def test_short_malformed_id_strips_parenthetical(self):
        # 'claude-beta' without a version — doesn't match → display-name fallback
        result = core._abbreviate_model('claude-beta', 'Claude Beta (preview)', 'short')
        self.assertEqual(result, 'Beta')

    # ── empty / None edge cases ──────────────────────────────────────────────

    def test_short_empty_model_id(self):
        # No prefix matches; display_name is '' → m='' → ''[:5] → ''
        result = core._abbreviate_model('', '', 'short')
        self.assertEqual(result, '')

    def test_short_empty_display_name_known_id(self):
        # Known id still matches via startswith
        result = core._abbreviate_model('claude-opus-4-6', '', 'short')
        self.assertEqual(result, 'Op46')

    def test_full_empty_display_name(self):
        result = core._abbreviate_model('claude-opus-4-6', '', 'full')
        self.assertEqual(result, '')


# ── 2. _parse_remote ────────────────────────────────────────────────────────

class TestParseRemote(unittest.TestCase):

    # ── SCP-style git@ URLs ──────────────────────────────────────────────────

    def test_github_scp(self):
        self.assertEqual(core._parse_remote('git@github.com:owner/repo.git'), ('gh', 'owner'))

    def test_gitlab_scp(self):
        self.assertEqual(core._parse_remote('git@gitlab.com:owner/repo.git'), ('gl', 'owner'))

    def test_bitbucket_scp(self):
        self.assertEqual(core._parse_remote('git@bitbucket.org:owner/repo.git'), ('bb', 'owner'))

    def test_github_scp_no_git_suffix(self):
        self.assertEqual(core._parse_remote('git@github.com:owner/repo'), ('gh', 'owner'))

    def test_unknown_host_scp(self):
        # First label before first '.' becomes the short name
        self.assertEqual(core._parse_remote('git@myserver.example.com:owner/repo'), ('myserver', 'owner'))

    def test_single_label_host_scp(self):
        # Host with no dots: split('.', 1)[0] returns the host itself
        self.assertEqual(core._parse_remote('git@intranet:team/project.git'), ('intranet', 'team'))

    # ── https:// URLs ────────────────────────────────────────────────────────

    def test_github_https(self):
        self.assertEqual(core._parse_remote('https://github.com/owner/repo.git'), ('gh', 'owner'))

    def test_gitlab_https(self):
        self.assertEqual(core._parse_remote('https://gitlab.com/owner/repo.git'), ('gl', 'owner'))

    def test_https_with_user(self):
        # https://user@github.com/owner/repo.git — user@ before host
        self.assertEqual(core._parse_remote('https://user@github.com/owner/repo.git'), ('gh', 'owner'))

    # ── ssh:// URLs ──────────────────────────────────────────────────────────

    def test_github_ssh_protocol(self):
        self.assertEqual(core._parse_remote('ssh://git@github.com/owner/repo.git'), ('gh', 'owner'))

    def test_ssh_with_port(self):
        # ssh://git@host:2222/owner/repo — port is stripped from host
        hs, owner = core._parse_remote('ssh://git@host.example.com:2222/owner/repo')
        self.assertEqual(hs, 'host')
        self.assertEqual(owner, 'owner')

    def test_ssh_unknown_host(self):
        hs, owner = core._parse_remote('ssh://git@private.corp.com/team/project.git')
        self.assertEqual(hs, 'private')
        self.assertEqual(owner, 'team')

    # ── empty / degenerate inputs ────────────────────────────────────────────

    def test_empty_string(self):
        self.assertEqual(core._parse_remote(''), ('', ''))

    def test_only_git_at(self):
        # 'git@' with nothing after: host='' path=''
        hs, owner = core._parse_remote('git@')
        self.assertEqual(hs, '')
        self.assertEqual(owner, '')

    def test_no_path_segments(self):
        # https://github.com with no slash after host — host and path are never
        # assigned in the https:// branch, so both come back empty.
        hs, owner = core._parse_remote('https://github.com')
        self.assertEqual(hs, '')
        self.assertEqual(owner, '')

    def test_git_suffix_stripped(self):
        # .git suffix is stripped before any other parsing
        hs1, o1 = core._parse_remote('https://github.com/a/b.git')
        hs2, o2 = core._parse_remote('https://github.com/a/b')
        self.assertEqual(hs1, hs2)
        self.assertEqual(o1, o2)


# ── 3. _truncate_path ────────────────────────────────────────────────────────

class TestTruncatePath(unittest.TestCase):

    def test_short_unix_path_returned_as_is(self):
        p = '/home/user/code'
        self.assertEqual(core._truncate_path(p), p)

    def test_short_windows_path_returned_as_is(self):
        p = 'C:/Users/dev/code'
        self.assertEqual(core._truncate_path(p), p)

    def test_empty_string(self):
        self.assertEqual(core._truncate_path(''), '')

    def test_single_segment_unix(self):
        self.assertEqual(core._truncate_path('/tmp'), '/tmp')

    def test_exact_max_len_not_truncated(self):
        # A path of exactly 75 chars should not be truncated
        p = '/a/' + 'b' * 72
        self.assertEqual(len(p), 75)
        self.assertEqual(core._truncate_path(p), p)

    def test_one_over_max_len_is_truncated(self):
        # The algorithm always keeps at least one tail segment, so the output may
        # slightly exceed max_len when the final segment is large. The contract is
        # that '...' appears, not that len() <= max_len.
        p = '/a/' + 'b' * 73
        self.assertEqual(len(p), 76)
        result = core._truncate_path(p)
        self.assertIn('...', result)

    def test_long_unix_path_contains_ellipsis(self):
        # Construct a path that is definitely over 75 characters.
        long_p = '/home/user/projects/verylongprojectname/src/components/submodules/deeper/anddeeper/path'
        self.assertGreater(len(long_p), 75)
        result = core._truncate_path(long_p)
        self.assertIn('...', result)

    def test_windows_drive_preserved(self):
        # Windows drive letters should appear in the output
        long_p = 'C:/Users/someone/extremely/long/path/that/will/definitely/exceed/the/max/limit/right'
        result = core._truncate_path(long_p)
        self.assertTrue(result.startswith('C:/'))
        self.assertIn('...', result)

    def test_path_sep_normalized_to_forward_slash(self):
        # _truncate_path does norm = cwd.replace(os.sep, '/')
        # On any platform, forward slashes are used in output
        p = '/a/b/c'
        result = core._truncate_path(p)
        self.assertNotIn('\\', result)

    def test_long_path_preserves_tail_segments(self):
        # The algorithm keeps trailing path segments intact — the final segment
        # should survive truncation since it is inserted last.
        long_p = '/very/deeply/nested/' + 'a/' * 20 + 'finalfile'
        result = core._truncate_path(long_p)
        self.assertTrue(result.endswith('finalfile'))

    def test_custom_max_len(self):
        p = '/a/b/c/d/e/f/g/h/i/j'
        result_30 = core._truncate_path(p, max_len=30)
        result_10 = core._truncate_path(p, max_len=10)
        # Shorter max_len should produce shorter or equal output
        self.assertLessEqual(len(result_10), len(result_30))


# ── 4. fmt_reset ─────────────────────────────────────────────────────────────

class TestFmtReset(unittest.TestCase):

    def test_past_time_returns_empty(self):
        self.assertEqual(core.fmt_reset(_past_epoch(3600)), '')

    def test_exactly_now_is_past(self):
        # t <= now should return ''
        epoch = datetime.now().timestamp() - 0.001
        self.assertEqual(core.fmt_reset(epoch), '')

    def test_future_today_returns_time_only(self):
        # Reset is 4 hours from now, same calendar day
        now = datetime.now()
        target = now + timedelta(hours=4)
        target = target.replace(minute=0, second=0, microsecond=0)
        # Only proceed if target is still today (avoid edge at midnight)
        if target.date() == now.date():
            epoch = target.timestamp()
            result = core.fmt_reset(epoch)
            h = target.hour % 12 or 12
            ap = 'a' if target.hour < 12 else 'p'
            self.assertEqual(result, f'{h}{ap}')

    def test_future_tomorrow_returns_day_and_time(self):
        now = datetime.now()
        target = (now + timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0)
        epoch = target.timestamp()
        result = core.fmt_reset(epoch)
        days = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
        expected_day = days[target.weekday()]
        h = target.hour % 12 or 12   # 15 % 12 = 3
        ap = 'a' if target.hour < 12 else 'p'  # 'p'
        self.assertEqual(result, f'{expected_day}{h}{ap}')

    def test_midnight_hour_formats_as_12(self):
        # hour=0 → 0%12=0 → `or 12` → 12a
        now = datetime.now()
        target = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        if target.date() != now.date():
            epoch = target.timestamp()
            result = core.fmt_reset(epoch)
            # hour 0 → 12; am/pm 'a'
            self.assertIn('12a', result)

    def test_noon_hour_formats_as_12p(self):
        now = datetime.now()
        target = (now + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        if target.date() != now.date():
            epoch = target.timestamp()
            result = core.fmt_reset(epoch)
            self.assertIn('12p', result)

    def test_day_only_true_same_day_returns_empty(self):
        now = datetime.now()
        target = now + timedelta(hours=2)
        if target.date() == now.date():
            epoch = target.timestamp()
            result = core.fmt_reset(epoch, day_only=True)
            self.assertEqual(result, '')

    def test_day_only_true_different_day_returns_day_abbreviation(self):
        now = datetime.now()
        target = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        epoch = target.timestamp()
        result = core.fmt_reset(epoch, day_only=True)
        days = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
        self.assertEqual(result, days[target.weekday()])

    def test_uppercase_true_future_today(self):
        now = datetime.now()
        target = now + timedelta(hours=3)
        if target.date() == now.date():
            epoch = target.timestamp()
            result = core.fmt_reset(epoch, uppercase=True)
            # All characters should be uppercase (digits are unchanged, 'A' or 'P')
            self.assertTrue(result.isupper() or result[-1] in ('A', 'P'))
            self.assertIn(result[-1], ('A', 'P'))

    def test_uppercase_true_different_day(self):
        now = datetime.now()
        target = (now + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
        epoch = target.timestamp()
        result = core.fmt_reset(epoch, uppercase=True)
        days_upper = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        # Result should start with an uppercase 3-letter day abbreviation
        self.assertTrue(any(result.startswith(d) for d in days_upper))

    def test_invalid_epoch_string_returns_empty(self):
        self.assertEqual(core.fmt_reset('not-a-number'), '')

    def test_invalid_epoch_none_returns_empty(self):
        self.assertEqual(core.fmt_reset(None), '')

    def test_lowercase_days_are_two_letters(self):
        # The day abbreviations in fmt_reset are 2-letter lowercase: mo tu we th fr sa su
        now = datetime.now()
        target = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        epoch = target.timestamp()
        result = core.fmt_reset(epoch)
        # Result should start with a 2-letter lowercase day
        valid_days = {'mo', 'tu', 'we', 'th', 'fr', 'sa', 'su'}
        self.assertIn(result[:2], valid_days)


# ── 5. fmt_reset_long ────────────────────────────────────────────────────────

class TestFmtResetLong(unittest.TestCase):

    def test_past_time_returns_empty(self):
        self.assertEqual(core.fmt_reset_long(_past_epoch()), '')

    def test_future_today_returns_time_string(self):
        now = datetime.now()
        target = now + timedelta(hours=3)
        target = target.replace(second=0, microsecond=0)
        if target.date() == now.date():
            epoch = target.timestamp()
            result = core.fmt_reset_long(epoch)
            h = target.hour % 12 or 12
            mn = target.minute
            ap = 'am' if target.hour < 12 else 'pm'
            self.assertEqual(result, f'{h}:{mn:02d}{ap}')

    def test_future_different_day_returns_day_and_time(self):
        now = datetime.now()
        target = (now + timedelta(days=1)).replace(hour=14, minute=30, second=0, microsecond=0)
        epoch = target.timestamp()
        result = core.fmt_reset_long(epoch)
        days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
        expected_day = days[target.weekday()]
        self.assertIn(expected_day, result)
        self.assertIn('2:30pm', result)

    def test_long_day_names_are_three_letters(self):
        # fmt_reset_long uses 3-letter days: mon tue wed thu fri sat sun
        now = datetime.now()
        target = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        epoch = target.timestamp()
        result = core.fmt_reset_long(epoch)
        valid_days = {'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'}
        self.assertIn(result[:3], valid_days)

    def test_day_only_true_same_day(self):
        now = datetime.now()
        target = now + timedelta(hours=2)
        if target.date() == now.date():
            self.assertEqual(core.fmt_reset_long(target.timestamp(), day_only=True), '')

    def test_day_only_true_different_day(self):
        now = datetime.now()
        target = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        epoch = target.timestamp()
        result = core.fmt_reset_long(epoch, day_only=True)
        valid_days = {'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'}
        self.assertIn(result, valid_days)

    def test_uppercase_true_uses_am_pm_uppercase(self):
        now = datetime.now()
        target = now + timedelta(hours=3)
        if target.date() == now.date():
            result = core.fmt_reset_long(target.timestamp(), uppercase=True)
            self.assertTrue(result.endswith('AM') or result.endswith('PM'))

    def test_invalid_epoch_returns_empty(self):
        self.assertEqual(core.fmt_reset_long('garbage'), '')

    def test_midnight_is_12_am(self):
        now = datetime.now()
        target = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        if target.date() != now.date():
            result = core.fmt_reset_long(target.timestamp())
            # hour 0 → 12am (same day path: returns time only if same day, day+time if different)
            self.assertIn('12:00am', result)

    def test_noon_is_12_pm(self):
        now = datetime.now()
        target = (now + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        if target.date() != now.date():
            result = core.fmt_reset_long(target.timestamp())
            self.assertIn('12:00pm', result)


# ── 6. _track_session ────────────────────────────────────────────────────────

class TestTrackSession(unittest.TestCase):

    def test_new_session_returns_dirty(self):
        data = {'session_id': 'abc123'}
        state = {}
        _, _, dirty = core._track_session(data, state)
        self.assertTrue(dirty)

    def test_new_session_stores_sid_in_state(self):
        data = {'session_id': 'abc123'}
        state = {}
        core._track_session(data, state)
        self.assertEqual(state['session_start']['sid'], 'abc123')

    def test_same_session_not_dirty(self):
        data = {'session_id': 'abc123'}
        state = {}
        # First call — new session, dirty
        core._track_session(data, state)
        # Second call — same session, should not be dirty
        _, _, dirty = core._track_session(data, state)
        self.assertFalse(dirty)

    def test_different_session_id_resets_timer(self):
        state = {}
        core._track_session({'session_id': 'first'}, state)
        ts_first = state['session_start']['ts']
        # Advance time in state artificially to confirm reset resets the timestamp
        state['session_start']['ts'] -= 1000
        core._track_session({'session_id': 'second'}, state)
        ts_second = state['session_start']['ts']
        # Timestamp should be refreshed (close to now, not 1000 seconds ago)
        self.assertGreater(ts_second, ts_first - 500)

    def test_duration_seconds_format(self):
        data = {'session_id': 'test'}
        state = {'session_start': {'sid': 'test', 'ts': datetime.now().timestamp() - 45}}
        dur, elapsed, _ = core._track_session(data, state)
        self.assertRegex(dur, r'^\d+s$')
        self.assertAlmostEqual(elapsed, 45, delta=2)

    def test_duration_minutes_format(self):
        data = {'session_id': 'test'}
        state = {'session_start': {'sid': 'test', 'ts': datetime.now().timestamp() - 125}}
        dur, elapsed, _ = core._track_session(data, state)
        # 125s → 2m05s
        self.assertRegex(dur, r'^\d+m\d{2}s$')
        self.assertIn('2m', dur)
        self.assertIn('05s', dur)

    def test_duration_hours_format(self):
        data = {'session_id': 'test'}
        state = {'session_start': {'sid': 'test', 'ts': datetime.now().timestamp() - 3661}}
        dur, elapsed, _ = core._track_session(data, state)
        # 3661s = 1h01m
        self.assertRegex(dur, r'^\d+h\d{2}m$')
        self.assertIn('1h', dur)
        self.assertIn('01m', dur)

    def test_duration_exactly_one_hour(self):
        data = {'session_id': 'test'}
        state = {'session_start': {'sid': 'test', 'ts': datetime.now().timestamp() - 3600}}
        dur, _, _ = core._track_session(data, state)
        self.assertEqual(dur, '1h00m')

    def test_duration_exactly_one_minute(self):
        data = {'session_id': 'test'}
        state = {'session_start': {'sid': 'test', 'ts': datetime.now().timestamp() - 60}}
        dur, _, _ = core._track_session(data, state)
        self.assertEqual(dur, '1m00s')

    def test_zero_elapsed_is_0s(self):
        data = {'session_id': 'test'}
        # Session just started — ts is now
        state = {'session_start': {'sid': 'test', 'ts': datetime.now().timestamp()}}
        dur, elapsed, _ = core._track_session(data, state)
        # elapsed ≈ 0, so dur should be '0s'
        self.assertRegex(dur, r'^\d+s$')

    def test_missing_session_id_treated_as_empty_string(self):
        data = {}  # no session_id key
        state = {}
        dur, elapsed, dirty = core._track_session(data, state)
        # Missing key → sid='', new session
        self.assertTrue(dirty)
        self.assertIsInstance(dur, str)


# ── 7. _process_rate_limits ──────────────────────────────────────────────────

class TestProcessRateLimits(unittest.TestCase):

    def _config(self, auto_hide=True, date_format='short'):
        return {'auto_hide_reset': auto_hide, 'date_format': date_format}

    def _empty_data(self):
        return {'rate_limits': {}}

    def _data_with_five_hour(self, pct, resets_at=None):
        rl = {'used_percentage': pct}
        if resets_at is not None:
            rl['resets_at'] = resets_at
        return {'rate_limits': {'five_hour': rl}}

    def _data_with_seven_day(self, pct, resets_at=None):
        rl = {'used_percentage': pct}
        if resets_at is not None:
            rl['resets_at'] = resets_at
        return {'rate_limits': {'seven_day': rl}}

    def test_no_rate_limit_data_returns_two_items_pct_none(self):
        results, dirty = core._process_rate_limits(
            self._empty_data(), 'sonnet', {}, False, None, self._config()
        )
        self.assertEqual(len(results), 2)
        self.assertIsNone(results[0]['pct'])
        self.assertIsNone(results[1]['pct'])

    def test_no_rate_limit_data_not_dirty(self):
        # No pct data → no threshold logic → dirty only from new resets_at window check
        # Since resets_at is None, rk='unknown'; first call sets rk_key → dirty=True
        results, dirty = core._process_rate_limits(
            self._empty_data(), 'sonnet', {}, False, None, self._config()
        )
        # pct is None so the window/threshold block is skipped — dirty stays False
        self.assertFalse(dirty)

    def test_result_keys_present(self):
        results, _ = core._process_rate_limits(
            self._data_with_five_hour(50.0, _future_epoch()),
            'sonnet', {}, False, None, self._config()
        )
        for item in results:
            self.assertIn('key', item)
            self.assertIn('label', item)
            self.assertIn('pct', item)
            self.assertIn('reset_str', item)

    def test_five_hour_label(self):
        results, _ = core._process_rate_limits(
            self._data_with_five_hour(10.0), 'sonnet', {}, False, None, self._config()
        )
        five_h = next(r for r in results if r['key'] == 'five_hour')
        self.assertEqual(five_h['label'], '5h')

    def test_seven_day_label(self):
        results, _ = core._process_rate_limits(
            self._data_with_seven_day(10.0), 'sonnet', {}, False, None, self._config()
        )
        seven_d = next(r for r in results if r['key'] == 'seven_day')
        self.assertEqual(seven_d['label'], '7d')

    def test_pct_rounded_to_int(self):
        results, _ = core._process_rate_limits(
            self._data_with_five_hour(42.6), 'sonnet', {}, False, None, self._config()
        )
        five_h = next(r for r in results if r['key'] == 'five_hour')
        self.assertEqual(five_h['pct'], 43)

    def test_auto_hide_five_hour_below_50_hides_reset_time(self):
        # 20% with reset > 30 minutes away → reset_str should be '' (auto-hidden)
        resets_at = _future_epoch(7200)  # 2 hours away
        results, _ = core._process_rate_limits(
            self._data_with_five_hour(20.0, resets_at),
            'sonnet', {}, False, None, self._config(auto_hide=True)
        )
        five_h = next(r for r in results if r['key'] == 'five_hour')
        self.assertEqual(five_h['reset_str'], '')

    def test_auto_hide_five_hour_above_50_shows_reset_time(self):
        # 55% → rl_i >= 50 → show reset time
        resets_at = _future_epoch(7200)
        results, _ = core._process_rate_limits(
            self._data_with_five_hour(55.0, resets_at),
            'sonnet', {}, False, None, self._config(auto_hide=True)
        )
        five_h = next(r for r in results if r['key'] == 'five_hour')
        self.assertNotEqual(five_h['reset_str'], '')

    def test_auto_hide_five_hour_below_30min_shows_reset_time(self):
        # < 30 minutes until reset → always show even if pct < 50
        resets_at = _future_epoch(600)  # 10 minutes away
        results, _ = core._process_rate_limits(
            self._data_with_five_hour(20.0, resets_at),
            'sonnet', {}, False, None, self._config(auto_hide=True)
        )
        five_h = next(r for r in results if r['key'] == 'five_hour')
        self.assertNotEqual(five_h['reset_str'], '')

    def test_no_auto_hide_always_shows_reset_time(self):
        resets_at = _future_epoch(7200)
        results, _ = core._process_rate_limits(
            self._data_with_five_hour(10.0, resets_at),
            'sonnet', {}, False, None, self._config(auto_hide=False)
        )
        five_h = next(r for r in results if r['key'] == 'five_hour')
        self.assertNotEqual(five_h['reset_str'], '')

    def test_threshold_95_crossed_logs_entry(self):
        # 96% ≥ 95 → should set dirty=True and disarm the threshold
        resets_at = _future_epoch(3600)
        state = {}
        results, dirty = core._process_rate_limits(
            self._data_with_five_hour(96.0, resets_at),
            'sonnet', state, False, None, self._config()
        )
        self.assertTrue(dirty)
        # Armed flag for threshold 95 should now be False (disarmed after crossing)
        self.assertFalse(state.get('sonnet_five_hour_armed_95', True))

    def test_threshold_94_9_not_crossed(self):
        # 94.9% < 95 → threshold not crossed, armed flag stays True
        resets_at = _future_epoch(3600)
        state = {}
        results, dirty = core._process_rate_limits(
            self._data_with_five_hour(94.9, resets_at),
            'sonnet', state, False, None, self._config()
        )
        # Armed is set to True by new window detection, then not disarmed since rl < 95
        # threshold is not crossed → armed_95 should remain True
        self.assertTrue(state.get('sonnet_five_hour_armed_95', True))

    def test_threshold_exactly_95_crossed(self):
        # rl=95 → 95 >= 95 is True
        resets_at = _future_epoch(3600)
        state = {}
        core._process_rate_limits(
            self._data_with_five_hour(95.0, resets_at),
            'sonnet', state, False, None, self._config()
        )
        self.assertFalse(state.get('sonnet_five_hour_armed_95', True))

    def test_new_reset_window_rearms_thresholds(self):
        # First call at 96% → disarms
        resets_at_1 = _future_epoch(3600)
        state = {}
        core._process_rate_limits(
            self._data_with_five_hour(96.0, resets_at_1),
            'sonnet', state, False, None, self._config()
        )
        # Still disarmed
        self.assertFalse(state.get('sonnet_five_hour_armed_95', True))

        # Second call with a new resets_at value → should re-arm
        resets_at_2 = _future_epoch(7200)
        core._process_rate_limits(
            self._data_with_five_hour(96.0, resets_at_2),
            'sonnet', state, False, None, self._config()
        )
        # After re-arm + immediate cross, should be disarmed again
        # Key point: rk changed → re-arm happened (state reflects new window)
        self.assertEqual(state.get('sonnet_five_hour_last_rk'), str(int(float(resets_at_2))))

    def test_only_one_threshold_exists(self):
        # THRESHOLDS = [95] — confirm no other thresholds exist
        self.assertEqual(core.THRESHOLDS, [95])

    def test_model_family_scopes_state_keys(self):
        # opus and sonnet use different state key namespaces
        resets_at = _future_epoch(3600)
        state_opus = {}
        state_sonnet = {}
        core._process_rate_limits(
            self._data_with_five_hour(96.0, resets_at),
            'opus', state_opus, False, None, self._config()
        )
        core._process_rate_limits(
            self._data_with_five_hour(96.0, resets_at),
            'sonnet', state_sonnet, False, None, self._config()
        )
        # Each state dict should contain family-prefixed keys
        self.assertIn('opus_five_hour_armed_95', state_opus)
        self.assertIn('sonnet_five_hour_armed_95', state_sonnet)

    def test_past_resets_at_produces_empty_reset_str(self):
        # If resets_at is in the past, fmt_reset returns '' regardless of auto_hide
        resets_at = _past_epoch(3600)
        results, _ = core._process_rate_limits(
            self._data_with_five_hour(55.0, resets_at),
            'sonnet', {}, False, None, self._config(auto_hide=False)
        )
        five_h = next(r for r in results if r['key'] == 'five_hour')
        self.assertEqual(five_h['reset_str'], '')


# ── 8. build_context ─────────────────────────────────────────────────────────

class TestBuildContext(unittest.TestCase):

    def _call(self, data=None):
        """Call build_context, isolating file I/O side effects."""
        with patch.object(core, 'safe_write_json'), \
             patch.object(core, 'safe_read_json', return_value={}), \
             patch.object(core, '_collect_git', return_value={
                 'branch': '', 'detached': False, 'dirty': 0,
                 'ahead': 0, 'behind': 0, 'stash': 0,
                 'remote_short': '', 'worktree': '', 'operation': '',
             }), \
             patch.object(core, '_find_claude_account', return_value='user@example.com'), \
             patch.object(core, '_rotate_log', return_value=False), \
             patch.object(core, '_rebuild_logged_windows', return_value={'five_hour': {}, 'seven_day': {}}):
            return core.build_context(data=data)

    # ── return keys ──────────────────────────────────────────────────────────

    def test_returns_all_expected_keys(self):
        ctx = self._call(_minimal_data())
        expected_keys = [
            'model_name', 'model_id', 'model_family', 'model_display',
            'cw_size', 'cw_str', 'used_pct',
            'cwd', 'path_display',
            'email', 'user_short',
            'effort',
            'rate_limits',
            'session_dur', 'session_elapsed',
            'git',
            'config',
        ]
        for k in expected_keys:
            self.assertIn(k, ctx, f'Missing key: {k}')

    def test_error_fallback_on_none_data_with_stdin_failure(self):
        # data=None triggers json.load(sys.stdin); mock stdin to raise
        with patch('sys.stdin') as mock_stdin:
            mock_stdin.read.side_effect = Exception('no stdin')
            # json.load will call mock_stdin.read internally and raise
            import io
            mock_stdin = io.StringIO('')  # empty → json.load raises JSONDecodeError
            with patch('sys.stdin', mock_stdin):
                ctx = core.build_context(data=None)
        self.assertTrue(ctx.get('error'))
        self.assertEqual(ctx['model_name'], '???')
        self.assertEqual(ctx['rate_limits'], [])

    # ── model family classification ──────────────────────────────────────────

    def test_model_family_opus(self):
        ctx = self._call(_minimal_data(model={'id': 'claude-opus-4-6', 'display_name': 'Claude Opus 4.6'}))
        self.assertEqual(ctx['model_family'], 'opus')

    def test_model_family_opus_4_7(self):
        ctx = self._call(_minimal_data(model={'id': 'claude-opus-4-7', 'display_name': 'Claude Opus 4.7'}))
        self.assertEqual(ctx['model_family'], 'opus')

    def test_model_family_haiku(self):
        ctx = self._call(_minimal_data(model={'id': 'claude-haiku-4-5', 'display_name': 'Claude Haiku 4.5'}))
        self.assertEqual(ctx['model_family'], 'haiku')

    def test_model_family_sonnet_default(self):
        ctx = self._call(_minimal_data(model={'id': 'claude-sonnet-4-6', 'display_name': 'Claude Sonnet 4.6'}))
        self.assertEqual(ctx['model_family'], 'sonnet')

    def test_model_family_fallback_to_sonnet(self):
        # Unknown model id → falls to else branch → 'sonnet'
        ctx = self._call(_minimal_data(model={'id': 'claude-future-99', 'display_name': 'Claude Future'}))
        self.assertEqual(ctx['model_family'], 'sonnet')

    # ── context window string ────────────────────────────────────────────────

    def test_cw_str_1m(self):
        ctx = self._call(_minimal_data(context_window={'used_percentage': 10.0, 'context_window_size': 1_000_000}))
        self.assertEqual(ctx['cw_str'], '1M')

    def test_cw_str_200k(self):
        ctx = self._call(_minimal_data(context_window={'used_percentage': 10.0, 'context_window_size': 200_000}))
        self.assertEqual(ctx['cw_str'], '200k')

    def test_cw_str_0_is_empty(self):
        ctx = self._call(_minimal_data(context_window={'used_percentage': 10.0, 'context_window_size': 0}))
        self.assertEqual(ctx['cw_str'], '')

    def test_cw_str_500_is_empty(self):
        # < 1000 → no k or M suffix
        ctx = self._call(_minimal_data(context_window={'used_percentage': 10.0, 'context_window_size': 500}))
        self.assertEqual(ctx['cw_str'], '')

    def test_cw_str_10m(self):
        ctx = self._call(_minimal_data(context_window={'used_percentage': 25.0, 'context_window_size': 10_000_000}))
        self.assertEqual(ctx['cw_str'], '10M')

    # ── user_short ───────────────────────────────────────────────────────────

    def test_user_short_is_first_two_chars_of_username(self):
        ctx = self._call(_minimal_data())
        # _find_claude_account returns 'user@example.com' → 'user'[:2] → 'us'
        self.assertEqual(ctx['user_short'], 'us')

    def test_user_short_empty_when_no_account(self):
        with patch.object(core, 'safe_write_json'), \
             patch.object(core, 'safe_read_json', return_value={}), \
             patch.object(core, '_collect_git', return_value={
                 'branch': '', 'detached': False, 'dirty': 0,
                 'ahead': 0, 'behind': 0, 'stash': 0,
                 'remote_short': '', 'worktree': '', 'operation': '',
             }), \
             patch.object(core, '_find_claude_account', return_value=''), \
             patch.object(core, '_rotate_log', return_value=False), \
             patch.object(core, '_rebuild_logged_windows', return_value={'five_hour': {}, 'seven_day': {}}):
            ctx = core.build_context(data=_minimal_data())
        self.assertEqual(ctx['user_short'], '')

    # ── effort ───────────────────────────────────────────────────────────────

    def test_effort_present(self):
        data = _minimal_data()
        data['effort'] = 'high'
        ctx = self._call(data)
        self.assertEqual(ctx['effort'], 'high')

    def test_effort_absent_is_none(self):
        ctx = self._call(_minimal_data())
        self.assertIsNone(ctx['effort'])

    # ── path_display ─────────────────────────────────────────────────────────

    def test_path_display_set_when_cwd_present(self):
        ctx = self._call(_minimal_data(cwd='/home/user/code'))
        self.assertEqual(ctx['path_display'], '/home/user/code')

    def test_path_display_empty_when_no_cwd(self):
        data = _minimal_data()
        del data['cwd']
        ctx = self._call(data)
        self.assertEqual(ctx['path_display'], '')

    # ── rate_limits list structure ───────────────────────────────────────────

    def test_rate_limits_is_list_of_two(self):
        ctx = self._call(_minimal_data())
        self.assertIsInstance(ctx['rate_limits'], list)
        self.assertEqual(len(ctx['rate_limits']), 2)

    def test_rate_limits_keys_are_five_hour_and_seven_day(self):
        ctx = self._call(_minimal_data())
        keys = {r['key'] for r in ctx['rate_limits']}
        self.assertEqual(keys, {'five_hour', 'seven_day'})

    # ── missing optional data gracefully handled ──────────────────────────────

    def test_no_model_key(self):
        data = _minimal_data()
        del data['model']
        ctx = self._call(data)
        self.assertEqual(ctx['model_display'], 'Claude')
        self.assertEqual(ctx['model_id'], '')

    def test_no_context_window_key(self):
        data = _minimal_data()
        del data['context_window']
        ctx = self._call(data)
        self.assertIsNone(ctx['used_pct'])
        self.assertEqual(ctx['cw_size'], 0)

    def test_no_rate_limits_key(self):
        data = _minimal_data()
        del data['rate_limits']
        ctx = self._call(data)
        self.assertIsInstance(ctx['rate_limits'], list)


# ── 9. render_standard ───────────────────────────────────────────────────────

class TestRenderStandard(unittest.TestCase):

    def _minimal_ctx(self, **overrides):
        """Build a minimal context dict suitable for render_standard."""
        ctx = {
            'model_name': 'Sn46',
            'model_id': 'claude-sonnet-4-6',
            'model_family': 'sonnet',
            'model_display': 'Claude Sonnet 4.6',
            'cw_size': 200_000,
            'cw_str': '200k',
            'used_pct': 42.0,
            'cwd': '/home/user/project',
            'path_display': '/home/user/project',
            'email': 'test@example.com',
            'user_short': 'te',
            'effort': None,
            'rate_limits': [
                {'key': 'five_hour', 'label': '5h', 'pct': 30, 'reset_str': '', 'resets_at': None},
                {'key': 'seven_day', 'label': '7d', 'pct': 10, 'reset_str': '', 'resets_at': None},
            ],
            'session_dur': '5m30s',
            'session_elapsed': 330,
            'git': {
                'branch': 'main', 'detached': False, 'dirty': 0,
                'ahead': 0, 'behind': 0, 'stash': 0,
                'remote_short': '', 'worktree': '', 'operation': '',
            },
            'config': dict(core.DEFAULT_CONFIG),
        }
        ctx.update(overrides)
        return ctx

    def _minimal_theme(self):
        """Minimal theme config for render_standard."""
        grad = [240] * 20
        return {
            'sep': ' | ',
            'grad': grad,
            'tier': {'opus': 160, 'sonnet': 75, 'haiku': 220},
            'tier_default': 240,
            'colors': {
                'user': 255, 'effort': 200, 'duration': 240,
                'empty_bar': 235,
                'rl_label': 240, 'rl_reset': 235, 'rl_null': 235,
                'operation': 196, 'worktree': 200,
                'branch': 114, 'detached': 196,
                'remote_arrow': 240, 'remote': 110,
                'ahead': 114, 'behind': 209,
                'dirty': 215, 'stash': 104, 'path': 223,
            },
        }

    def test_output_is_nonempty_string(self):
        out = core.render_standard(self._minimal_ctx(), self._minimal_theme())
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 0)

    def test_output_contains_newline_when_git_branch_present(self):
        # Line 2 has git branch info → output should have a newline
        out = core.render_standard(self._minimal_ctx(), self._minimal_theme())
        self.assertIn('\n', out)

    def test_model_name_appears_in_output(self):
        ctx = self._minimal_ctx(model_name='Op46')
        out = strip_ansi(core.render_standard(ctx, self._minimal_theme()))
        self.assertIn('Op46', out)

    def test_context_window_str_appears_in_output(self):
        out = strip_ansi(core.render_standard(self._minimal_ctx(), self._minimal_theme()))
        self.assertIn('200k', out)

    def test_used_pct_appears_in_output(self):
        out = strip_ansi(core.render_standard(self._minimal_ctx(), self._minimal_theme()))
        self.assertIn('42%', out)

    def test_session_dur_appears_in_output(self):
        out = strip_ansi(core.render_standard(self._minimal_ctx(), self._minimal_theme()))
        self.assertIn('5m30s', out)

    def test_branch_appears_on_line2(self):
        ctx = self._minimal_ctx()
        ctx['git']['branch'] = 'feature/test'
        out = strip_ansi(core.render_standard(ctx, self._minimal_theme()))
        self.assertIn('feature/test', out)

    def test_path_appears_on_line2(self):
        out = strip_ansi(core.render_standard(self._minimal_ctx(), self._minimal_theme()))
        self.assertIn('/home/user/project', out)

    def test_no_user_when_user_short_empty(self):
        ctx = self._minimal_ctx(user_short='')
        out = strip_ansi(core.render_standard(ctx, self._minimal_theme()))
        # user_short is empty → user chip should not be in line 1 parts
        # Cannot assert 'te' absent in general, but 'te' came from user_short
        self.assertNotIn('te', out)

    def test_show_user_false_hides_user(self):
        ctx = self._minimal_ctx()
        ctx['config'] = dict(core.DEFAULT_CONFIG)
        ctx['config']['show_user'] = False
        out = strip_ansi(core.render_standard(ctx, self._minimal_theme()))
        self.assertNotIn('te', out)

    def test_effort_appears_when_set(self):
        ctx = self._minimal_ctx(effort='high')
        out = strip_ansi(core.render_standard(ctx, self._minimal_theme()))
        self.assertIn('high', out)

    def test_effort_absent_when_none(self):
        ctx = self._minimal_ctx(effort=None)
        out = strip_ansi(core.render_standard(ctx, self._minimal_theme()))
        # No effort string should appear where effort would be
        # (We just verify the output is still well-formed)
        self.assertIsInstance(out, str)

    def test_dirty_files_shown(self):
        ctx = self._minimal_ctx()
        ctx['git']['dirty'] = 5
        out = strip_ansi(core.render_standard(ctx, self._minimal_theme()))
        self.assertIn('+5', out)

    def test_stash_shown(self):
        ctx = self._minimal_ctx()
        ctx['git']['stash'] = 2
        out = strip_ansi(core.render_standard(ctx, self._minimal_theme()))
        self.assertIn('2', out)

    def test_ahead_shown(self):
        ctx = self._minimal_ctx()
        ctx['git']['ahead'] = 3
        out = strip_ansi(core.render_standard(ctx, self._minimal_theme()))
        self.assertIn('3', out)

    def test_detached_shows_detached_suffix(self):
        ctx = self._minimal_ctx()
        ctx['git']['detached'] = True
        ctx['git']['branch'] = 'abc1234'
        out = strip_ansi(core.render_standard(ctx, self._minimal_theme()))
        self.assertIn('abc1234', out)
        self.assertIn('det', out)

    def test_no_line2_when_no_git_and_no_path(self):
        ctx = self._minimal_ctx(path_display='')
        ctx['git'] = {
            'branch': '', 'detached': False, 'dirty': 0,
            'ahead': 0, 'behind': 0, 'stash': 0,
            'remote_short': '', 'worktree': '', 'operation': '',
        }
        out = core.render_standard(ctx, self._minimal_theme())
        # No line 2 content → no newline
        self.assertNotIn('\n', out)

    def test_rate_limit_pct_none_shows_null_label(self):
        ctx = self._minimal_ctx()
        ctx['rate_limits'] = [
            {'key': 'five_hour', 'label': '5h', 'pct': None, 'reset_str': '', 'resets_at': None},
        ]
        out = strip_ansi(core.render_standard(ctx, self._minimal_theme()))
        # Sonnet sends empty rate_limits; null pct windows should be hidden, not show "--"
        self.assertNotIn('5h', out)

    def test_line2_prefix_prepended(self):
        ctx = self._minimal_ctx()
        theme = self._minimal_theme()
        theme['line2_prefix'] = 'PREFIX> '
        out = strip_ansi(core.render_standard(ctx, theme))
        lines = out.split('\n')
        self.assertEqual(len(lines), 2)
        self.assertIn('PREFIX>', lines[1])

    def test_separator_used_between_line1_parts(self):
        ctx = self._minimal_ctx()
        theme = self._minimal_theme()
        theme['sep'] = '---SEP---'
        out = strip_ansi(core.render_standard(ctx, theme))
        self.assertIn('---SEP---', out)

    def test_operation_shown_when_present(self):
        ctx = self._minimal_ctx()
        ctx['git']['operation'] = 'MERGE'
        out = strip_ansi(core.render_standard(ctx, self._minimal_theme()))
        self.assertIn('MERGE', out)

    def test_worktree_shown_when_present(self):
        ctx = self._minimal_ctx()
        ctx['git']['worktree'] = 'feature-worktree'
        out = strip_ansi(core.render_standard(ctx, self._minimal_theme()))
        self.assertIn('feature-worktree', out)


# ── 10. All 14 themes import and render without crashing ────────────────────

_THEME_NAMES = [
    'buddy', 'monochrome', 'matrix', 'dracula', 'catppuccin',
    'outrun', 'amber', 'ibm3278', 'c64', 'win95',
    'teletext', 'lcars', 'rainbow', 'skittles',
]

def _make_full_ctx():
    """Build a representative context dict for theme smoke tests."""
    return {
        'model_name': 'Op46',
        'model_id': 'claude-opus-4-6',
        'model_family': 'opus',
        'model_display': 'Claude Opus 4.6',
        'cw_size': 1_000_000,
        'cw_str': '1M',
        'used_pct': 65.0,
        'cwd': '/home/user/project',
        'path_display': '/home/user/project',
        'email': 'dev@example.com',
        'user_short': 'de',
        'effort': None,
        'rate_limits': [
            {'key': 'five_hour', 'label': '5h', 'pct': 42, 'reset_str': '3p', 'resets_at': _future_epoch()},
            {'key': 'seven_day', 'label': '7d', 'pct': 15, 'reset_str': '',   'resets_at': _future_epoch()},
        ],
        'session_dur': '12m00s',
        'session_elapsed': 720,
        'git': {
            'branch': 'main', 'detached': False, 'dirty': 2,
            'ahead': 1, 'behind': 0, 'stash': 0,
            'remote_short': 'gh:owner', 'worktree': '', 'operation': '',
        },
        'config': dict(core.DEFAULT_CONFIG),
    }


class TestAllThemesSmoke(unittest.TestCase):
    """Import every theme and call render(ctx). None should raise."""

    def _render_theme(self, name):
        import importlib
        mod = importlib.import_module(name)
        ctx = _make_full_ctx()
        result = mod.render(ctx)
        return result

    def test_buddy_renders(self):
        out = self._render_theme('buddy')
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 0)

    def test_monochrome_renders(self):
        out = self._render_theme('monochrome')
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 0)

    def test_matrix_renders(self):
        out = self._render_theme('matrix')
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 0)

    def test_dracula_renders(self):
        out = self._render_theme('dracula')
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 0)

    def test_catppuccin_renders(self):
        out = self._render_theme('catppuccin')
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 0)

    def test_outrun_renders(self):
        out = self._render_theme('outrun')
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 0)

    def test_amber_renders(self):
        out = self._render_theme('amber')
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 0)

    def test_ibm3278_renders(self):
        out = self._render_theme('ibm3278')
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 0)

    def test_c64_renders(self):
        out = self._render_theme('c64')
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 0)

    def test_win95_renders(self):
        out = self._render_theme('win95')
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 0)

    def test_teletext_renders(self):
        out = self._render_theme('teletext')
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 0)

    def test_lcars_renders(self):
        out = self._render_theme('lcars')
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 0)

    def test_rainbow_renders(self):
        out = self._render_theme('rainbow')
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 0)

    def test_skittles_renders(self):
        out = self._render_theme('skittles')
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 0)

    def test_all_themes_produce_nonempty_output(self):
        """Meta-test: parameterised smoke run to catch any theme not covered above."""
        import importlib
        ctx = _make_full_ctx()
        for name in _THEME_NAMES:
            with self.subTest(theme=name):
                mod = importlib.import_module(name)
                out = mod.render(ctx)
                self.assertIsInstance(out, str)
                self.assertGreater(len(strip_ansi(out)), 0,
                                   f'Theme {name} produced empty output')

    def test_all_themes_render_with_pct_none(self):
        """Themes must handle used_pct=None (no context window data) without crashing."""
        import importlib
        ctx = _make_full_ctx()
        ctx['used_pct'] = None
        ctx['cw_str'] = ''
        for name in _THEME_NAMES:
            with self.subTest(theme=name):
                mod = importlib.import_module(name)
                out = mod.render(ctx)
                self.assertIsInstance(out, str)

    def test_all_themes_render_with_empty_git(self):
        """Themes must handle empty git state (not in a repo) without crashing."""
        import importlib
        ctx = _make_full_ctx()
        ctx['git'] = {
            'branch': '', 'detached': False, 'dirty': 0,
            'ahead': 0, 'behind': 0, 'stash': 0,
            'remote_short': '', 'worktree': '', 'operation': '',
        }
        for name in _THEME_NAMES:
            with self.subTest(theme=name):
                mod = importlib.import_module(name)
                out = mod.render(ctx)
                self.assertIsInstance(out, str)

    def test_all_themes_render_with_rl_pct_none(self):
        """Themes must handle rate limit entries where pct=None."""
        import importlib
        ctx = _make_full_ctx()
        ctx['rate_limits'] = [
            {'key': 'five_hour', 'label': '5h', 'pct': None, 'reset_str': '', 'resets_at': None},
            {'key': 'seven_day', 'label': '7d', 'pct': None, 'reset_str': '', 'resets_at': None},
        ]
        for name in _THEME_NAMES:
            with self.subTest(theme=name):
                mod = importlib.import_module(name)
                out = mod.render(ctx)
                self.assertIsInstance(out, str)

    def test_all_themes_render_with_detached_head(self):
        """Themes must handle detached HEAD state (common during rebases)."""
        import importlib
        ctx = _make_full_ctx()
        ctx['git']['detached'] = True
        ctx['git']['branch'] = 'abc1234'
        for name in _THEME_NAMES:
            with self.subTest(theme=name):
                mod = importlib.import_module(name)
                out = mod.render(ctx)
                self.assertIsInstance(out, str)


# ── 11. Gradient helpers ─────────────────────────────────────────────────────

class TestGradientHelpers(unittest.TestCase):

    def test_std_grad_color_0pct(self):
        grad = list(range(20))
        # 0% → index 0
        self.assertEqual(core._std_grad_color(0, grad), 0)

    def test_std_grad_color_100pct(self):
        grad = list(range(20))
        # 100% → index 19
        self.assertEqual(core._std_grad_color(100, grad), 19)

    def test_std_grad_color_50pct(self):
        grad = list(range(20))
        # 50% → int(50/100 * 19) = 9
        self.assertEqual(core._std_grad_color(50, grad), 9)

    def test_std_grad_color_clamped_above_100(self):
        grad = list(range(20))
        # min(int(150/100*19), 19) = min(28, 19) = 19
        self.assertEqual(core._std_grad_color(150, grad), 19)


# ── 12. safe_read_json / safe_write_json ─────────────────────────────────────

class TestSafeJson(unittest.TestCase):

    def test_safe_read_missing_file_returns_empty_dict(self):
        result = core.safe_read_json('/tmp/does_not_exist_abc123.json')
        self.assertEqual(result, {})

    def test_safe_read_empty_file_returns_empty_dict(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('')
            path = f.name
        try:
            result = core.safe_read_json(path)
            self.assertEqual(result, {})
        finally:
            os.unlink(path)

    def test_safe_read_corrupt_json_returns_empty_dict(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{{not valid json!!!')
            path = f.name
        try:
            result = core.safe_read_json(path)
            self.assertEqual(result, {})
        finally:
            os.unlink(path)

    def test_safe_read_valid_json(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'key': 'value', 'num': 42}, f)
            path = f.name
        try:
            result = core.safe_read_json(path)
            self.assertEqual(result, {'key': 'value', 'num': 42})
        finally:
            os.unlink(path)

    def test_safe_write_then_read_roundtrip(self):
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = f.name
        try:
            data = {'a': 1, 'b': [1, 2, 3]}
            core.safe_write_json(path, data)
            result = core.safe_read_json(path)
            self.assertEqual(result, data)
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass

    def test_safe_write_to_unwritable_path_does_not_raise(self):
        # Writing to a bad path should silently fail, not raise
        try:
            core.safe_write_json('/no/such/directory/state.json', {'x': 1})
        except Exception as e:
            self.fail(f'safe_write_json raised unexpectedly: {e}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
