"""evaluator / eval_collect.py
目的: ADAの品質シグナルを月次で集計し、ダッシュボード用データ層(JSON)＋人間向けレポート(MD)を出力
作成: ADA (Claude Code)
承認日: 2026-06-23
設計: ada-board #21 / 計画 ~/.claude/plans/2026-06-23_ada-board-21_quality-eval-loop.md
       Gemini Pro レビュー反映（定量ベースライン・ツール空振り・システムイベント主軸・Reflexion）

シグナル源:
- worklog (Vault/ada_worklog/YYYY-MM-DD.md) … 総タスク数のベースライン
- ada-guard.log … BLOCK = policy_violation 候補
- session jsonl (~/.claude/projects/<slug>/*.jsonl) … tool_use 数・tool error・人間の割り込み・自己訂正
- gh reopened issues … rework 候補（main()でのみ呼ぶ。純粋関数はテスト可能に分離）

metrics は「自動検知できた生カウント」。誤報(factual_error)等の最終ラベルは主人の月次レビューで確定する。
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

WORKLOG_DIR = os.path.join(os.path.expanduser("~"), "Vault", "ada_worklog")
GUARD_LOG = os.path.join(os.path.expanduser("~"), ".claude", "hooks", "ada-guard.log")
PROJECTS_ROOT = os.path.join(os.path.expanduser("~"), ".claude", "projects")
OUT_DIR = os.path.join(
    os.path.expanduser("~"), "projects", "life", "cch-bot-knowledge", "eval"
)

INTERRUPT_WORDS = ("違う", "ちがう", "ストップ", "やり直", "間違ってる", "間違っている", "そうじゃない")
RETRACT_WORDS = ("撤回", "誤報", "訂正", "間違いだった", "間違えた")
TOOL_SPIN_THRESHOLD = 3
INTERRUPT_MAX_LEN = 200  # 本物の割り込みは短い。長文への語の巻き込み（偽陽性）を弾く
INJECTION_MARKERS = ("Base directory for this skill", "<system-reminder>", "Contents of",
                     "system-reminder", "<command-name>", "local-command")

METRIC_KEYS = ("factual_error", "rework", "policy_violation", "self_correction", "tool_spin")


# ---------- pure parsers ----------

_GUARD_LINE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(AUDIT|BLOCK)\s+(.+?)\s+::\s+(.*)$"
)


def parse_guard_log(text: str) -> list[dict]:
    """ada-guard.log を構造化。継続行（タイムスタンプ無し）は直前の command に連結。"""
    events: list[dict] = []
    for line in text.splitlines():
        m = _GUARD_LINE.match(line)
        if m:
            events.append(
                {"ts": m.group(1), "level": m.group(2), "pattern": m.group(3).strip(), "command": m.group(4)}
            )
        elif events:
            events[-1]["command"] += "\n" + line
    return events


def count_worklog_entries(md_text: str) -> int:
    """worklog の `## ` 見出し（H1タイトルは除外）を1タスクとして数える。"""
    return sum(1 for ln in md_text.splitlines() if ln.startswith("## "))


def iter_session_events(jsonl_text: str) -> list[dict]:
    """session jsonl を {ts, role, text, tool_uses:[names], tool_errors:int} に正規化。"""
    out: list[dict] = []
    for line in jsonl_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        role = o.get("type")
        if role not in ("user", "assistant"):
            continue
        msg = o.get("message")
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        texts: list[str] = []
        tool_uses: list[str] = []
        tool_errors = 0
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for it in content:
                if not isinstance(it, dict):
                    continue
                t = it.get("type")
                if t == "text":
                    texts.append(it.get("text", ""))
                elif t == "tool_use":
                    tool_uses.append(it.get("name", ""))
                elif t == "tool_result" and it.get("is_error"):
                    tool_errors += 1
        out.append(
            {
                "ts": o.get("timestamp", ""),
                "role": role,
                "text": "\n".join(texts),
                "tool_uses": tool_uses,
                "tool_errors": tool_errors,
            }
        )
    return out


def _contains(text: str, words: tuple[str, ...]) -> bool:
    return any(w.lower() in text.lower() for w in words)


def _is_injected(text: str) -> bool:
    return any(m in text for m in INJECTION_MARKERS)


def detect_signals(events: list[dict], session_id: str = "") -> list[dict]:
    """正規化済みイベント列から品質シグナルを抽出（システムイベント＋人間の割り込みを主軸）。"""
    signals: list[dict] = []
    err_run: list[str] = []  # 直近の連続 tool error の発生元ツール名
    for ev in events:
        text = ev.get("text", "")
        ts = ev.get("ts", "")
        if ev["role"] == "user":
            if (len(text) <= INTERRUPT_MAX_LEN and not _is_injected(text)
                    and _contains(text, INTERRUPT_WORDS)):
                signals.append({"ts": ts, "category": "rework", "source": "human_interrupt",
                                "session": session_id, "summary": _snippet(text)})
        elif ev["role"] == "assistant":
            if not _is_injected(text) and _contains(text, RETRACT_WORDS):
                signals.append({"ts": ts, "category": "self_correction", "source": "assistant_retract",
                                "session": session_id, "summary": _snippet(text)})
        # tool error の連続を tool_spin として検知
        if ev.get("tool_errors", 0) > 0:
            err_run.extend(ev["tool_uses"] or ["?"])
            if len(err_run) >= TOOL_SPIN_THRESHOLD:
                signals.append({"ts": ts, "category": "tool_spin", "source": "consecutive_tool_error",
                                "session": session_id, "summary": f"連続ツール失敗 x{len(err_run)}"})
                err_run = []
        else:
            err_run = []
    return signals


def _snippet(text: str, n: int = 80) -> str:
    s = " ".join(text.split())
    return s[:n] + ("…" if len(s) > n else "")


def compute_baseline(total_tasks: int, total_tool_uses: int, session_count: int) -> dict:
    avg = round(total_tool_uses / session_count, 2) if session_count else 0.0
    return {
        "total_tasks": total_tasks,
        "avg_tool_steps": avg,
        "completion_rate": None,  # 客観シグナル未確立。捏造せず null（主人レビューで補う）
    }


def tally_metrics(signals: list[dict], guard_blocks: int, reopened: int) -> dict:
    metrics = {k: 0 for k in METRIC_KEYS}
    for s in signals:
        if s["category"] in metrics:
            metrics[s["category"]] += 1
    metrics["policy_violation"] += guard_blocks
    metrics["rework"] += reopened
    return metrics


def find_repeated_patterns(signals: list[dict], min_count: int = 2) -> list[dict]:
    """同種シグナルの繰り返しを (category, source) で束ねる。proposed_rule は主人レビューで埋める。"""
    counts: dict[tuple[str, str], int] = {}
    for s in signals:
        key = (s["category"], s.get("source", ""))
        counts[key] = counts.get(key, 0) + 1
    out = [
        {"signal": f"{cat}/{src}", "count": c, "proposed_rule": ""}
        for (cat, src), c in counts.items()
        if c >= min_count
    ]
    return sorted(out, key=lambda x: x["count"], reverse=True)


def build_report(period: str, baseline: dict, metrics: dict,
                 patterns: list[dict], events: list[dict]) -> dict:
    return {
        "period": period,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "baseline": baseline,
        "metrics": metrics,
        "repeated_patterns": patterns,
        "events": events,
    }


def render_markdown(report: dict) -> str:
    m = report["metrics"]
    b = report["baseline"]
    lines = [
        "---",
        f"date: {report['generated_at'][:10]}",
        "source: evaluator/eval_collect.py",
        "organization: ADA",
        "category: quality-evaluation",
        f"period: {report['period']}",
        "---",
        "",
        f"# ADA品質評価レポート {report['period']}",
        "",
        "## ベースライン（定量）",
        "| 指標 | 値 |",
        "|---|---|",
        f"| 総タスク数 | {b['total_tasks']} |",
        f"| 平均ツールステップ/セッション | {b['avg_tool_steps']} |",
        f"| タスク完了率 | {b['completion_rate'] if b['completion_rate'] is not None else 'N/A（要手動）'} |",
        "",
        "## メトリクス（自動検知の生カウント）",
        "| 分類 | 件数 |",
        "|---|---|",
        f"| 誤報 factual_error | {m['factual_error']}（※主人レビューで確定） |",
        f"| 手戻り rework | {m['rework']} |",
        f"| 承認逸脱 policy_violation | {m['policy_violation']} |",
        f"| 自己訂正 self_correction | {m['self_correction']} |",
        f"| ツール空振り tool_spin | {m['tool_spin']} |",
        "",
        "## 繰り返しパターン（→ Reflexionで汎用ルール化して #23 へ）",
    ]
    if report["repeated_patterns"]:
        lines += ["| シグナル | 回数 | 提案ルール(主人/ADAが記入) |", "|---|---|---|"]
        for p in report["repeated_patterns"]:
            lines.append(f"| {p['signal']} | {p['count']} | {p['proposed_rule'] or '（未記入）'} |")
    else:
        lines.append("（繰り返しパターンなし）")
    lines += ["", "## イベント明細", ""]
    for e in report["events"]:
        lines.append(f"- [{e.get('ts','')[:16]}] {e.get('category','')} / {e.get('source','')}: {e.get('summary','')}")
    lines.append("")
    return "\n".join(lines)


# ---------- boundary I/O (main only) ----------

def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return ""


def _collect_worklog_tasks(period: str) -> int:
    total = 0
    for path in glob.glob(os.path.join(WORKLOG_DIR, f"{period}-*.md")):
        total += count_worklog_entries(_read(path))
    return total


def _collect_sessions(period: str) -> tuple[list[dict], int, int]:
    """期間内の session シグナル・総tool_use数・セッション数を集める。"""
    all_signals: list[dict] = []
    total_tool_uses = 0
    session_count = 0
    for path in glob.glob(os.path.join(PROJECTS_ROOT, "*", "*.jsonl")):
        events = iter_session_events(_read(path))
        events = [e for e in events if (e.get("ts") or "").startswith(period)]
        if not events:
            continue
        session_count += 1
        total_tool_uses += sum(len(e.get("tool_uses") or []) for e in events)
        all_signals.extend(detect_signals(events, session_id=os.path.basename(path)[:8]))
    return all_signals, total_tool_uses, session_count


def _count_guard_blocks(period: str) -> int:
    events = parse_guard_log(_read(GUARD_LOG))
    return sum(1 for e in events if e["level"] == "BLOCK" and e["ts"].startswith(period))


def _count_reopened_issues(period: str) -> int:
    try:
        out = subprocess.run(
            ["gh", "issue", "list", "--repo", "H-Hirata9/ada-board",
             "--state", "all", "--json", "number,stateReason,updatedAt", "--limit", "100"],
            capture_output=True, text=True, timeout=30,
        )
        if out.returncode != 0:
            return 0
        data = json.loads(out.stdout or "[]")
        return sum(1 for d in data
                   if d.get("stateReason") == "REOPENED" and (d.get("updatedAt") or "").startswith(period))
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return 0


def run(period: str, write: bool, no_gh: bool) -> dict:
    total_tasks = _collect_worklog_tasks(period)
    signals, total_tool_uses, session_count = _collect_sessions(period)
    guard_blocks = _count_guard_blocks(period)
    reopened = 0 if no_gh else _count_reopened_issues(period)

    baseline = compute_baseline(total_tasks, total_tool_uses, session_count)
    metrics = tally_metrics(signals, guard_blocks, reopened)
    patterns = find_repeated_patterns(signals)
    report = build_report(period, baseline, metrics, patterns, signals)

    if write:
        os.makedirs(OUT_DIR, exist_ok=True)
        with open(os.path.join(OUT_DIR, f"eval-{period}.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        with open(os.path.join(OUT_DIR, f"eval-{period}.md"), "w", encoding="utf-8") as f:
            f.write(render_markdown(report))
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="ADA quality evaluation collector")
    ap.add_argument("--month", default=datetime.now().strftime("%Y-%m"), help="対象月 YYYY-MM")
    ap.add_argument("--write", action="store_true", help="cch-bot-knowledge/eval/ に出力")
    ap.add_argument("--no-gh", action="store_true", help="gh 呼び出しをスキップ")
    args = ap.parse_args()
    report = run(args.month, write=args.write, no_gh=args.no_gh)
    print(render_markdown(report))


if __name__ == "__main__":
    main()
