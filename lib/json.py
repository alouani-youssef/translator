import json
import re
import hashlib
from typing import Any, Dict, List, Tuple
from lib.translator import translate_batch
from lib.context import build_context, generate_summary
from lib.queue_manager import db_queue
from lib.db import get_translation_metadata
from config import Config


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
            if k.lower() in ("icon", "icons"):
                continue
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




def translate_file_content(filename: str, data: Any, state=None, output_path=None) -> Any:

    content_str = json.dumps(data, ensure_ascii=False)

    content_hash = hashlib.md5(content_str.encode("utf-8")).hexdigest()
    context_cache_key = f"context:{filename}:{content_hash}"
    
    context = None
    if state:
        cached_context = state.get(context_cache_key)
        if cached_context:
            if isinstance(cached_context, bytes):
                cached_context = cached_context.decode("utf-8")
            context = json.loads(cached_context)

    if not context:
        context = build_context(
            filename,
            content_str,
            target_language=Config.TARGET_LANGUAGE
        )
        if state:
            state.set(context_cache_key, json.dumps(context), expire=86400)


    global_summary = state.get("global_summary") if state else ""
    if isinstance(global_summary, bytes):
        global_summary = global_summary.decode("utf-8")
    global_summary = global_summary or ""

    items = extract_strings(data)

    if not items:
        return data

    paths, texts = zip(*items)


    BATCH_SIZE = 20

    for i in range(0, len(texts), BATCH_SIZE):
        batch_paths = paths[i:i + BATCH_SIZE]
        batch_texts = texts[i:i + BATCH_SIZE]
        
        translated_batch = translate_batch(list(batch_texts), context, redis_client=state, global_summary=global_summary)
        
        batch_records = []
        for path, original, res in zip(batch_paths, batch_texts, translated_batch):
            translated = res["translation"]
            set_value(data, path, translated)
            
            if res.get("skip_db"):
                continue

            record = {
                "filename": filename,
                "property": path,
                "value": original,
                "language": Config.SOURCE_LANGUAGE,
                "translation": translated,
                "translation_language": Config.TARGET_LANGUAGE,
                "detected_input_lang": res.get("detected_input"),
                "detected_output_lang": res.get("detected_output"),
                "is_successed": res.get("is_successed", False),
                "score": None,
                "is_approved": res.get("is_approved", False),
                "is_verified": False,
                "verified_at": None,
                "notes": None,
                "translation_time": res.get("duration"),
                "input_size": res.get("input_size"),
                "output_size": res.get("output_size"),
                "size_difference": res.get("size_difference"),
                "is_duplicated": False,
                "duplication_count": 1
            }

            # Check duplication
            meta = get_translation_metadata(original, Config.SOURCE_LANGUAGE, Config.TARGET_LANGUAGE)
            record["is_duplicated"] = meta["is_duplicated"]
            record["duplication_count"] = meta["duplication_count"]

            batch_records.append(record)
        
        if batch_records:
            db_queue.push_batch(batch_records)
            # print(f"📥 Queued batch of {len(batch_records)} translations for {filename}")

        # Atomic Save: Save the file after each batch to ensure progress is persisted
        if output_path:
            try:
                import os
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"⚠️ Failed to incrementally save {filename}: {e}")

    return data