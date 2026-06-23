"""
pdf_extract.py
目的: PDFからテキストを抽出してwiki/raw/に保存する
作成: ADA (Claude Code)
承認日: 2026-06-04
"""

import argparse
import io
import re
import sys
from datetime import date
from pathlib import Path

import pypdf

if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8")

WIKI_RAW = Path.home() / "Vault" / "wiki" / "raw"


def extract_text(pdf_path: Path) -> tuple[str, bool]:
    """テキストを抽出する。(text, was_encrypted) を返す。"""
    reader = pypdf.PdfReader(str(pdf_path))

    decrypted = False
    if reader.is_encrypted:
        result = reader.decrypt("")
        if result == pypdf.PasswordType.NOT_DECRYPTED:
            raise ValueError("パスワードが必要なPDFです。空パスワードでは復号できませんでした。")
        decrypted = True

    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages.append(f"## ページ {i + 1}\n\n{text.strip()}")

    return "\n\n".join(pages), decrypted


def save_to_wiki_raw(text: str, title: str, source: str = "PDF") -> Path:
    slug = re.sub(r"[^\w　-鿿゠-ヿ]", "-", title).strip("-").lower()
    slug = re.sub(r"-+", "-", slug)[:60]
    today = date.today().isoformat()
    filename = f"{today}_{slug}.md"
    out_path = WIKI_RAW / filename

    frontmatter = f"""---
title: {title}
source: {source}
date: {today}
type: pdf-extract
---

"""
    out_path.write_text(frontmatter + text, encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="PDFからwiki/raw/にテキストを抽出する")
    parser.add_argument("pdf", help="PDFファイルのパス")
    parser.add_argument("--title", help="タイトル（省略時はファイル名）")
    parser.add_argument("--source", default="PDF", help="出典名")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"エラー: ファイルが見つかりません: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    title = args.title or pdf_path.stem
    text, decrypted = extract_text(pdf_path)
    out_path = save_to_wiki_raw(text, title, args.source)

    pages = text.count("## ページ")
    print(f"抽出完了: {pages}ページ, {len(text)}文字")
    if decrypted:
        print("（空パスワードで復号しました）")
    print(f"保存先: {out_path}")


if __name__ == "__main__":
    main()
