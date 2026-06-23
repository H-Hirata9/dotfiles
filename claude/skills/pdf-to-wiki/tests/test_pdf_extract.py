import re

import pytest


def make_slug(title: str) -> str:
    slug = re.sub(r"[^\w　-鿿゠-ヿ]", "-", title).strip("-").lower()
    return re.sub(r"-+", "-", slug)[:60]


@pytest.mark.parametrize(
    "title,expected",
    [
        (
            "スタディング_テキスト1-1_経営と戦略の全体像",
            "スタディング_テキスト1-1_経営と戦略の全体像",
        ),
        ("My PDF Title!", "my-pdf-title"),
        ("  spaces  and---dashes  ", "spaces--and---dashes"),
        ("a" * 80, "a" * 60),
    ],
)
def test_make_slug_length_and_chars(title: str, expected: str) -> None:
    result = make_slug(title)
    assert len(result) <= 60
    assert not result.startswith("-")
    assert not result.endswith("-")


def test_make_slug_no_special_chars() -> None:
    slug = make_slug("hello world!")
    assert "!" not in slug
    assert " " not in slug


def test_make_slug_japanese_preserved() -> None:
    slug = make_slug("財務・会計テキスト")
    assert "財務" in slug
    assert "会計" in slug
    assert "テキスト" in slug
