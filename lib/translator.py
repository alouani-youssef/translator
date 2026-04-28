import json
import re
import time
from ollama import Client
from typing import List, Dict, Any, Optional
from config import Config
from lib import prompts
from lib.detection import LanguageDetectorService
from lib.db import get_approved_translations

TranslationLLMClient = Client(host=Config.TRANSLATION_LLM_URL)
FallbackLLMClient = Client(host=Config.FALLBACK_TRANSLATION_LLM_URL)
_detector = LanguageDetectorService()

def get_placeholders(text: str) -> List[str]:
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

def extract_json(raw: Any) -> str:
    if not isinstance(raw, str):
        return str(raw)
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

def clean_translation(text: str) -> str:
    """Removes conversational filler from LLM responses."""
    if not text: return ""
    
    # 1. Remove common introductory phrases
    text = re.sub(r"^(here is|corrected|translation|fix|result)[:\s]*", "", text, flags=re.IGNORECASE | re.MULTILINE)
    
    # 2. Extract content from quotes if present
    quoted = re.findall(r'"([^"]+)"', text)
    if quoted:
        # Return the one that doesn't look like an English explanation (simple heuristic)
        for q in reversed(quoted):
            if not re.search(r"[a-zA-Z]{5,}", q): # If it doesn't have long English words, it's likely the target
                return q.strip()
        return quoted[-1].strip()

    # 3. Take the first non-empty line that doesn't look like English meta-commentary
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for l in lines:
        if not re.match(r"^(note|change|improvement|fluency|correction|i made)", l, re.I):
            return l
            
    return text.strip()

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
    global_summary: str = "",
    source_language: Optional[str] = None,
    target_language: Optional[str] = None
) -> List[Dict[str, Any]]:

    if not texts:
        return []
    if not context or not context.get("summary"):
        raise ValueError("❌ Context is required and must be precomputed (summary missing)")

    results: List[Optional[Dict[str, Any]]] = [None] * len(texts)
    missing_texts: List[str] = []
    missing_indexes: List[int] = []
    size_rules: List[str] = []

    source_lang = source_language or Config.SOURCE_LANGUAGE
    target_lang = target_language or Config.TARGET_LANGUAGE

    try:
        approved_db_translations = get_approved_translations(texts, source_lang, target_lang)
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
            expected_lang = target_lang.lower()[:2]
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
            expected_lang = target_lang.lower()[:2]
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
            margin = int(len(text) * Config.SIZE_MARGIN_PRIMARY)
            size_rules.append(f"'{text[:20]}...': original {len(text)} chars, target {len(text)}±{margin} chars")

    if missing_texts:
        try:
            start_time = time.time()
            
            # --- Pass 1: Draft ---
            print(f"📝 Drafting batch of {len(missing_texts)} translations...")
            draft_prompt = prompts.build_translation_draft_prompt(missing_texts, context, source_lang, target_lang)
            draft_raw = ollama_chat(draft_prompt, TranslationLLMClient, Config.TRANSLATION_LLM)
            try:
                drafts = json.loads(extract_json(draft_raw))
                if not isinstance(drafts, list): raise ValueError("Drafts not a list")
                # Sanitize to ensure list of strings
                drafts = [t if isinstance(t, str) else (t.get("translation") or t.get("translatedText") or str(t)) if isinstance(t, dict) else str(t) for t in drafts]
            except Exception as e:
                print(f"⚠️ Draft JSON failed: {e}. Repairing...")
                repair_prompt = prompts.build_json_repair_prompt(draft_raw)
                repaired = ollama_chat(repair_prompt, TranslationLLMClient, Config.TRANSLATION_LLM)
                drafts = json.loads(extract_json(repaired))
                # Sanitize to ensure list of strings
                drafts = [t if isinstance(t, str) else (t.get("translation") or t.get("translatedText") or str(t)) if isinstance(t, dict) else str(t) for t in drafts]

            # --- Pass 2: Refine ---
            print(f"✨ Refining batch...")
            refine_prompt = prompts.build_translation_refine_prompt(drafts, context, target_lang)
            print(refine_prompt)
            refine_raw = ollama_chat(refine_prompt, TranslationLLMClient, Config.TRANSLATION_LLM)
            try:
                refined = json.loads(extract_json(refine_raw))
                if not isinstance(refined, list): raise ValueError("Refined not a list")
                # Sanitize to ensure list of strings
                refined = [t if isinstance(t, str) else (t.get("translation") or t.get("translatedText") or str(t)) if isinstance(t, dict) else str(t) for t in refined]
            except Exception as e:
                print(f"⚠️ Refine JSON failed: {e}. Repairing...")
                repair_prompt = prompts.build_json_repair_prompt(refine_raw)
                repaired = ollama_chat(repair_prompt, TranslationLLMClient, Config.TRANSLATION_LLM)
                refined = json.loads(extract_json(repaired))

            duration = (time.time() - start_time) / len(missing_texts)

            # --- Pass 3 & 4: Validate and Fix (Per Text) ---
            for idx, original, trans in zip(missing_indexes, missing_texts, refined):
                detected_input = _detector.detect(original)
                expected_lang = target_lang.lower()[:2]
                
                # Fast check: Placeholders
                orig_ph = get_placeholders(original)
                trans_ph = get_placeholders(trans)
                placeholders_valid = sorted(orig_ph) == sorted(trans_ph)
                
                # Deep check: LLM Validation
                is_valid = False
                notes = ""
                if placeholders_valid:
                    print(f"🔍 Validating: {original[:20]} -> {trans[:20]}...")
                    valid_prompt = prompts.build_validation_prompt(original, trans, source_lang, target_lang)
                    valid_raw = ollama_chat(valid_prompt, TranslationLLMClient, Config.TRANSLATION_LLM)
                    try:
                        valid_data = json.loads(extract_json(valid_raw))
                        is_valid = valid_data.get("is_valid", False)
                        notes = valid_data.get("reason", "")
                    except:
                        is_valid = True # Assume valid if validation LLM fails to output JSON
                else:
                    notes = f"Placeholder mismatch: expected {orig_ph}, got {trans_ph}"

                # Pass 4: Fix
                if not is_valid:
                    print(f"🛠️ Fixing translation for: {original[:30]}... (Reason: {notes})")
                    fix_prompt = prompts.build_fix_translation_prompt(original, trans, target_lang)
                    trans = ollama_chat(fix_prompt, FallbackLLMClient, Config.FALLBACK_TRANSLATION_LLM)
                    trans = clean_translation(trans)
                    
                    # Re-verify after fix
                    detected_output = _detector.detect(trans)
                    is_successed = detected_output == expected_lang and check_placeholders(original, trans)
                else:
                    detected_output = _detector.detect(trans)
                    is_successed = True

                input_len = len(original)
                output_len = len(trans)
                size_diff = abs(output_len - input_len) / max(input_len, 1)

                results[idx] = {
                    "translation": trans,
                    "detected_input": detected_input,
                    "detected_output": detected_output,
                    "is_successed": is_successed,
                    "duration": duration,
                    "input_size": input_len,
                    "output_size": output_len,
                    "size_difference": size_diff,
                    "is_approved": False, # Approval is handled by the verification module
                    "notes": notes if not is_valid else None
                }
                
                if is_successed and redis_client:
                    redis_client.set(f"tr:{hash(original)}", trans, expire=86400)

        except Exception as e:
            print(f"⚠️ Pipeline failed: {e}")
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