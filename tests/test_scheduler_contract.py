"""Verify HA coordinator scheduler and API budget remain independent."""
import ast
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/"custom_components"/"safeconnect"

def test_local_tick_is_one_minute_but_cloud_budget_is_persisted():
    code=(ROOT/"coordinator.py").read_text()
    ast.parse(code)
    assert "update_interval=timedelta(minutes=1)" in code
    assert "if not self.budget.allowed(now):" in code
    assert code.index("if not self.budget.allowed(now):") < code.index("raw = await self.api.telemetry()")
    assert code.index("await self._save_now()") < code.index("raw = await self.api.telemetry()")
    assert "self.budget.mark_started(now, self.poll_minutes)" in code

def test_one_minute_cloud_queries_remain_budgeted():
    const = (ROOT / "const.py").read_text()
    budget = (ROOT / "budget.py").read_text()
    coordinator = (ROOT / "coordinator.py").read_text()
    assert "DEFAULT_POLL_MINUTES: Final = 1" in const
    assert "MIN_POLL_MINUTES: Final = 1" in const
    assert "max(1, interval_minutes)" in budget
    assert "self.poll_minutes = max(1, min(1440, requested_poll))" in coordinator
    assert "update_interval=timedelta(minutes=1)" in coordinator


def test_diagnostic_and_manifest_versions_match():
    version=json.loads((ROOT/"manifest.json").read_text())["version"]
    assert f'"version": "{version}"' in (ROOT/"diagnostics.py").read_text()
