"""
session-search / session_search.py
目的: Claude Code の全セッション(.jsonl)を SQLite+FTS5(trigram) で全文検索し、ADA に長期記憶を与える
作成: ADA (Claude Code)
承認日: 2026-06-19
設計: ada-board #13（Hermes state.db / session_search 相当）

仕組み:
- データ源 ~/.claude/projects/<slug>/<conv-id>.jsonl（1行1イベント）。user/assistant の
  message.content を平文化して索引する。会話ID=ファイル名。
- 索引 DB: ~/.claude/ada/sessions.db。FTS5 は trigram トークナイザ（日本語/CJK 対応に必須）。
- 増分: ingested_files に last_byte_offset を持ち、追記分だけ seek して取り込む（.jsonl は append-only）。
  ファイルが縮んだら該当セッションを作り直す。検索時に自動で増分同期してから検索（on-demand）。
- 検索(DISCOVERY): query→FTS5 MATCH→bm25順→各ヒットに ±5 メッセージ窓＋セッション先頭/末尾3件(bookends)。

使い方:
    python session_search.py index                       # 増分インデックス
    python session_search.py search "診断士 弱点" [--limit 8] [--since 2026-06-01]
    python session_search.py status
"""

import glob
import json
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import sqlite3

PROJECTS_ROOT = os.path.join(os.path.expanduser("~"), ".claude", "projects")
DB_PATH = os.path.join(os.path.expanduser("~"), ".claude", "ada", "sessions.db")
WINDOW = 5          # ヒット前後のメッセージ数
BOOKEND = 3         # セッション先頭/末尾の表示数
INDEXED_TYPES = ("user", "assistant")


def connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.execute("PRAGMA journal_mode=WAL")
    return con


