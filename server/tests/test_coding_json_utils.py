from app.coding.json_utils import strip_markdown_fences


def test_strip_fences() -> None:
    raw = "```json\n{\"a\": 1}\n```"
    assert strip_markdown_fences(raw) == '{"a": 1}'


def test_strip_plain() -> None:
    assert strip_markdown_fences('{"x": 2}') == '{"x": 2}'
