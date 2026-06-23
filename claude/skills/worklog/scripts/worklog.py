"""
worklog
目的: ADAが完了したタスクをVaultの作業ログに追記し、Google Driveにミラーする
作成: ADA (Claude Code)
承認日: 2026-06-21
"""

import argparse
import html
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
VAULT_DIR = Path.home() / "Vault" / "ada_worklog"
DRIVE_FOLDER = "ada_worklog"
_FOLDER_MIME = "application/vnd.google-apps.folder"
_DOC_MIME = "application/vnd.google-apps.document"
_LABELS = ("依頼:", "やったこと:", "成果物:")


def day_filename(dt: datetime) -> str:
    return f"{dt:%Y-%m-%d}.md"


def format_entry(title: str, request: str, did: str, artifacts: str, dt: datetime) -> str:
    lines = [
        f"## {dt:%Y-%m-%d %H:%M} — {title}",
        f"依頼: {request}",
        f"やったこと: {did}",
    ]
    if artifacts:
        lines.append(f"成果物: {artifacts}")
    return "\n".join(lines) + "\n\n"


def append_entry(vault_dir: Path, dt: datetime, entry: str) -> Path:
    vault_dir.mkdir(parents=True, exist_ok=True)
    path = vault_dir / day_filename(dt)
    if not path.exists():
        path.write_text(f"# ADA作業ログ {dt:%Y-%m-%d}\n\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as f:
        f.write(entry)
    return path


def md_to_html(md: str) -> str:
    body: list[str] = []
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("# "):
            body.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{html.escape(line[3:])}</h2>")
        else:
            label = next((lb for lb in _LABELS if line.startswith(lb)), None)
            if label:
                rest = html.escape(line[len(label):].lstrip())
                body.append(f"<p><b>{label}</b> {rest}</p>")
            else:
                body.append(f"<p>{html.escape(line)}</p>")
    return "<html><body>\n" + "\n".join(body) + "\n</body></html>\n"


def _extract_json(text: str) -> dict:
    start = text.find("{")
    if start == -1:
        raise ValueError(f"no JSON in output: {text[:200]}")
    return json.loads(text[start:])


def _run(args: list[str], cwd: str | None = None) -> str:
    result = subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8", cwd=cwd
    )
    if result.returncode != 0:
        raise RuntimeError(f"gws failed: {' '.join(args)}\n{result.stderr}")
    return result.stdout


def sync_to_drive(path: Path, folder_name: str = DRIVE_FOLDER, run=_run) -> str:
    """Vaultの月次mdをHTMLに変換し、Drive上のGoogleドキュメント(同月)をupdate-or-createする。"""
    folder_q = (
        f"name='{folder_name}' and mimeType='{_FOLDER_MIME}' and trashed=false"
    )
    res = _extract_json(
        run(["gws", "drive", "files", "list", "--params",
             json.dumps({"q": folder_q, "fields": "files(id,name)"})])
    )
    folders = res.get("files", [])
    if folders:
        folder_id = folders[0]["id"]
    else:
        created = _extract_json(
            run(["gws", "drive", "files", "create", "--json",
                 json.dumps({"name": folder_name, "mimeType": _FOLDER_MIME})])
        )
        folder_id = created["id"]

    doc_name = path.stem  # 例: 2026-06（拡張子なし＝Googleドキュメント名）
    doc_q = (
        f"name='{doc_name}' and '{folder_id}' in parents "
        f"and mimeType='{_DOC_MIME}' and trashed=false"
    )
    res2 = _extract_json(
        run(["gws", "drive", "files", "list", "--params",
             json.dumps({"q": doc_q, "fields": "files(id,name)"})])
    )
    existing = res2.get("files", [])

    html_path = path.with_suffix(".html")
    html_path.write_text(md_to_html(path.read_text(encoding="utf-8")), encoding="utf-8")
    cwd = str(path.parent)
    html_name = html_path.name
    try:
        if existing:
            doc_id = existing[0]["id"]
            run(["gws", "drive", "files", "update", "--params",
                 json.dumps({"fileId": doc_id}),
                 "--upload", html_name, "--upload-content-type", "text/html"], cwd=cwd)
            return doc_id

        created = _extract_json(
            run(["gws", "drive", "files", "create", "--json",
                 json.dumps({"name": doc_name, "parents": [folder_id], "mimeType": _DOC_MIME}),
                 "--upload", html_name, "--upload-content-type", "text/html"], cwd=cwd)
        )
        return created["id"]
    finally:
        html_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="ADA作業ログに追記しDriveにミラーする")
    parser.add_argument("--title", required=True)
    parser.add_argument("--request", required=True)
    parser.add_argument("--did", required=True)
    parser.add_argument("--artifacts", default="")
    parser.add_argument("--at", default=None, help="ISO8601。省略時は現在(JST)")
    parser.add_argument("--no-drive", action="store_true", help="Driveミラーを行わない")
    args = parser.parse_args()

    dt = datetime.fromisoformat(args.at).astimezone(JST) if args.at else datetime.now(JST)
    entry = format_entry(args.title, args.request, args.did, args.artifacts, dt)
    path = append_entry(VAULT_DIR, dt, entry)
    print(f"appended: {path}")

    if not args.no_drive:
        file_id = sync_to_drive(path)
        print(f"drive synced: {file_id}")


if __name__ == "__main__":
    main()
