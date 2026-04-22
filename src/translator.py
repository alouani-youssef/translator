import json
import re
from ollama import Client
from typing import List, Dict, Any, Optional
from src.config import Config
llm_translate_client = Client(host=Config.TRANSLATION_LLM_URL)
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


# =========================================================
# PROMPT (BATCH)
# =========================================================

def build_batch_prompt(texts: List[str], context: Dict[str, Any]) -> str:
    return f"""You are a professional translator specialized in SaaS marketing.

Target language: {Config.TARGET_LANGUAGE}
Source language: {Config.SOURCE_LANGUAGE}

=== CONTEXT ===
Summary: {context.get("summary", "")}
Industry: {context.get("industry", "")}
Tone: {context.get("tone", "")}
Audience: {context.get("audience", "")}
Content type: {context.get("content_type", "")}
Intent: {context.get("intent", "")}

Glossary:
{json.dumps(context.get("glossary", {}), ensure_ascii=False)}

Entities to preserve:
{context.get("entities", [])}

=== RULES ===
- Preserve meaning, tone, and SEO intent
- Keep placeholders like {{name}}, %s, :var unchanged
- Respect glossary strictly
- Keep brand/entity names unchanged
- Return ONLY JSON array of translated strings
- Same order as input

=== TEXTS ===
{json.dumps(texts, ensure_ascii=False, indent=2)}
"""


def ollama_chat(prompt: str, temperature: float = 0.3) -> str:
    print(f"Prompt: {prompt}")
    response = llm_translate_client.chat(
        model=Config.TRANSLATION_LLM,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": temperature},
    )
    print(f"Response: {response}")
    return response["message"]["content"].strip()



def translate_batch(
    texts: List[str],
    context: Dict[str, Any],
    redis_client=None
) -> List[str]:

    if not texts:
        return []
    if not context or not context.get("summary"):
        raise ValueError("❌ Context is required and must be precomputed (summary missing)")

    results: List[Optional[str]] = [None] * len(texts)
    missing_texts: List[str] = []
    missing_indexes: List[int] = []

    for i, text in enumerate(texts):
        cache_key = f"tr:{hash(text)}"

        cached = redis_client.get(cache_key) if redis_client else None

        if cached:
            results[i] = cached
        else:
            missing_texts.append(text)
            missing_indexes.append(i)

    if missing_texts:
        try:
            prompt = build_batch_prompt(missing_texts, context)

            raw = ollama_chat(prompt)
            cleaned = extract_json(raw)
            parsed = json.loads(cleaned)

            if not isinstance(parsed, list):
                raise ValueError("Invalid LLM response format")

            for idx, translated in zip(missing_indexes, parsed):
                results[idx] = translated
                if redis_client:
                    redis_client.set(
                        f"tr:{hash(texts[idx])}",
                        translated,
                        expire=86400
                    )

        except Exception as e:
            print(f"⚠️ Batch translation failed: {e}")

            # fallback: return original texts for failed ones
            for idx in missing_indexes:
                results[idx] = texts[idx]

    return [r if r is not None else texts[i] for i, r in enumerate(results)]



def translate(
    text: str,
    context: Dict[str, Any],
    redis_client=None
) -> str:
    result = translate_batch([text], context, redis_client)
    return result[0] if result else text