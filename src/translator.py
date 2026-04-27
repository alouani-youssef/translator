import json
import re
import time
from ollama import Client
from typing import List, Dict, Any, Optional
from src.config import Config
from src import prompts
from src.detection import LanguageDetectorService
from src.db import get_approved_translations


print(Config.TRANSLATION_LLM_URL)
print(Config.FALLBACK_TRANSLATION_LLM_URL)

TranslationLLMClient = Client(host=Config.TRANSLATION_LLM_URL)
FallbackLLMClient = Client(host=Config.FALLBACK_TRANSLATION_LLM_URL)
_detector = LanguageDetectorService()

def get_placeholders(text: str) -> List[str]:
    # Matches {{var}}, %s, :var, {var}
    patterns = [
        r"\{\{.*?\}\}",
        r"%s",
        r":\w+",
        r"\{.*?\}"
    ]
    found = []
    for p in patterns:
        found.extend(re.findall(p, text))
    return sorted(found)

def check_placeholders(original: str, translated: str) -> bool:
    orig_placeholders = get_placeholders(original)
    trans_placeholders = get_placeholders(translated)
    return sorted(orig_placeholders) == sorted(trans_placeholders)

def extract_json(raw: str) -> str:
    raw = re.sub(r"```(?:json)?\s*", "", raw)
    raw = re.sub(r"```", "", raw)
    raw = raw.strip()

    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = raw.find(start_char)
        if start == -1:
            continue

        end = raw.rfind(end_char)
        if end != -1 and end > start:
            candidate = raw[start:end + 1]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass

    return raw

def ollama_chat(prompt: str, client: Client, model: str, temperature: float = 0.3) -> str:
    request_time = time.time()
    print(f"Sending request to Ollama ({model})")
    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": temperature},
    )
    response_time = time.time()
    print(f"Response Received from {model} in {response_time - request_time} seconds")
    return response["message"]["content"].strip()

