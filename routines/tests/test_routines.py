import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import routines  # noqa: E402


# --- parse_cron ---


def test_parse_cron_daily():
    assert routines.parse_cron("0 8 * * *") == {"kind": "daily", "minute": 0, "hour": 8}


def test_parse_cron_weekly():
    assert routines.parse_cron("30 9 * * 1") == {
        "kind": "weekly",
        "minute": 30,
        "hour": 9,
        "dow": 1,
    }


def test_parse_cron_monthly():
    assert routines.parse_cron("0 19 20 * *") == {
        "kind": "monthly",
        "minute": 0,
        "hour": 19,
        "dom": 20,
    }


@pytest.mark.parametrize(
    "s",
    [
        "0 8 * *",  # フィールド数違い(4)
        "*/5 8 * * *",  # */n
        "0,30 8 * * *",  # カンマ
        "0 8 * 3 *",  # 月指定
        "0 8 15 * 3",  # 曜日と日同時指定
    ],
)
def test_parse_cron_invalid(s):
    with pytest.raises(ValueError):
        routines.parse_cron(s)


# --- to_oncalendar ---


def test_to_oncalendar_daily():
    assert (
        routines.to_oncalendar({"kind": "daily", "minute": 0, "hour": 8})
        == "*-*-* 08:00:00"
    )


def test_to_oncalendar_weekly():
    assert (
        routines.to_oncalendar({"kind": "weekly", "minute": 30, "hour": 9, "dow": 1})
        == "Mon *-*-* 09:30:00"
    )


def test_to_oncalendar_monthly():
    assert (
        routines.to_oncalendar({"kind": "monthly", "minute": 0, "hour": 19, "dom": 20})
        == "*-*-20 19:00:00"
    )


# --- to_schtasks_args ---


def test_to_schtasks_args_daily():
    result = routines.to_schtasks_args(
        "Name", {"kind": "daily", "minute": 0, "hour": 8}, "cmd"
    )
    assert result == [
        "schtasks",
        "/create",
        "/tn",
        "Name",
        "/tr",
        "cmd",
        "/sc",
        "DAILY",
        "/st",
        "08:00",
        "/f",
    ]


def test_to_schtasks_args_weekly():
    result = routines.to_schtasks_args(
        "Name", {"kind": "weekly", "minute": 0, "hour": 9, "dow": 0}, "cmd"
    )
    assert result == [
        "schtasks",
        "/create",
        "/tn",
        "Name",
        "/tr",
        "cmd",
        "/sc",
        "WEEKLY",
        "/d",
        "SUN",
        "/st",
        "09:00",
        "/f",
    ]


def test_to_schtasks_args_monthly():
    result = routines.to_schtasks_args(
        "Name", {"kind": "monthly", "minute": 0, "hour": 19, "dom": 20}, "cmd"
    )
    assert result == [
        "schtasks",
        "/create",
        "/tn",
        "Name",
        "/tr",
        "cmd",
        "/sc",
        "MONTHLY",
        "/d",
        "20",
        "/st",
        "19:00",
        "/f",
    ]


# --- resolve_command ---


def test_resolve_command_logical_name():
    result = routines.resolve_command(
        "pwsh -NoProfile -File script.ps1",
        "",
        True,
        lambda n: {"pwsh": "C:\\Tools\\pwsh.exe"}.get(n),
    )
    assert result == "C:\\Tools\\pwsh.exe -NoProfile -File script.ps1"


def test_resolve_command_venv_python_windows():
    result = routines.resolve_command(
        "venv-python fetch.py", "C:\\proj", True, lambda n: None
    )
    assert result == "C:\\proj\\.venv\\Scripts\\python.exe fetch.py"


def test_resolve_command_venv_python_linux():
    result = routines.resolve_command(
        "venv-python fetch.py", "/home/user/proj", False, lambda n: None
    )
    assert result == "/home/user/proj/.venv/bin/python fetch.py"


