import re
from src.translator import translate


# ------------------------------------------------------------------
# Patterns
# ------------------------------------------------------------------

_DATE_PATTERNS = [
    r"^\d{4}-\d{2}-\d{2}$",        # YYYY-MM-DD
    r"^\d{2}/\d{2}/\d{4}$",        # DD/MM/YYYY or MM/DD/YYYY
    r"^\d{2}-\d{2}-\d{4}$",        # DD-MM-YYYY or MM-DD-YYYY
]

_COMPILED_DATES = [re.compile(p) for p in _DATE_PATTERNS]


def is_translatable(text: str) -> bool:

    # Empty / whitespace only
    if not text.strip():
        return False

    # URL
    if text.startswith("http://") or text.startswith("https://") or text.startswith("www.") or text.startswith("/"):
        return False

    # Email  (contains @ with at least one dot after it)
    if re.search(r"@.+\.", text):
        return False

    # Pure number string
    try:
        float(text)
        return False
    except ValueError:
        pass

    # Date
    for pattern in _COMPILED_DATES:
        if pattern.match(text):
            return False

    # Enum-like: short, no spaces, only word-chars + hyphens/underscores,
    # and either all lowercase or all uppercase
    if (
        len(text) <= 30
        and " " not in text
        and re.fullmatch(r"[a-zA-Z0-9_\-]+", text)
        and (text == text.lower() or text == text.upper())
    ):
        return False

    return True




def walk(data) -> any:


    if isinstance(data, str):
        if is_translatable(data):
            return translate(data)
        return data

    elif isinstance(data, dict):
        return {key: walk(value) for key, value in data.items()}

    elif isinstance(data, list):
        return [walk(item) for item in data]

    else:
        return data

def translateContent(fileName: str, data: dict | list) -> any:
    context = getContext(fileName)
    return walk(data, context)