def translate_batch(
    texts: List[str],
    context: Dict[str, Any],
    redis_client=None,
    global_summary: str = ""
) -> List[Dict[str, Any]]:

    if not texts:
        return []
    if not context or not context.get("summary"):
        raise ValueError("❌ Context is required and must be precomputed (summary missing)")

    results: List[Optional[Dict[str, Any]]] = [None] * len(texts)
    missing_texts: List[str] = []
    missing_indexes: List[int] = []
    size_rules: List[str] = []

    try:
        approved_db_translations = get_approved_translations(texts, Config.SOURCE_LANGUAGE, Config.TARGET_LANGUAGE)
    except Exception as e:
        print(f"⚠️ Failed to fetch approved translations from DB: {e}")
        approved_db_translations = {}

    for i, text in enumerate(texts):
        # 1. Check if the text has any language
        detected_input = _detector.detect(text)
        if detected_input is None:
            # Skip translation and database storage for non-language content
            results[i] = {
                "translation": text,
                "detected_input": None,
                "detected_output": None,
                "is_successed": True,
                "duration": 0,
                "input_size": len(text),
                "output_size": len(text),
                "size_difference": 0.0,
                "is_approved": True,
                "skip_db": True # Custom flag for json.py
            }
            continue

        cache_key = f"tr:{hash(text)}"
        cached = redis_client.get(cache_key) if redis_client else None

        if cached:
            if isinstance(cached, bytes):
                cached = cached.decode("utf-8")
            
            detected_output = _detector.detect(cached)
            expected_lang = Config.TARGET_LANGUAGE.lower()[:2]
            size_diff = abs(len(cached) - len(text)) / max(len(text), 1)
            
            results[i] = {
                "translation": cached,
                "detected_input": detected_input,
                "detected_output": detected_output,
                "is_successed": detected_output == expected_lang,
                "duration": 0,
                "input_size": len(text),
                "output_size": len(cached),
                "size_difference": size_diff,
                "is_approved": False
            }
        elif text in approved_db_translations:
            db_trans = approved_db_translations[text]
            detected_output = _detector.detect(db_trans)
            expected_lang = Config.TARGET_LANGUAGE.lower()[:2]
            size_diff = abs(len(db_trans) - len(text)) / max(len(text), 1)
            
            results[i] = {
                "translation": db_trans,
                "detected_input": detected_input,
                "detected_output": detected_output,
                "is_successed": True,
                "duration": 0,
                "input_size": len(text),
                "output_size": len(db_trans),
                "size_difference": size_diff,
                "is_approved": True,
                "skip_db": True # Already in DB, approved and succeeded
            }
            if redis_client:
                redis_client.set(cache_key, db_trans, expire=86400)
        else:
            missing_texts.append(text)
            missing_indexes.append(i)
            # Calculate 20% margin for the prompt
            margin = int(len(text) * Config.SIZE_MARGIN_PRIMARY)
            size_rules.append(f"'{text[:20]}...': original {len(text)} chars, target {len(text)}±{margin} chars")

    if missing_texts:
        try:
            start_time = time.time()
            prompt = prompts.build_batch_prompt(
                missing_texts,
                context,
                Config.SOURCE_LANGUAGE,
                Config.TARGET_LANGUAGE,
                global_summary=global_summary,
                size_rules=size_rules,
                size_margin_pct=Config.SIZE_MARGIN_PRIMARY
            )
            
            # --- Primary Attempt ---
            try:
                raw = ollama_chat(prompt, TranslationLLMClient, Config.TRANSLATION_LLM)
                cleaned = extract_json(raw)
                parsed = json.loads(cleaned)
                if not isinstance(parsed, list):
                    raise ValueError("Invalid format")
            except Exception as e:
                print(f"⚠️ Primary LLM failed: {e}. Trying fallback...")
                raw = ollama_chat(prompt, FallbackLLMClient, Config.FALLBACK_TRANSLATION_LLM)
                cleaned = extract_json(raw)
                parsed = json.loads(cleaned)
            
            duration = (time.time() - start_time) / len(missing_texts)
            
            if not isinstance(parsed, list):
                raise ValueError("Invalid LLM response format even after fallback")

            for idx, translated in zip(missing_indexes, parsed):
                original = texts[idx]
                detected_input = _detector.detect(original)
                detected_output = _detector.detect(translated)
                expected_lang = Config.TARGET_LANGUAGE.lower()[:2]
                
                input_len = len(original)
                output_len = len(translated)
                size_diff = abs(output_len - input_len) / max(input_len, 1)
                
                placeholders_valid = check_placeholders(original, translated)
                
                # Use Primary Margin (20%)
                is_successed = detected_output == expected_lang and size_diff <= Config.SIZE_MARGIN_PRIMARY and placeholders_valid

                # --- Retry individual mismatch or primary size violation with Fallback ---
                is_fallback_approved = False
                if not is_successed:
                    reason = ""
                    if not placeholders_valid: reason = "Placeholder corruption"
                    elif detected_output != expected_lang: reason = f"Language mismatch ({detected_output})"
                    else: reason = f"Size constraint violated ({size_diff:.1%})"
                    
                    print(f"⚠️ {reason}. Retrying with fallback...")
                    
                    # Calculate exact margin for fallback prompt (20% instruction but we allow 60%)
                    margin_primary = int(input_len * Config.SIZE_MARGIN_PRIMARY)
                    single_prompt = prompts.build_batch_prompt(
                        [original],
                        context,
                        Config.SOURCE_LANGUAGE,
                        Config.TARGET_LANGUAGE,
                        global_summary=global_summary,
                        size_rules=[f"'{original[:20]}...': target {input_len}±{margin_primary} chars"],
                        size_margin_pct=Config.SIZE_MARGIN_FALLBACK
                    )
                    try:
                        raw_fb = ollama_chat(single_prompt, FallbackLLMClient, Config.FALLBACK_TRANSLATION_LLM)
                        cleaned_fb = extract_json(raw_fb)
                        parsed_fb = json.loads(cleaned_fb)
                        if isinstance(parsed_fb, list) and parsed_fb:
                            translated = parsed_fb[0]
                            output_len = len(translated)
                            size_diff = abs(output_len - input_len) / max(input_len, 1)
                            detected_output = _detector.detect(translated)
                            # Fallback allows up to 60%
                            if detected_output == expected_lang and size_diff <= Config.SIZE_MARGIN_FALLBACK and check_placeholders(original, translated):
                                is_successed = True
                                is_fallback_approved = True
                    except Exception as fb_err:
                        print(f"⚠️ Fallback retry failed: {fb_err}")

                results[idx] = {
                    "translation": translated if is_successed else original,
                    "detected_input": detected_input,
                    "detected_output": detected_output,
                    "is_successed": is_successed,
                    "duration": duration,
                    "input_size": input_len,
                    "output_size": output_len if is_successed else input_len,
                    "size_difference": size_diff,
                    "is_approved": is_fallback_approved
                }
                
                if is_successed and redis_client:
                    redis_client.set(f"tr:{hash(original)}", translated, expire=86400)

        except Exception as e:
            print(f"⚠️ Batch translation failed completely: {e}")
            for idx in missing_indexes:
                orig = texts[idx]
                results[idx] = {
                    "translation": orig,
                    "detected_input": _detector.detect(orig),
                    "detected_output": None,
                    "is_successed": False,
                    "duration": 0,
                    "input_size": len(orig),
                    "output_size": len(orig),
                    "size_difference": 0.0,
                    "is_approved": False
                }

    return [r for r in results if r is not None]

def translate(
    text: str,
    context: Dict[str, Any],
    redis_client=None,
    global_summary: str = ""
) -> str:
    result = translate_batch([text], context, redis_client, global_summary=global_summary)
    return result[0]["translation"] if result else text