def test_resolve_command_resolves_token_after_double_dash():
    def which(n: str) -> str | None:
        return {"dotenvx": "/usr/bin/dotenvx", "uv": "/usr/bin/uv"}.get(n)

    result = routines.resolve_command(
        "dotenvx run -- uv run python x.py", "", False, which
    )
    assert result == "/usr/bin/dotenvx run -- /usr/bin/uv run python x.py"


def test_resolve_command_which_failure_raises():
    with pytest.raises(ValueError):
        routines.resolve_command("pwsh -File x.ps1", "", True, lambda n: None)


def test_resolve_command_tilde_expansion():
    result = routines.resolve_command(
        "python ~/scripts/x.py",
        "",
        True,
        lambda n: {"python": "C:\\Python\\python.exe"}.get(n),
    )
    home = os.path.expanduser("~")
    expected_tail = (home + "\\scripts\\x.py").replace("/", "\\")
    assert result == f"C:\\Python\\python.exe {expected_tail}"


# --- systemd_units ---


def test_systemd_units_multiple_exec_start():
    routine = {
        "name": "ADA-HealthFetch",
        "description": "desc",
        "schedule": "0 9 * * *",
        "commands": ["dotenvx run -- uv run python fetch_health.py"],
        "workdir": "/home/user/health_sync",
        "enabled": True,
    }
    resolved = [
        "/usr/bin/python fetch_health.py",
        "/usr/bin/python health_verify.py",
    ]
    service, timer = routines.systemd_units(routine, resolved)
    assert service.count("ExecStart=") == 2
    assert "ExecStart=/usr/bin/python fetch_health.py" in service
    assert "ExecStart=/usr/bin/python health_verify.py" in service
    assert "WorkingDirectory=/home/user/health_sync" in service
    assert "Type=oneshot" in service


def test_unit_basename():
    assert routines.unit_basename("ADA Security Audit") == "ada-security-audit"


def test_systemd_units_oncalendar():
    routine = {
        "name": "ADA-HealthTrend",
        "description": "d",
        "schedule": "30 9 * * 1",
        "commands": [],
        "workdir": "",
        "enabled": True,
    }
    service, timer = routines.systemd_units(routine, [])
    assert "OnCalendar=Mon *-*-* 09:30:00" in timer
    assert "Persistent=true" in timer
    assert "WantedBy=timers.target" in timer


# --- load_manifest ---


def test_load_manifest_real_file():
    toml_path = Path(__file__).resolve().parent.parent / "routines.toml"
    routines_list = routines.load_manifest(toml_path)
    assert len(routines_list) == 8
    names = {r["name"] for r in routines_list}
    assert "ADA Security Audit" in names
    assert "ZundamonShindan" in names


def test_load_manifest_duplicate_name(tmp_path):
    content = """
[[routine]]
name = "Dup"
description = "d"
schedule = "0 8 * * *"
commands = ["python x.py"]
workdir = ""
enabled = true

[[routine]]
name = "Dup"
description = "d2"
schedule = "0 9 * * *"
commands = ["python y.py"]
workdir = ""
enabled = true
"""
    p = tmp_path / "dup.toml"
    p.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        routines.load_manifest(p)


# --- parse_task_xml ---

_WEEKLY_XML = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-07-11T18:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByWeek>
        <DaysOfWeek>
          <Sunday />
        </DaysOfWeek>
        <WeeksInterval>1</WeeksInterval>
      </ScheduleByWeek>
    </CalendarTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>C:\\Program Files\\PowerShell\\7\\pwsh.exe</Command>
      <Arguments>-NoProfile -File C:\\skills\\security-audit\\run-audit.ps1</Arguments>
      <WorkingDirectory>C:\\Users\\nov26</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""

