#!/usr/bin/env python3
"""routines — ADA定期タスクのマニフェスト管理(Windows Task Scheduler / Linux systemd user timer)。

check(既定)=読み取り専用のドリフト検知。install=登録内容の生成(--applyで実登録)。
export=Windows上の実タスクからTOML雛形を出力。詳細はREADME.md参照。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable

_TASK_NS = "{http://schemas.microsoft.com/windows/2004/02/mit/task}"
_DOW_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
_DOW_FULL = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
]
_SCHTASKS_DOW = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
_LOGICAL_TOOLS = {"pwsh", "python", "uv", "dotenvx"}


# --- 純関数 ---


def parse_cron(s: str) -> dict:
    fields = s.split()
    if len(fields) != 5:
        raise ValueError(f"cron must have 5 fields: {s!r}")
    minute, hour, dom, month, dow = fields

    if not minute.isdigit() or not hour.isdigit():
        raise ValueError(f"minute/hour must be plain integers: {s!r}")
    if month != "*":
        raise ValueError(f"month field is not supported: {s!r}")
    if dom != "*" and dow != "*":
        raise ValueError(f"cannot specify both day-of-month and day-of-week: {s!r}")

    minute_i, hour_i = int(minute), int(hour)

    if dom == "*" and dow == "*":
        return {"kind": "daily", "minute": minute_i, "hour": hour_i}

    if dow != "*":
        if not dow.isdigit():
            raise ValueError(f"day-of-week must be a plain integer: {s!r}")
        dow_i = int(dow)
        if not 0 <= dow_i <= 6:
            raise ValueError(f"day-of-week out of range 0-6: {s!r}")
        return {"kind": "weekly", "minute": minute_i, "hour": hour_i, "dow": dow_i}

    if not dom.isdigit():
        raise ValueError(f"day-of-month must be a plain integer: {s!r}")
    return {"kind": "monthly", "minute": minute_i, "hour": hour_i, "dom": int(dom)}


def to_oncalendar(sched: dict) -> str:
    kind = sched["kind"]
    hh = f"{sched['hour']:02d}"
    mm = f"{sched['minute']:02d}"
    if kind == "daily":
        return f"*-*-* {hh}:{mm}:00"
    if kind == "weekly":
        return f"{_DOW_NAMES[sched['dow']]} *-*-* {hh}:{mm}:00"
    if kind == "monthly":
        dd = f"{sched['dom']:02d}"
        return f"*-*-{dd} {hh}:{mm}:00"
    raise ValueError(f"unknown schedule kind: {kind!r}")


def to_schtasks_args(name: str, sched: dict, cmdline: str) -> list[str]:
    kind = sched["kind"]
    st = f"{sched['hour']:02d}:{sched['minute']:02d}"
    base = ["schtasks", "/create", "/tn", name, "/tr", cmdline]
    if kind == "daily":
        return base + ["/sc", "DAILY", "/st", st, "/f"]
    if kind == "weekly":
        return base + [
            "/sc",
            "WEEKLY",
            "/d",
            _SCHTASKS_DOW[sched["dow"]],
            "/st",
            st,
            "/f",
        ]
    if kind == "monthly":
        return base + ["/sc", "MONTHLY", "/d", str(sched["dom"]), "/st", st, "/f"]
    raise ValueError(f"unknown schedule kind: {kind!r}")


def _expand_tilde(tok: str, is_windows: bool) -> str:
    if tok != "~" and not tok.startswith("~/"):
        return tok
    home = os.path.expanduser("~")
    rest = tok[1:].lstrip("/")
    expanded = os.path.join(home, rest) if rest else home
    return expanded.replace("/", "\\") if is_windows else expanded.replace("\\", "/")


def _venv_python_path(workdir: str, is_windows: bool) -> str:
    wd = _expand_tilde(workdir, is_windows).rstrip("\\/")
    if is_windows:
        return f"{wd}\\.venv\\Scripts\\python.exe"
    return f"{wd}/.venv/bin/python"


def resolve_command(
    cmd: str,
    workdir: str,
    is_windows: bool,
    which: Callable[[str], str | None],
) -> str:
    tokens = cmd.split()
    if not tokens:
        return cmd

    resolve_indices = {0}
    if "--" in tokens:
        dd = tokens.index("--")
        if dd + 1 < len(tokens):
            resolve_indices.add(dd + 1)

    for i in sorted(resolve_indices):
        tok = tokens[i]
        if tok in _LOGICAL_TOOLS:
            resolved = which(tok)
            if resolved is None:
                raise ValueError(f"could not resolve tool on PATH: {tok!r}")
            tokens[i] = resolved
        elif tok == "venv-python":
            tokens[i] = _venv_python_path(workdir, is_windows)

    tokens = [_expand_tilde(t, is_windows) for t in tokens]
    return " ".join(tokens)


def unit_basename(name: str) -> str:
    return name.lower().replace(" ", "-")


def systemd_units(routine: dict, resolved_cmds: list[str]) -> tuple[str, str]:
    description = routine.get("description", "")
    sched = parse_cron(routine["schedule"])
    oncalendar = to_oncalendar(sched)
    workdir = routine.get("workdir", "")

    service_lines = [
        "[Unit]",
        f"Description={description}",
        "",
        "[Service]",
        "Type=oneshot",
    ]
    if workdir:
        service_lines.append(f"WorkingDirectory={workdir}")
    for cmd in resolved_cmds:
        service_lines.append(f"ExecStart={cmd}")
    service = "\n".join(service_lines) + "\n"

    timer_lines = [
        "[Unit]",
        f"Description={description}",
        "",
        "[Timer]",
        f"OnCalendar={oncalendar}",
        "Persistent=true",
        "",
        "[Install]",
        "WantedBy=timers.target",
    ]
    timer = "\n".join(timer_lines) + "\n"
    return service, timer


def load_manifest(path: str | Path) -> list[dict]:
    with open(path, "rb") as f:
        data = tomllib.load(f)

    required = {"name", "description", "schedule", "commands", "workdir", "enabled"}
    seen: set[str] = set()
    result: list[dict] = []
    for r in data.get("routine", []):
        missing = required - r.keys()
        if missing:
            raise ValueError(f"routine missing keys {missing}: {r.get('name', '?')}")
        name = r["name"]
        if name in seen:
            raise ValueError(f"duplicate routine name: {name}")
        seen.add(name)
        parse_cron(r["schedule"])  # 不正なら ValueError
        result.append(r)
    return result


def parse_task_xml(xml_text: str) -> dict:
    root = ET.fromstring(xml_text)
    trigger = root.find(f".//{_TASK_NS}CalendarTrigger")
    if trigger is None:
        raise ValueError("no CalendarTrigger found in task XML")

    hour = minute = 0
    start = trigger.findtext(f"{_TASK_NS}StartBoundary", default="")
    if start and "T" in start:
        time_part = start.split("T", 1)[1]
        parts = time_part.split(":")
        if len(parts) >= 2:
            hour, minute = int(parts[0]), int(parts[1])

    result: dict = {"minute": minute, "hour": hour}

    days_of_week = trigger.find(f".//{_TASK_NS}DaysOfWeek")
    days_of_month = trigger.find(f".//{_TASK_NS}DaysOfMonth")

    if days_of_week is not None and len(days_of_week) > 0:
        day_tag = days_of_week[0].tag.replace(_TASK_NS, "")
        result["kind"] = "weekly"
        result["dow"] = _DOW_FULL.index(day_tag)
    elif days_of_month is not None:
        day_text = days_of_month.findtext(f"{_TASK_NS}Day")
        result["kind"] = "monthly"
        result["dom"] = int(day_text) if day_text else 0
    else:
        result["kind"] = "daily"

    commands: list[str] = []
    workdir = ""
    for exec_el in root.findall(f".//{_TASK_NS}Actions/{_TASK_NS}Exec"):
        command = exec_el.findtext(f"{_TASK_NS}Command", default="") or ""
        arguments = exec_el.findtext(f"{_TASK_NS}Arguments", default="") or ""
        commands.append(f"{command} {arguments}".strip())
        wd_text = exec_el.findtext(f"{_TASK_NS}WorkingDirectory", default="") or ""
        if wd_text and not workdir:
            workdir = wd_text

    result["commands"] = commands
    result["workdir"] = workdir
    return result


def _sched_tuple(sched: dict) -> tuple:
    return (
        sched.get("kind"),
        sched.get("hour"),
        sched.get("minute"),
        sched.get("dow"),
        sched.get("dom"),
    )


def _sched_str(sched: dict) -> str:
    kind = sched.get("kind")
    hh, mm = sched.get("hour"), sched.get("minute")
    extra = ""
    if kind == "weekly":
        extra = f" dow={sched.get('dow')}"
    elif kind == "monthly":
        extra = f" dom={sched.get('dom')}"
    return f"{kind} {hh}:{mm}{extra}"


def diff_routine(manifest_r: dict, live: dict | None) -> list[str]:
    if live is None:
        return ["missing"]

    diffs: list[str] = []

    m_sched = parse_cron(manifest_r["schedule"])
    if _sched_tuple(m_sched) != _sched_tuple(live):
        diffs.append(
            f"schedule: manifest={_sched_str(m_sched)} live={_sched_str(live)}"
        )

    live_cmds_joined = " ".join(live.get("commands", []))
    for cmd in manifest_r.get("commands", []):
        script_tok = None
        for tok in cmd.split():
            if tok.lower().endswith(".py") or tok.lower().endswith(".ps1"):
                script_tok = tok
        if script_tok is None:
            continue
        basename = script_tok.replace("\\", "/").rsplit("/", 1)[-1]
        if basename not in live_cmds_joined:
            diffs.append(f"command hint: {basename} not found in live actions")

    m_workdir = manifest_r.get("workdir", "")
    if m_workdir:
        m_wd = os.path.normpath(os.path.expanduser(m_workdir)).rstrip("\\/").lower()
        l_wd = (
            os.path.normpath(live.get("workdir") or "").rstrip("\\/").lower()
            if live.get("workdir")
            else ""
        )
        if m_wd != l_wd:
            diffs.append(f"workdir: manifest={m_wd} live={l_wd}")

    return diffs


# --- boundary I/O ---


def _default_toml_path() -> Path:
    return Path(__file__).resolve().parent.parent / "routines.toml"


def get_live_task(name: str) -> dict | None:
    escaped = name.replace("'", "''")
    try:
        result = subprocess.run(
            [
                "pwsh",
                "-NoProfile",
                "-Command",
                f"Export-ScheduledTask -TaskName '{escaped}'",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return parse_task_xml(result.stdout)
    except ET.ParseError:
        return None


def _list_live_task_names() -> list[str]:
    try:
        result = subprocess.run(
            [
                "pwsh",
                "-NoProfile",
                "-Command",
                "(Get-ScheduledTask -TaskName 'ADA*','ZundamonShindan' "
                "-ErrorAction SilentlyContinue).TaskName",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _sched_to_cron(live: dict) -> str:
    hh, mm = live["hour"], live["minute"]
    kind = live["kind"]
    if kind == "daily":
        return f"{mm} {hh} * * *"
    if kind == "weekly":
        return f"{mm} {hh} * * {live['dow']}"
    if kind == "monthly":
        return f"{mm} {hh} {live['dom']} * *"
    raise ValueError(f"unknown schedule kind: {kind!r}")


def _to_toml_block(name: str, live: dict) -> str:
    cron = _sched_to_cron(live)
    cmds_toml = ", ".join(json.dumps(c) for c in live.get("commands", []))
    lines = [
        "[[routine]]",
        f"name = {json.dumps(name)}",
        'description = ""',
        f"schedule = {json.dumps(cron)}",
        f"commands = [{cmds_toml}]",
        f"workdir = {json.dumps(live.get('workdir', ''))}",
        "enabled = true",
        "",
    ]
    return "\n".join(lines)


def cmd_check(args: argparse.Namespace) -> int:
    routines_list = load_manifest(args.toml)
    any_diff = False
    for r in routines_list:
        if not r.get("enabled", True):
            continue
        live = get_live_task(r["name"])
        diffs = diff_routine(r, live)
        if diffs:
            any_diff = True
            print(f"[DRIFT] {r['name']}")
            for d in diffs:
                print(f"  - {d}")
        else:
            print(f"[OK] {r['name']}")
    return 1 if any_diff else 0


def cmd_install(args: argparse.Namespace) -> int:
    routines_list = load_manifest(args.toml)
    is_windows = sys.platform.startswith("win")

    for r in routines_list:
        if not r.get("enabled", True):
            continue
        resolved = [
            resolve_command(c, r.get("workdir", ""), is_windows, shutil.which)
            for c in r["commands"]
        ]
        if is_windows:
            sched = parse_cron(r["schedule"])
            if len(resolved) == 1:
                cmdline = resolved[0]
            else:
                cmdline = 'cmd.exe /c "' + " && ".join(resolved) + '"'
            schtasks_args = to_schtasks_args(r["name"], sched, cmdline)
            if args.apply:
                subprocess.run(schtasks_args, check=True)
                print(f"[APPLIED] {r['name']}")
            else:
                print(f"[DRY-RUN] {r['name']}")
                print("  " + " ".join(schtasks_args))
        else:
            service, timer = systemd_units(r, resolved)
            base = unit_basename(r["name"])
            if args.apply:
                out_dir = (
                    Path(args.out) if args.out else Path.home() / ".config/systemd/user"
                )
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / f"{base}.service").write_text(service, encoding="utf-8")
                (out_dir / f"{base}.timer").write_text(timer, encoding="utf-8")
                print(f"[APPLIED] {r['name']} -> {out_dir}")
            else:
                print(f"[DRY-RUN] {r['name']}")
                print(f"--- {base}.service ---")
                print(service)
                print(f"--- {base}.timer ---")
                print(timer)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    for name in _list_live_task_names():
        live = get_live_task(name)
        if live is None:
            continue
        print(_to_toml_block(name, live))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="routines")
    parser.add_argument("--toml", default=str(_default_toml_path()))
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("check")

    install_p = sub.add_parser("install")
    install_p.add_argument("--apply", action="store_true")
    install_p.add_argument("--out", default=None)

    sub.add_parser("export")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command or "check"
    if command == "check":
        return cmd_check(args)
    if command == "install":
        return cmd_install(args)
    if command == "export":
        return cmd_export(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
