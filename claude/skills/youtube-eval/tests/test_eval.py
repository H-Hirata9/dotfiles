import sys

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent / "scripts"))

from eval import extract_video_id


@pytest.mark.parametrize(
    "url,expected_id",
    [
        ("https://www.youtube.com/watch?v=jZgcWCzxh1I", "jZgcWCzxh1I"),
        ("https://youtu.be/jZgcWCzxh1I", "jZgcWCzxh1I"),
        ("https://www.youtube.com/embed/jZgcWCzxh1I", "jZgcWCzxh1I"),
        ("https://www.youtube.com/watch?v=jZgcWCzxh1I&t=30s", "jZgcWCzxh1I"),
        ("https://www.youtube.com/shorts/jZgcWCzxh1I", "jZgcWCzxh1I"),
    ],
)
def test_extract_video_id_valid(url: str, expected_id: str) -> None:
    assert extract_video_id(url) == expected_id


@pytest.mark.parametrize(
    "url",
    [
        "https://www.example.com/watch?v=abc",
        "not_a_url",
        "",
    ],
)
def test_extract_video_id_invalid(url: str) -> None:
    with pytest.raises(ValueError):
        extract_video_id(url)
