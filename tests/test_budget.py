import importlib.util
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest

SRC = Path(__file__).resolve().parents[1] / "custom_components" / "safeconnect" / "budget.py"
spec = importlib.util.spec_from_file_location("safeconnect_budget_test", SRC)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
RequestBudget = module.RequestBudget
retry_after_seconds = module.retry_after_seconds


def test_budget_covers_restarts():
    now = 1792920000.0
    state = RequestBudget()
    assert state.allowed(now)
    state.mark_started(now, 60)
    restored = RequestBudget(next_allowed=state.next_allowed)
    assert not restored.allowed(now + 10)
    assert not restored.allowed(now + 3599)
    assert restored.allowed(now + 3600)


def test_minimum_budget_is_one_minute():
    b = RequestBudget()
    b.mark_started(100, 1)
    assert b.next_allowed == 160


def test_once_per_minute_budget_and_restart_guard():
    start = 1792965844.7303603
    budget = RequestBudget()
    assert budget.allowed(start)
    budget.mark_started(start, 1)
    for seconds in (0, 10, 30, 59.9):
        restored = RequestBudget(next_allowed=budget.next_allowed)
        assert not restored.allowed(start + seconds)
    assert RequestBudget(next_allowed=budget.next_allowed).allowed(start + 60)


def test_owner_can_choose_slower_polling():
    budget = RequestBudget()
    budget.mark_started(100, 30)
    assert budget.next_allowed == 1900


def test_429_circuit_breaker_and_forbidden():
    b = RequestBudget()
    b.throttle(100, 8000)
    assert b.next_allowed == 8100
    assert not b.allowed(8100 - 1)
    b.forbid()
    assert not b.allowed(10**15)


def test_retry_after_date_and_seconds():
    now = datetime(2026, 10, 25, tzinfo=timezone.utc)
    assert retry_after_seconds("180", now=now) == 180
    assert retry_after_seconds("Sun, 25 Oct 2026 00:05:00 GMT", now=now) == 300
    assert retry_after_seconds("suspicious", now=now) == 0
    assert retry_after_seconds("100000000", now=now) == 604800


def test_local_tick_does_not_remove_hourly_budget_across_restarts():
    first = 1792965844.476324
    state = RequestBudget()
    state.mark_started(first, 60)
    for minute in range(1, 60):
        state = RequestBudget(next_allowed=state.next_allowed)
        assert not state.allowed(first + minute * 60)
    assert state.allowed(first + 3600)
