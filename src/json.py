import json
import re
from typing import Any, Dict, List, Tuple
from src.translator import translate_batch
from src.context import build_context, generate_summary


_DATE_PATTERNS = [
    r"^\d{4}-\d{2}-\d{2}$",
    r"^\d{2}/\d{2}/\d{4}$",
    r"^\d{2}-\d{2}-\d{4}$",
]

_COMPILED_DATES = [re.compile(p) for p in _DATE_PATTERNS]


def is_translatable(text: str) -> bool:
    if not text.strip():
        return False

    if text.startswith(("http://", "https://", "www.", "/")):
        return False

    if re.search(r"@.+\.", text):
        return False

    try:
        float(text)
        return False
    except ValueError:
        pass

    for pattern in _COMPILED_DATES:
        if pattern.match(text):
            return False

    if (
        len(text) <= 30
        and " " not in text
        and re.fullmatch(r"[a-zA-Z0-9_\-]+", text)
        and (text == text.lower() or text == text.upper())
    ):
        return False

    return True

def extract_strings(data: Any, path="") -> List[Tuple[str, str]]:
    """
    Returns list of (json_path, value)
    """
    results = []

    if isinstance(data, str):
        if is_translatable(data):
            results.append((path, data))

    elif isinstance(data, dict):
        for k, v in data.items():
            results.extend(extract_strings(v, f"{path}.{k}" if path else k))

    elif isinstance(data, list):
        for i, item in enumerate(data):
            results.extend(extract_strings(item, f"{path}[{i}]"))

    return results


def set_value(data: Any, path: str, value: str):
    keys = re.split(r"\.(?![^\[]*\])", path)

    ref = data
    for k in keys[:-1]:
        if "[" in k:
            name, idx = re.match(r"(.*?)\[(\d+)\]", k).groups()
            ref = ref[name][int(idx)]
        else:
            ref = ref[k]

    last = keys[-1]
    if "[" in last:
        name, idx = re.match(r"(.*?)\[(\d+)\]", last).groups()
        ref[name][int(idx)] = value
    else:
        ref[last] = value




def translate_file_content(filename: str, data: Any, state=None) -> Any:

    content_str = json.dumps(data, ensure_ascii=False)

    cache_key = f"summary:{filename}"

    summary = None
    if state:
        summary = state.get(cache_key)

    if not summary:
        summary = generate_summary(filename, content_str)
        if state:
            state.set(cache_key, summary, expire=86400)
    context = build_context(
        filename,
        content_str,
        properties={"summary": summary}
    )


    items = extract_strings(data)

    if not items:
        return data

    paths, texts = zip(*items)


    BATCH_SIZE = 20
    translated_results = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        translated_batch = translate_batch(list(batch), context)
        translated_results.extend(translated_batch)


    for path, translated in zip(paths, translated_results):
        set_value(data, path, translated)

    return data