import json
from typing import Any


# -----------------------------
# Utility Methods
# -----------------------------
def dict2json(python_dict: dict[str, Any]) -> str:
    """
    Pythonの辞書をJSON文字列に変換する。
    """
    return json.dumps(python_dict, indent=2, ensure_ascii=False)


def json2dict(json_string: str, error_key: str | None = "error") -> dict[Any, Any] | dict[str, Any]:
    """
    JSON文字列をPythonの辞書に変換する。
    JSONパースに失敗した場合は error_key をキーに元の文字列を返す。
    """
    try:
        # _extract_stringで{}部分を抜き出した上でパース
        extracted = _extract_string(json_string, start_string="{", end_string="}")
        python_dict = json.loads(extracted, strict=False)
    except ValueError:
        # パースに失敗したらエラーとしてそのまま文字列を返す
        if error_key is None:
            return {"error": json_string}
        return {error_key: json_string}

    if isinstance(python_dict, dict):
        return python_dict

    return {error_key: python_dict}


def _extract_string(text: str, start_string: str | None = None, end_string: str | None = None) -> str:
    """
    textから start_string 以降、end_string 以前の部分を抜き出す。
    例: start_string='{', end_string='}' なら最初の{}を抽出する。
    """
    # 最初の文字
    if start_string is not None and start_string in text:
        idx_head = text.index(start_string)
        text = text[idx_head:]
    # 最後の文字
    if end_string is not None and end_string in text:
        idx_tail = text.rindex(end_string) + len(end_string)
        text = text[:idx_tail]
    return text
