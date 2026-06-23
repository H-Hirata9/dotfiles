"""dotenvx_doctor.py
目的: プロジェクトの dotenvx 移行の健全性を読み取り専用でチェックして報告する
作成: ADA (Claude Code)
承認日: 2026-06-23
設計: dotenvx スキル（移行の抜け漏れ検知。秘密値は一切出力しない）

使い方:
    uv run --project ~/.claude/skills/dotenvx python ~/.claude/skills/dotenvx/scripts/dotenvx_doctor.py <project_path>
"""

from __future__ import annotations

import glob
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


# ---------- pure checks (秘密値は返さない・出力しない) ----------

def env_is_encrypted(env_text: str) -> bool:
    """DOTENV_PUBLIC_KEY があり、少なくとも1つの値が encrypted: になっている。"""
    has_pub = bool(re.search(r"^DOTENV_PUBLIC_KEY\s*=", env_text, re.M))
    has_enc = bool(re.search(r"=\s*\"?encrypted:", env_text))
    return has_pub and has_enc


def find_plaintext_keys(env_text: str) -> list[str]:
    """暗号化されていない平文値が残っているキー名の一覧（値は返さない）。"""
    out: list[str] = []
    for line in env_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _ASSIGN.match(line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip().strip('"').strip("'")
        if key in ("DOTENV_PUBLIC_KEY",):
            continue
        if val == "" or val.startswith("encrypted:"):
            continue
        out.append(key)
    return out


def keys_file_has_private(keys_text: str) -> bool:
    return bool(re.search(r"^DOTENV_PRIVATE_KEY", keys_text, re.M))


def py_files_with_load_dotenv(py_texts: dict[str, str]) -> list[str]:
    """load_dotenv が残っているファイル名の一覧。"""
    return [name for name, text in py_texts.items() if "load_dotenv" in text]


# ---------- boundary I/O ----------

def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return ""


def _git_ignored(project: str, name: str) -> bool:
    try:
        r = subprocess.run(
            ["git", "-C", project, "check-ignore", name],
            capture_output=True, text=True, timeout=15,
        )
        return r.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def diagnose(project: str) -> list[tuple[str, str, str]]:
    """(status, label, detail) のリストを返す。status は OK / NG / WARN。"""
    results: list[tuple[str, str, str]] = []
    env_path = os.path.join(project, ".env")
    keys_path = os.path.join(project, ".env.keys")

    env_text = _read(env_path)
    if not env_text:
        results.append(("NG", ".env", "見つからない/空"))
    elif env_is_encrypted(env_text):
        results.append(("OK", ".env 暗号化", "DOTENV_PUBLIC_KEY＋encrypted値あり"))
    else:
        results.append(("NG", ".env 暗号化", "未暗号化（dotenvx encrypt 未実行？）"))

    if env_text:
        plain = find_plaintext_keys(env_text)
        if plain:
            results.append(("NG", "平文値の残存", f"{len(plain)}件: {', '.join(plain)}"))
        else:
            results.append(("OK", "平文値なし", "全値が暗号化済み"))

    keys_text = _read(keys_path)
    if keys_text and keys_file_has_private(keys_text):
        results.append(("OK", ".env.keys", "DOTENV_PRIVATE_KEY あり"))
    else:
        results.append(("NG", ".env.keys", "無い/秘密鍵行なし"))

    if _git_ignored(project, ".env.keys"):
        results.append(("OK", ".env.keys gitignore", "無視されている"))
    else:
        results.append(("NG", ".env.keys gitignore", "★無視されてない（誤コミット危険）"))

    py_texts = {
        os.path.relpath(p, project): _read(p)
        for p in glob.glob(os.path.join(project, "**", "*.py"), recursive=True)
        if ".venv" not in p and "__pycache__" not in p
    }
    leftover = py_files_with_load_dotenv(py_texts)
    if leftover:
        results.append(("NG", "load_dotenv 残存", ", ".join(leftover)))
    else:
        results.append(("OK", "load_dotenv 撤去", "残っていない"))

    baks = glob.glob(os.path.join(project, "*.plain.bak"))
    if baks:
        results.append(("WARN", "平文backup残存", f"{len(baks)}件（検証後は削除推奨）"))

    return results


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: dotenvx_doctor.py <project_path>")
        return 2
    project = os.path.abspath(sys.argv[1])
    if not os.path.isdir(project):
        print(f"not a directory: {project}")
        return 2
    print(f"=== dotenvx doctor: {project} ===")
    results = diagnose(project)
    mark = {"OK": "[OK]", "NG": "[NG]", "WARN": "[!]"}
    for status, label, detail in results:
        print(f"{mark.get(status, '?'):5} {label:22} {detail}")
    ng = sum(1 for s, _, _ in results if s == "NG")
    print(f"--- {'PASS' if ng == 0 else f'{ng} 件の問題あり'} ---")
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
