from pydantic import ValidationError
import pytest

from src.domain.models import Paper


def test_paper_valid() -> None:
    """
    正常なデータを使って Paper モデルが問題なく生成できるかをテストする。
    """
    paper = Paper(
        title="A Great Title",
        category=["LLM", "Generative Model"],
        brief_digest="60文字以内でまとめた1文要約",
        url="https://example.com/paper.pdf",
        summary={
            "Q1": "何に関する論文かを詳しく説明",
            "Q2": "背景、新規性、方法などを分けて詳しく説明",
        },
    )
    assert paper.title == "A Great Title"
    assert paper.category == ["LLM", "Generative Model"]
    assert paper.brief_digest == "60文字以内でまとめた1文要約"
    assert paper.url == "https://example.com/paper.pdf"
    assert paper.summary == {
        "Q1": "何に関する論文かを詳しく説明",
        "Q2": "背景、新規性、方法などを分けて詳しく説明",
    }


def test_paper_invalid_title() -> None:
    """
    titleに数値を渡してしまった場合など、StrictStr でバリデーションエラーになるかをテストする。
    """
    with pytest.raises(ValidationError):
        Paper(
            title=1234,  # type: ignore[arg-type] # StrictStrに反する
            category=["LLM"],
            brief_digest="要約",
            url="https://example.com",
            summary={"Q1": "回答1"},
        )


def test_paper_invalid_category() -> None:
    """
    categoryには list[StrictStr] を要求しているため、
    リストの中に数値が含まれているとエラーになるかをテストする。
    """
    with pytest.raises(ValidationError):
        Paper(
            title="Some Title",
            category=["LLM", 999],  # type: ignore[list-item] # リスト内に数値
            brief_digest="要約",
            url="https://example.com",
            summary={"Q1": "回答1"},
        )


def test_paper_invalid_url() -> None:
    """
    urlにNoneや数値など文字列でない値を渡した場合のエラーをテストする。
    """
    with pytest.raises(ValidationError):
        Paper(
            title="Some Title",
            category=["LLM"],
            brief_digest="要約",
            url=None,  # type: ignore[arg-type] # StrictStrに反する
            summary={"Q1": "回答1"},
        )


def test_paper_invalid_summary_key() -> None:
    """
    summaryのキーが StrictStr であるため、文字列以外のキーを渡すとエラーになるかをテストする。
    """
    with pytest.raises(ValidationError):
        Paper(
            title="Some Title",
            category=["LLM"],
            brief_digest="要約",
            url="https://example.com",
            summary={
                1: "キーが数値",  # type: ignore[dict-item] # StrictStrではない
            },
        )


def test_paper_invalid_summary_value() -> None:
    """
    summaryのバリューも StrictStr であるため、文字列以外の値を渡すとエラーになるかをテストする。
    """
    with pytest.raises(ValidationError):
        Paper(
            title="Some Title",
            category=["LLM"],
            brief_digest="要約",
            url="https://example.com",
            summary={
                "Q1": None,  # type: ignore[dict-item] # StrictStrではない
            },
        )
