import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import eval_collect as ec


# ---------- parse_guard_log ----------

def test_parse_guard_log_single_line():
    text = "2026-06-22 16:57:11  AUDIT   recursive rm  ::  rm -rf /tmp/x"
    ev = ec.parse_guard_log(text)
    assert len(ev) == 1
    assert ev[0]["level"] == "AUDIT"
    assert ev[0]["pattern"] == "recursive rm"
    assert ev[0]["command"] == "rm -rf /tmp/x"


def test_parse_guard_log_multiline_command_appends():
    text = (
        "2026-06-22 16:57:11  AUDIT   recursive rm  ::  set -e\n"
        'rm -rf "$SK/x"\n'
        "echo done"
    )
    ev = ec.parse_guard_log(text)
    assert len(ev) == 1
    assert "set -e" in ev[0]["command"]
    assert 'rm -rf "$SK/x"' in ev[0]["command"]
    assert "echo done" in ev[0]["command"]


def test_parse_guard_log_block_level():
    text = "2026-06-20 10:00:00  BLOCK   fork bomb  ::  :(){ :|:& };:"
    ev = ec.parse_guard_log(text)
    assert ev[0]["level"] == "BLOCK"


# ---------- count_worklog_entries ----------

def test_count_worklog_entries_ignores_h1():
    md = "# ADA作業ログ\n\n## 09:00 — A\n本文\n## 10:00 — B\n本文\n"
    assert ec.count_worklog_entries(md) == 2


def test_count_worklog_entries_empty():
    assert ec.count_worklog_entries("") == 0


# ---------- iter_session_events ----------

def _line(role, content, ts="2026-06-22T10:00:00Z"):
    return json.dumps({"type": role, "timestamp": ts, "message": {"content": content}})


def test_iter_session_events_text_and_tooluse():
    jl = "\n".join([
        _line("assistant", [{"type": "text", "text": "やるね"},
                            {"type": "tool_use", "name": "Bash", "input": {}}]),
        _line("user", [{"type": "tool_result", "is_error": True, "content": "boom"}]),
    ])
    evs = ec.iter_session_events(jl)
    assert evs[0]["role"] == "assistant"
    assert evs[0]["tool_uses"] == ["Bash"]
    assert "やるね" in evs[0]["text"]
    assert evs[1]["tool_errors"] == 1


def test_iter_session_events_skips_non_message_types():
    jl = "\n".join([
        json.dumps({"type": "system", "subtype": "x"}),
        _line("user", "ただのテキスト"),
        "not json",
    ])
    evs = ec.iter_session_events(jl)
    assert len(evs) == 1
    assert evs[0]["text"] == "ただのテキスト"


# ---------- detect_signals ----------

def test_detect_signals_human_interrupt_is_rework():
    evs = [{"ts": "t", "role": "user", "text": "違う、それじゃない", "tool_uses": [], "tool_errors": 0}]
    sig = ec.detect_signals(evs)
    assert sig[0]["category"] == "rework"
    assert sig[0]["source"] == "human_interrupt"


def test_detect_signals_assistant_retract_is_self_correction():
    evs = [{"ts": "t", "role": "assistant", "text": "ごめん、さっきのは誤報。撤回するね", "tool_uses": [], "tool_errors": 0}]
    sig = ec.detect_signals(evs)
    assert any(s["category"] == "self_correction" for s in sig)


def test_detect_signals_consecutive_tool_errors_is_tool_spin():
    evs = [
        {"ts": "t1", "role": "assistant", "text": "", "tool_uses": ["Grep"], "tool_errors": 1},
        {"ts": "t2", "role": "assistant", "text": "", "tool_uses": ["Grep"], "tool_errors": 1},
        {"ts": "t3", "role": "assistant", "text": "", "tool_uses": ["Grep"], "tool_errors": 1},
    ]
    sig = ec.detect_signals(evs)
    assert any(s["category"] == "tool_spin" for s in sig)


def test_detect_signals_long_text_interrupt_word_is_ignored():
    long_noise = "Base directory for this skill: " + "x" * 300 + " ストップ"
    evs = [{"ts": "t", "role": "user", "text": long_noise, "tool_uses": [], "tool_errors": 0}]
    assert ec.detect_signals(evs) == []


def test_detect_signals_injected_assistant_text_ignored():
    evs = [{"ts": "t", "role": "assistant",
            "text": "<system-reminder> ... 訂正 ...", "tool_uses": [], "tool_errors": 0}]
    assert ec.detect_signals(evs) == []


def test_detect_signals_clean_session_no_signals():
    evs = [
        {"ts": "t", "role": "user", "text": "これお願い", "tool_uses": [], "tool_errors": 0},
        {"ts": "t", "role": "assistant", "text": "できたよ", "tool_uses": ["Bash"], "tool_errors": 0},
    ]
    assert ec.detect_signals(evs) == []


# ---------- baseline / metrics / patterns ----------

def test_compute_baseline_completion_rate_is_null():
    b = ec.compute_baseline(total_tasks=10, total_tool_uses=30, session_count=3)
    assert b["total_tasks"] == 10
    assert b["avg_tool_steps"] == 10.0
    assert b["completion_rate"] is None


def test_compute_baseline_zero_sessions_no_div_error():
    b = ec.compute_baseline(0, 0, 0)
    assert b["avg_tool_steps"] == 0.0


def test_tally_metrics_adds_guard_and_reopened():
    signals = [
        {"category": "rework", "source": "human_interrupt"},
        {"category": "self_correction", "source": "assistant_retract"},
    ]
    m = ec.tally_metrics(signals, guard_blocks=2, reopened=1)
    assert m["policy_violation"] == 2
    assert m["rework"] == 1 + 1
    assert m["self_correction"] == 1
    assert m["factual_error"] == 0


def test_find_repeated_patterns_groups_by_category_source():
    signals = [
        {"category": "tool_spin", "source": "consecutive_tool_error"},
        {"category": "tool_spin", "source": "consecutive_tool_error"},
        {"category": "rework", "source": "human_interrupt"},
    ]
    pats = ec.find_repeated_patterns(signals, min_count=2)
    assert len(pats) == 1
    assert pats[0]["signal"] == "tool_spin/consecutive_tool_error"
    assert pats[0]["count"] == 2


# ---------- report schema / markdown ----------

def test_build_report_has_fixed_schema():
    rep = ec.build_report("2026-06", ec.compute_baseline(1, 1, 1),
                          ec.tally_metrics([], 0, 0), [], [])
    for key in ("period", "generated_at", "baseline", "metrics", "repeated_patterns", "events"):
        assert key in rep
    for mk in ec.METRIC_KEYS:
        assert mk in rep["metrics"]


def test_render_markdown_has_frontmatter_and_period():
    rep = ec.build_report("2026-06", ec.compute_baseline(1, 1, 1),
                          ec.tally_metrics([], 0, 0), [], [])
    md = ec.render_markdown(rep)
    assert md.startswith("---")
    assert "period: 2026-06" in md
    assert "category: quality-evaluation" in md
