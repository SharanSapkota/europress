from functools import lru_cache
from pathlib import Path

PARAMS = Path(__file__).resolve().parents[3] / "configs" / "my_params.yaml"


def scalar(text: str):
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        return [scalar(x) for x in text[1:-1].split(",") if x.strip()]
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1]
    if text in ("null", "~", ""):
        return None
    if text in ("true", "false"):
        return text == "true"
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            pass
    return text


def parse(text: str) -> dict:
    root: dict = {}
    stack = [(-1, root)]
    for raw in text.splitlines():
        line = raw.split(" #")[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        key, _, value = line.strip().partition(":")
        while stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if value.strip():
            parent[key] = scalar(value)
        else:
            parent[key] = {}
            stack.append((indent, parent[key]))
    return root


@lru_cache
def params(path: Path = PARAMS) -> dict:
    return parse(path.read_text()) if path.exists() else {}
