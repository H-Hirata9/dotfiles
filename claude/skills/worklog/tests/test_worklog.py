import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import worklog

JST = timezone(timedelta(hours=9))
DT = datetime(2026, 6, 21, 13, 25, tzinfo=JST)


def test_format_entry_full():
    e = worklog.format_entry("タイトル", "依頼内容", "やったこと内容", "abc123 / #18", DT)
    assert "## 2026-06-21 13:25 — タイトル" in e
    assert "依頼: 依頼内容" in e
    assert "やったこと: やったこと内容" in e
    assert "成果物: abc123 / #18" in e


def test_format_entry_omits_empty_artifacts():
    e = worklog.format_entry("t", "r", "d", "", DT)
    assert "成果物:" not in e


def test_append_entry_creates_header_then_appends(tmp_path):
    p1 = worklog.append_entry(tmp_path, DT, "## 1つ目\n\n")
    assert p1.name == "2026-06-21.md"
    text = p1.read_text(encoding="utf-8")
    assert text.startswith("# ADA作業ログ 2026-06-21")
    assert "## 1つ目" in text

    p2 = worklog.append_entry(tmp_path, DT, "## 2つ目\n\n")
    assert p2 == p1
    text2 = p2.read_text(encoding="utf-8")
    assert text2.count("# ADA作業ログ 2026-06-21") == 1
    assert "## 1つ目" in text2
    assert "## 2つ目" in text2


class FakeRun:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, args, cwd=None):
        self.calls.append(args)
        return self.responses.pop(0)


def test_md_to_html_basic():
    md = "# ADA作業ログ 2026-06\n\n## 2026-06-21 13:25 — タイトル\n依頼: 何か\n成果物: a < b & c\n"
    html = worklog.md_to_html(md)
    assert "<h1>ADA作業ログ 2026-06</h1>" in html
    assert "<h2>2026-06-21 13:25 — タイトル</h2>" in html
    assert "<b>依頼:</b> 何か" in html
    assert "a &lt; b &amp; c" in html  # HTMLエスケープされる


def test_sync_creates_folder_and_doc_when_missing(tmp_path):
    path = tmp_path / "2026-06.md"
    path.write_text("# ADA作業ログ 2026-06\n\n## x\n依頼: y\n", encoding="utf-8")
    run = FakeRun([
        '{"files": []}',                       # folder search: none
        '{"id": "FOLDER1"}',                   # folder create
        '{"files": []}',                       # doc search: none
        '{"id": "DOC1"}',                      # doc create (convert)
    ])

    doc_id = worklog.sync_to_drive(path, "ada_worklog", run=run)

    assert doc_id == "DOC1"
    joined = [" ".join(c) for c in run.calls]
    assert any("files create" in j and "ada_worklog" in j and "folder" in j for j in joined)
    # 作成時は Google ドキュメントへ変換指定 ＋ HTMLアップロード
    assert any("files create" in j and "document" in j and "text/html" in j for j in joined)
    # 一時HTMLは後始末される
    assert not (tmp_path / "2026-06.html").exists()


def test_sync_updates_existing_doc(tmp_path):
    path = tmp_path / "2026-06.md"
    path.write_text("# ADA作業ログ 2026-06\n\n## x\n依頼: y\n", encoding="utf-8")
    run = FakeRun([
        '{"files": [{"id": "FOLDER1", "name": "ada_worklog"}]}',   # folder found
        '{"files": [{"id": "DOC9", "name": "2026-06"}]}',          # doc found
        '{"id": "DOC9"}',                                           # update
    ])

    doc_id = worklog.sync_to_drive(path, "ada_worklog", run=run)

    assert doc_id == "DOC9"
    joined = [" ".join(c) for c in run.calls]
    assert any("files update" in j and "DOC9" in j and "text/html" in j for j in joined)
    assert not any("folder" in j and "files create" in j for j in joined)
    assert not (tmp_path / "2026-06.html").exists()


def test_extract_json_tolerates_prefix():
    assert worklog._extract_json('Using keyring backend: keyring\n{"a": 1}') == {"a": 1}
