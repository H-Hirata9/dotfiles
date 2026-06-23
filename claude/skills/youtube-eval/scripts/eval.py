"""
eval.py
目的: YouTube動画の字幕とメタデータを取得してADAが評価できる形式で出力
作成: ADA (Claude Code)
承認日: 2026-06-04
"""

import io
import json
import re
import sys
import urllib.request
from typing import Any

from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)

if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8")


def extract_video_id(url: str) -> str:
    pattern = r"(?:v=|/v/|youtu\.be/|/embed/|/shorts/)([a-zA-Z0-9_-]{11})"
    m = re.search(pattern, url)
    if m:
        return m.group(1)
    raise ValueError(f"video IDが取得できなかった: {url}")


def fetch_metadata(video_id: str) -> dict:
    oembed_url = (
        f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    )
    req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def fetch_transcript(video_id: str) -> tuple[str, str]:
    """(transcript_text, language) を返す。字幕なしなら ("(字幕なし)", "") を返す"""
    api = YouTubeTranscriptApi()
    try:
        transcript_list = api.list(video_id)
        transcript = None
        lang_used = ""
        for lang in ["ja", "en"]:
            try:
                transcript = transcript_list.find_transcript([lang])
                lang_used = lang
                break
            except NoTranscriptFound:
                continue
        if transcript is None:
            try:
                transcript = transcript_list.find_generated_transcript(["ja", "en"])
                lang_used = "auto"
            except NoTranscriptFound:
                return "(字幕なし)", ""

        data: Any = transcript.fetch()
        parts: list[str] = []
        for entry in data:
            if isinstance(entry, dict):
                parts.append(str(entry.get("text", "")))
            else:
                parts.append(str(entry.text))
        return " ".join(parts), lang_used
    except TranscriptsDisabled:
        return "(字幕が無効化されている)", ""


def main() -> None:
    if len(sys.argv) < 2:
        print("使用法: python eval.py <YouTube URL>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    video_id = extract_video_id(url)

    try:
        meta = fetch_metadata(video_id)
        title = meta.get("title", "不明")
        channel = meta.get("author_name", "不明")
    except Exception:
        title = "取得失敗"
        channel = "取得失敗"

    transcript, lang = fetch_transcript(video_id)

    print(f"タイトル: {title}")
    print(f"チャンネル: {channel}")
    print(f"URL: https://www.youtube.com/watch?v={video_id}")
    if lang:
        print(f"字幕言語: {lang}")
    print()
    print("【字幕・内容】")
    limit = 8000
    if len(transcript) > limit:
        print(transcript[:limit])
        print(f"\n... (省略: 全{len(transcript)}文字)")
    else:
        print(transcript)


if __name__ == "__main__":
    main()
