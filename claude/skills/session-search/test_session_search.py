"""
session-search のユニットテスト（標準ライブラリ unittest）。
実行: python test_session_search.py
- 一時ディレクトリに合成 .jsonl を置き、DB_PATH/PROJECTS_ROOT を差し替えて検証する。
"""

import json
import os
import tempfile
import unittest

import session_search as ss


def write_jsonl(path, entries):
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


class SessionSearchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.projects = os.path.join(root, "projects")
        os.makedirs(os.path.join(self.projects, "proj-a"))
        self.jsonl = os.path.join(self.projects, "proj-a", "conv-1.jsonl")
        # 索引対象（user/assistant）＋非対象（system 等）を混ぜる
        write_jsonl(self.jsonl, [
            {"type": "user", "uuid": "u1", "parentUuid": None, "timestamp": "2026-06-01T00:00:00Z",
             "message": {"role": "user", "content": "診断士の財務会計が弱点だと話した"}},
            {"type": "system", "content": "noise", "timestamp": "2026-06-01T00:00:01Z"},
            {"type": "assistant", "uuid": "a1", "parentUuid": "u1", "timestamp": "2026-06-01T00:00:02Z",
             "message": {"role": "assistant", "content": [{"type": "text", "text": "ふるさと納税の枠を確認するね"}]}},
        ])
        # モジュールのパスを差し替え
        ss.PROJECTS_ROOT = self.projects
        ss.DB_PATH = os.path.join(root, "sessions.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_index_and_japanese_trigram_search(self):
        con = ss.connect()
        stats = ss.index(con)
        # system はスキップ、user/assistant の2件のみ
        self.assertEqual(stats["new_messages"], 2)
        n = con.execute("SELECT count(*) FROM messages").fetchone()[0]
        self.assertEqual(n, 2)
        # 日本語 trigram ヒット
        rows = con.execute(
            "SELECT m.content FROM messages_fts JOIN messages m ON m.id=messages_fts.rowid"
            " WHERE messages_fts MATCH ?", ('"診断士"',)
        ).fetchall()
        self.assertTrue(any("診断士" in r[0] for r in rows))
        con.close()

    def test_incremental_appends_only_new(self):
        con = ss.connect()
        ss.index(con)
        before = con.execute("SELECT count(*) FROM messages").fetchone()[0]
        # 追記（append-only）
        with open(self.jsonl, "a", encoding="utf-8") as f:
            f.write(json.dumps({"type": "user", "uuid": "u2", "parentUuid": "a1",
                                "timestamp": "2026-06-02T00:00:00Z",
                                "message": {"role": "user", "content": "Hermesの設計を見た"}},
                               ensure_ascii=False) + "\n")
        stats = ss.index(con)
        self.assertEqual(stats["new_messages"], 1)  # 追記の1件だけ
        after = con.execute("SELECT count(*) FROM messages").fetchone()[0]
        self.assertEqual(after, before + 1)
        con.close()

    def test_short_query_like_fallback(self):
        # 2文字未満は trigram が効かないので LIKE フォールバックで拾えること
        con = ss.connect()
        with open(self.jsonl, "a", encoding="utf-8") as f:
            f.write(json.dumps({"type": "user", "uuid": "u3", "parentUuid": None,
                                "timestamp": "2026-06-03T00:00:00Z",
                                "message": {"role": "user", "content": "AIの話"}},
                               ensure_ascii=False) + "\n")
        ss.index(con)
        rows = con.execute(
            "SELECT session_id, project, seq FROM messages WHERE content LIKE ?", ("%AI%",)
        ).fetchall()
        self.assertTrue(rows)  # LIKE で2文字"AI"がヒット
        con.close()

    def test_query_escaping_no_crash(self):
        con = ss.connect()
        ss.index(con)
        # 記号入りクエリでも OperationalError を起こさない
        expr = ss._match_expr('agy --model "test"')
        con.execute(
            "SELECT count(*) FROM messages_fts WHERE messages_fts MATCH ?", (expr,)
        ).fetchone()
        con.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
