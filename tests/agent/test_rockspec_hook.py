"""VALOR-FORK: rockspec-loop-hook-fallback

Unit tests for `AIAgent._check_rockspec_stop_contract` and its helpers.

Verifies every `action` branch (inject / bypass_*) and the fallback guard that
short-circuits continuation when the latest user message is external (not
self-injected by the hook) and the agent has already written to state in the
current turn.

Tests bypass `AIAgent.__init__` via `__new__` and set only the attributes the
hook reads, so no real provider / model / config is required.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

import pytest

from run_agent import AIAgent


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


def _make_agent(
    *,
    working_dir: Optional[Path],
    state_seq_before: Optional[int] = None,
    continuation_count: int = 0,
    session_id: str = "test-session",
) -> AIAgent:
    agent = AIAgent.__new__(AIAgent)
    if working_dir is None:
        agent.ephemeral_system_prompt = "You are a helpful assistant.\n"
    else:
        agent.ephemeral_system_prompt = (
            f"DEFAULT_WORKING_DIRECTORY={working_dir}\n"
            "You are a helpful assistant working in the sandbox.\n"
        )
    agent._rockspec_turn_state_seq_before = state_seq_before
    agent._rockspec_contract_continuations = continuation_count
    agent._rockspec_prev_was_hook = False
    agent._session_messages = None
    agent.session_id = session_id
    return agent


def _write_state(
    root: Path,
    *,
    status: str = "in_progress",
    loop_paused: bool = False,
    next_action: str = "finish the test contract",
    state_seq: int = 5,
    extra: Optional[dict] = None,
) -> Path:
    state_dir = root / ".rockspec-loop" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "framework": "rockspec-loop",
        "version": 2,
        "state_seq": state_seq,
        "status": status,
        "loop_paused": loop_paused,
        "next_action": next_action,
    }
    if extra:
        payload.update(extra)
    state_path = state_dir / "current.yaml"
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    return state_path


def _hook_log_entries(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if "rockspec-loop hook decision" in r.getMessage()]


EXTERNAL_MSG = [{"role": "user", "content": "rockteam 看看這個狀況怎樣"}]
INJECTED_MSG = [
    {
        "role": "user",
        "content": (
            "[System: ROCKSPEC-LOOP STOP CONTRACT UNSATISFIED — "
            "The state file has been checked and the contract is NOT met."
        ),
    }
]


# ---------------------------------------------------------------------------
# bypass_* branches (short-circuit gates)
# ---------------------------------------------------------------------------


class TestBypassGates:
    def test_bypass_no_working_dir(self, caplog):
        agent = _make_agent(working_dir=None)
        caplog.set_level(logging.INFO)
        result = agent._check_rockspec_stop_contract(messages=EXTERNAL_MSG)
        assert result is None
        logs = _hook_log_entries(caplog)
        assert len(logs) == 1
        assert "action=bypass_no_working_dir" in logs[0].getMessage()

    def test_bypass_no_state(self, caplog, tmp_path):
        empty_dir = tmp_path / "no-state"
        empty_dir.mkdir()
        agent = _make_agent(working_dir=empty_dir)
        caplog.set_level(logging.INFO)
        result = agent._check_rockspec_stop_contract(messages=EXTERNAL_MSG)
        assert result is None
        assert "action=bypass_no_state" in _hook_log_entries(caplog)[0].getMessage()

    def test_bypass_parse_error(self, caplog, tmp_path):
        repo = tmp_path / "broken"
        state_dir = repo / ".rockspec-loop" / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "current.yaml").write_text("{ not valid json", encoding="utf-8")
        agent = _make_agent(working_dir=repo)
        caplog.set_level(logging.INFO)
        result = agent._check_rockspec_stop_contract(messages=EXTERNAL_MSG)
        assert result is None
        assert "action=bypass_parse_error" in _hook_log_entries(caplog)[0].getMessage()

    def test_bypass_loop_paused(self, caplog, tmp_path):
        repo = tmp_path / "paused"
        repo.mkdir()
        _write_state(repo, loop_paused=True)
        agent = _make_agent(working_dir=repo)
        caplog.set_level(logging.INFO)
        result = agent._check_rockspec_stop_contract(messages=EXTERNAL_MSG)
        assert result is None
        assert "action=bypass_loop_paused" in _hook_log_entries(caplog)[0].getMessage()

    def test_bypass_not_in_progress(self, caplog, tmp_path):
        repo = tmp_path / "done"
        repo.mkdir()
        _write_state(repo, status="completed")
        agent = _make_agent(working_dir=repo)
        caplog.set_level(logging.INFO)
        result = agent._check_rockspec_stop_contract(messages=EXTERNAL_MSG)
        assert result is None
        assert "action=bypass_not_in_progress" in _hook_log_entries(caplog)[0].getMessage()

    def test_bypass_empty_next_action(self, caplog, tmp_path):
        repo = tmp_path / "empty-contract"
        repo.mkdir()
        _write_state(repo, next_action="")
        agent = _make_agent(working_dir=repo)
        caplog.set_level(logging.INFO)
        result = agent._check_rockspec_stop_contract(messages=EXTERNAL_MSG)
        assert result is None
        assert "action=bypass_empty_next_action" in _hook_log_entries(caplog)[0].getMessage()


# ---------------------------------------------------------------------------
# Fallback guard (the behavioural core of this change)
# ---------------------------------------------------------------------------


class TestFallbackGuard:
    def test_bypass_fallback_external_user_with_state_write(self, caplog, tmp_path):
        """Agent has responded to external input AND written state -> release stop."""
        repo = tmp_path / "fallback"
        repo.mkdir()
        _write_state(repo, state_seq=11, next_action="keep observing watcher")
        agent = _make_agent(working_dir=repo, state_seq_before=10)
        caplog.set_level(logging.INFO)
        result = agent._check_rockspec_stop_contract(messages=EXTERNAL_MSG)
        assert result is None, "external user + state write should release stop"
        msg = _hook_log_entries(caplog)[0].getMessage()
        assert "action=bypass_fallback" in msg
        assert "is_hook_injected=False" in msg
        assert "agent_touched_state=True" in msg
        assert "state_seq_before=10" in msg
        assert "state_seq_after=11" in msg

    def test_inject_external_user_without_state_write(self, caplog, tmp_path):
        """External user input but agent did NOT write state -> still inject."""
        repo = tmp_path / "no-heartbeat"
        repo.mkdir()
        _write_state(repo, state_seq=10, next_action="keep observing watcher")
        agent = _make_agent(working_dir=repo, state_seq_before=10)
        caplog.set_level(logging.INFO)
        result = agent._check_rockspec_stop_contract(messages=EXTERNAL_MSG)
        assert result is not None, "no heartbeat means gates should trigger injection"
        assert "ROCKSPEC-LOOP STOP CONTRACT UNSATISFIED" in result
        msg = _hook_log_entries(caplog)[0].getMessage()
        assert "action=inject" in msg
        assert "agent_touched_state=False" in msg

    def test_inject_hook_injected_after_state_write(self, caplog, tmp_path):
        """Hook-injected message, even with state write, keeps original inject path."""
        repo = tmp_path / "self-injected"
        repo.mkdir()
        _write_state(repo, state_seq=12, next_action="keep observing watcher")
        agent = _make_agent(working_dir=repo, state_seq_before=10)
        caplog.set_level(logging.INFO)
        result = agent._check_rockspec_stop_contract(messages=INJECTED_MSG)
        assert result is not None, "hook-injected input must not be treated as external"
        msg = _hook_log_entries(caplog)[0].getMessage()
        assert "action=inject" in msg
        assert "is_hook_injected=True" in msg

    def test_inject_no_baseline(self, caplog, tmp_path):
        """No turn-init baseline -> agent_touched_state cannot be proven -> inject."""
        repo = tmp_path / "no-baseline"
        repo.mkdir()
        _write_state(repo, state_seq=11, next_action="keep observing watcher")
        agent = _make_agent(working_dir=repo, state_seq_before=None)
        caplog.set_level(logging.INFO)
        result = agent._check_rockspec_stop_contract(messages=EXTERNAL_MSG)
        assert result is not None
        assert "action=inject" in _hook_log_entries(caplog)[0].getMessage()


# ---------------------------------------------------------------------------
# Log contract
# ---------------------------------------------------------------------------


class TestLogContract:
    def test_log_emitted_exactly_once_per_call(self, caplog, tmp_path):
        repo = tmp_path / "log-shape"
        repo.mkdir()
        _write_state(repo, state_seq=11, next_action="finish")
        agent = _make_agent(working_dir=repo, state_seq_before=10, session_id="abc123")
        caplog.set_level(logging.INFO)
        agent._check_rockspec_stop_contract(messages=EXTERNAL_MSG)
        logs = _hook_log_entries(caplog)
        assert len(logs) == 1
        msg = logs[0].getMessage()
        for field in (
            "action=",
            "session=abc123",
            "user_msg_preview=",
            "is_hook_injected=",
            "agent_touched_state=",
            "state_seq_before=",
            "state_seq_after=",
            "continuation_count=",
        ):
            assert field in msg, f"missing field {field!r} in log: {msg}"

    def test_log_preview_strips_newlines_and_truncates(self, caplog, tmp_path):
        repo = tmp_path / "log-preview"
        repo.mkdir()
        _write_state(repo, state_seq=11, next_action="finish")
        long_msg = "line1\nline2\r\nline3 " + "X" * 200
        agent = _make_agent(working_dir=repo, state_seq_before=10)
        caplog.set_level(logging.INFO)
        agent._check_rockspec_stop_contract(
            messages=[{"role": "user", "content": long_msg}]
        )
        msg = _hook_log_entries(caplog)[0].getMessage()
        # Preview is repr-wrapped in the format string, so "\n" must be absent from the raw preview
        assert "\\n" not in msg.split("user_msg_preview=")[1].split(" is_hook_injected")[0] or "line1 line2 line3" in msg
        # And the visible substring should not contain the full 200 X's
        assert "X" * 200 not in msg

    def test_log_continuation_count_reflects_attr(self, caplog, tmp_path):
        repo = tmp_path / "log-count"
        repo.mkdir()
        _write_state(repo, state_seq=11, next_action="finish")
        agent = _make_agent(working_dir=repo, state_seq_before=10, continuation_count=3)
        caplog.set_level(logging.INFO)
        agent._check_rockspec_stop_contract(messages=EXTERNAL_MSG)
        msg = _hook_log_entries(caplog)[0].getMessage()
        assert "continuation_count=3/" in msg


# ---------------------------------------------------------------------------
# Helper surface
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_read_state_seq_returns_int(self, tmp_path):
        repo = tmp_path / "helper"
        repo.mkdir()
        _write_state(repo, state_seq=42, next_action="x")
        agent = _make_agent(working_dir=repo)
        assert agent._read_rockspec_state_seq() == 42

    def test_read_state_seq_missing_is_none(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        agent = _make_agent(working_dir=empty)
        assert agent._read_rockspec_state_seq() is None

    def test_resolve_state_path_uses_working_dir(self, tmp_path):
        repo = tmp_path / "resolve"
        repo.mkdir()
        sp = _write_state(repo, next_action="x")
        agent = _make_agent(working_dir=repo)
        assert agent._resolve_rockspec_state_path() == sp

    def test_resolve_state_path_none_without_prompt(self):
        agent = _make_agent(working_dir=None)
        assert agent._resolve_rockspec_state_path() is None