_MONTHLY_XML = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-07-20T19:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByMonth>
        <DaysOfMonth>
          <Day>20</Day>
        </DaysOfMonth>
        <Months>
          <January />
        </Months>
      </ScheduleByMonth>
    </CalendarTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>C:\\Users\\nov26\\.local\\bin\\uv.exe</Command>
      <Arguments>run --project C:\\skills\\evaluator python eval_collect.py --write</Arguments>
      <WorkingDirectory></WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""

_DAILY_XML = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-07-11T08:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>C:\\Users\\nov26\\.local\\bin\\python.exe</Command>
      <Arguments>triage.py</Arguments>
      <WorkingDirectory>C:\\Users\\nov26\\.claude\\ada\\loops\\daily-triage</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


def test_parse_task_xml_weekly():
    result = routines.parse_task_xml(_WEEKLY_XML)
    assert result["kind"] == "weekly"
    assert result["hour"] == 18
    assert result["minute"] == 0
    assert result["dow"] == 0
    assert result["workdir"] == "C:\\Users\\nov26"
    assert any("run-audit.ps1" in c for c in result["commands"])


def test_parse_task_xml_monthly():
    result = routines.parse_task_xml(_MONTHLY_XML)
    assert result["kind"] == "monthly"
    assert result["hour"] == 19
    assert result["minute"] == 0
    assert result["dom"] == 20
    assert any("eval_collect.py" in c for c in result["commands"])


def test_parse_task_xml_daily():
    result = routines.parse_task_xml(_DAILY_XML)
    assert result["kind"] == "daily"
    assert result["hour"] == 8
    assert result["minute"] == 0
    assert result["workdir"] == "C:\\Users\\nov26\\.claude\\ada\\loops\\daily-triage"
    assert any("triage.py" in c for c in result["commands"])


# --- diff_routine ---


def test_diff_routine_match():
    workdir_expanded = os.path.expanduser("~/.claude/ada/loops/daily-triage")
    manifest_r = {
        "name": "ADA-DailyTriage",
        "schedule": "0 8 * * *",
        "commands": ["python triage.py"],
        "workdir": "~/.claude/ada/loops/daily-triage",
    }
    live = {
        "kind": "daily",
        "minute": 0,
        "hour": 8,
        "commands": ["C:\\tools\\python.exe triage.py"],
        "workdir": workdir_expanded,
    }
    assert routines.diff_routine(manifest_r, live) == []


def test_diff_routine_missing():
    manifest_r = {"name": "X", "schedule": "0 8 * * *", "commands": [], "workdir": ""}
    assert routines.diff_routine(manifest_r, None) == ["missing"]


def test_diff_routine_schedule_mismatch():
    manifest_r = {"name": "X", "schedule": "0 8 * * *", "commands": [], "workdir": ""}
    live = {"kind": "daily", "minute": 30, "hour": 8, "commands": [], "workdir": ""}
    diffs = routines.diff_routine(manifest_r, live)
    assert len(diffs) == 1
    assert diffs[0].startswith("schedule:")


def test_diff_routine_command_hint_mismatch():
    manifest_r = {
        "name": "X",
        "schedule": "0 8 * * *",
        "commands": ["python triage.py"],
        "workdir": "",
    }
    live = {
        "kind": "daily",
        "minute": 0,
        "hour": 8,
        "commands": ["C:\\tools\\python.exe other.py"],
        "workdir": "",
    }
    diffs = routines.diff_routine(manifest_r, live)
    assert any("triage.py" in d for d in diffs)


def test_diff_routine_workdir_mismatch():
    manifest_r = {
        "name": "X",
        "schedule": "0 8 * * *",
        "commands": [],
        "workdir": "~/foo",
    }
    live = {
        "kind": "daily",
        "minute": 0,
        "hour": 8,
        "commands": [],
        "workdir": "C:\\Users\\nov26\\bar",
    }
    diffs = routines.diff_routine(manifest_r, live)
    assert any(d.startswith("workdir:") for d in diffs)