def init_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS messages(
          id INTEGER PRIMARY KEY,
          session_id TEXT NOT NULL,
          project TEXT,
          msg_uuid TEXT,
          parent_uuid TEXT,
          ts TEXT,
          role TEXT,
          content TEXT NOT NULL,
          seq INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_msg_session ON messages(session_id, seq);
        CREATE TABLE IF NOT EXISTS sessions(
          session_id TEXT PRIMARY KEY,
          project TEXT,
          started_at TEXT,
          ended_at TEXT,
          msg_count INTEGER
        );
        CREATE TABLE IF NOT EXISTS ingested_files(
          path TEXT PRIMARY KEY,
          mtime REAL,
          last_size INTEGER,
          last_byte_offset INTEGER,
          next_seq INTEGER
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
          content, content='messages', content_rowid='id', tokenize='trigram'
        );
        CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
          INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
        END;
        CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
          INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
        END;
        """
    )


def extract_text(message: dict) -> str:
    """user/assistant の message.content を平文化する。"""
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for b in content:
        if not isinstance(b, dict):
            continue
        bt = b.get("type")
        if bt == "text" and b.get("text"):
            parts.append(b["text"])
        elif bt == "thinking" and b.get("thinking"):
            parts.append(b["thinking"])
        elif bt == "tool_use":
            name = b.get("name", "")
            inp = b.get("input")
            parts.append(f"[tool:{name}] " + (json.dumps(inp, ensure_ascii=False)[:500] if inp else ""))
        elif bt == "tool_result":
            c = b.get("content")
            if isinstance(c, str):
                parts.append(c)
            elif isinstance(c, list):
                for cc in c:
                    if isinstance(cc, dict) and cc.get("type") == "text" and cc.get("text"):
                        parts.append(cc["text"])
    return "\n".join(p for p in parts if p)


def index(con: sqlite3.Connection, verbose: bool = False) -> dict:
    init_schema(con)
    files = glob.glob(os.path.join(PROJECTS_ROOT, "*", "*.jsonl"))
    stats = {"files": 0, "new_messages": 0, "changed_sessions": 0}
    for path in files:
        try:
            st = os.stat(path)
        except OSError:
            continue
        size, mtime = st.st_size, st.st_mtime
        session_id = os.path.splitext(os.path.basename(path))[0]
        project = os.path.basename(os.path.dirname(path))
        row = con.execute(
            "SELECT last_size, last_byte_offset, next_seq FROM ingested_files WHERE path=?",
            (path,),
        ).fetchone()

        if row is None:
            start_off, seq = 0, 0
        else:
            last_size, last_off, seq = row
            if size < last_size:  # 縮んだ/ローテート → 作り直し
                con.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
                start_off, seq = 0, 0
            elif size == last_size:
                continue  # 変化なし
            else:
                start_off = last_off

        with open(path, "rb") as fh:
            fh.seek(start_off)
            data = fh.read()
        nl = data.rfind(b"\n")
        if nl == -1:
            continue  # まだ完全な行が無い
        chunk = data[: nl + 1]
        new_off = start_off + nl + 1
        added = 0
        for line in chunk.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("type") not in INDEXED_TYPES:
                continue
            text = extract_text(d.get("message"))
            if not text.strip():
                continue
            con.execute(
                "INSERT INTO messages(session_id,project,msg_uuid,parent_uuid,ts,role,content,seq)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (session_id, project, d.get("uuid"), d.get("parentUuid"),
                 d.get("timestamp"), d.get("type"), text, seq),
            )
            seq += 1
            added += 1

        con.execute(
            "INSERT INTO ingested_files(path,mtime,last_size,last_byte_offset,next_seq)"
            " VALUES(?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET"
            " mtime=excluded.mtime,last_size=excluded.last_size,"
            " last_byte_offset=excluded.last_byte_offset,next_seq=excluded.next_seq",
            (path, mtime, size, new_off, seq),
        )
        if added:
            con.execute(
                "INSERT OR REPLACE INTO sessions(session_id,project,started_at,ended_at,msg_count)"
                " SELECT session_id, ?, min(ts), max(ts), count(*) FROM messages"
                " WHERE session_id=? GROUP BY session_id",
                (project, session_id),
            )
            stats["new_messages"] += added
            stats["changed_sessions"] += 1
        stats["files"] += 1
    con.commit()
    return stats


def _match_expr(query: str) -> str:
    terms = query.split()
    if not terms:
        terms = [query]
    return " AND ".join('"' + t.replace('"', '""') + '"' for t in terms)


def _trunc(s: str, n: int = 200) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n] + "…"


def _render_hits(con: sqlite3.Connection, hit_rows: list, query: str, limit: int) -> None:
    shown = []
    for sid, project, seq in hit_rows:
        if sid in shown:
            continue
        shown.append(sid)
        sess = con.execute(
            "SELECT started_at, ended_at, msg_count FROM sessions WHERE session_id=?", (sid,)
        ).fetchone()
        print("=" * 70)
        print(f"session {sid}  [{project}]")
        if sess:
            print(f"  {sess[0]} 〜 {sess[1]}  ({sess[2]} msgs)")
        head = con.execute(
            "SELECT seq, role, ts, content FROM messages WHERE session_id=? ORDER BY seq LIMIT ?",
            (sid, BOOKEND),
        ).fetchall()
        print("  --- session start ---")
        for s, role, t, c in head:
            print(f"   #{s} {role}: {_trunc(c, 120)}")
        print(f"  --- match window (seq {seq}) ---")
        win = con.execute(
            "SELECT seq, role, ts, content FROM messages WHERE session_id=? AND seq BETWEEN ? AND ? ORDER BY seq",
            (sid, seq - WINDOW, seq + WINDOW),
        ).fetchall()
        for s, role, t, c in win:
            mark = " <<<" if s == seq else ""
            print(f"   #{s} {role}: {_trunc(c)}{mark}")
        if len(shown) >= limit:
            break
    print("=" * 70)
    print(f"{len(shown)} session(s) shown for: {query}")


def search(con: sqlite3.Connection, query: str, limit: int, since: str | None) -> None:
    index(con)  # on-demand 増分同期
    terms = query.split() or [query]
    # trigram は3文字以上が前提。1〜2文字の語が混じるクエリは LIKE にフォールバック
    # （小規模DBなので全走査でも一瞬。bm25 が使えないので新しい順で返す）。
    if any(len(t) < 3 for t in terms):
        where = " AND ".join("content LIKE ?" for _ in terms)
        params: list = [f"%{t}%" for t in terms]
        sql = f"SELECT session_id, project, seq FROM messages WHERE {where}"
        if since:
            sql += " AND ts >= ?"
            params.append(since)
        sql += " ORDER BY ts DESC LIMIT ?"
        params.append(limit * 5)
        hit_rows = con.execute(sql, params).fetchall()
    else:
        match = _match_expr(query)
        sql = (
            "SELECT m.session_id, m.project, m.seq, bm25(messages_fts) AS rank"
            " FROM messages_fts JOIN messages m ON m.id = messages_fts.rowid"
            " WHERE messages_fts MATCH ?"
        )
        params = [match]
        if since:
            sql += " AND m.ts >= ?"
            params.append(since)
        sql += " ORDER BY rank LIMIT ?"
        params.append(limit * 5)
        try:
            rows = con.execute(sql, params).fetchall()
        except sqlite3.OperationalError as e:
            print(f"[query error] {e}  (query='{query}')")
            return
        hit_rows = [(r[0], r[1], r[2]) for r in rows]

    if not hit_rows:
        print(f"no hits for: {query}")
        return
    _render_hits(con, hit_rows, query, limit)


def status(con: sqlite3.Connection) -> None:
    init_schema(con)
    nmsg = con.execute("SELECT count(*) FROM messages").fetchone()[0]
    nsess = con.execute("SELECT count(*) FROM sessions").fetchone()[0]
    nfiles = con.execute("SELECT count(*) FROM ingested_files").fetchone()[0]
    rng = con.execute("SELECT min(started_at), max(ended_at) FROM sessions").fetchone()
    print(f"db: {DB_PATH}")
    print(f"sqlite: {sqlite3.sqlite_version}")
    print(f"indexed files: {nfiles} / sessions: {nsess} / messages: {nmsg}")
    print(f"time range: {rng[0]} 〜 {rng[1]}")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    con = connect()
    try:
        if cmd == "index":
            t0 = time.time()
            s = index(con, verbose=True)
            print(f"indexed: {s} in {time.time()-t0:.1f}s")
            return 0
        if cmd == "status":
            status(con)
            return 0
        if cmd == "search":
            if len(argv) < 3:
                print("usage: search \"<query>\" [--limit N] [--since YYYY-MM-DD]")
                return 2
            query = argv[2]
            limit = 8
            since = None
            rest = argv[3:]
            for i, a in enumerate(rest):
                if a == "--limit" and i + 1 < len(rest):
                    limit = int(rest[i + 1])
                elif a == "--since" and i + 1 < len(rest):
                    since = rest[i + 1]
            search(con, query, limit, since)
            return 0
        print(__doc__)
        return 2
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
