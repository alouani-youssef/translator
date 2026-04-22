import json
import re
import ollama
from typing import List, Dict, Any
from src.config import Config


def build_translation_prompt(text: str, context: Dict[str, Any]) -> str:
    return f"""
You are a content writter specialized in marketing and SEO for Saas B2B.
Target language: {Config.TARGET_LANGUAGE}

Context:
- Industry: "Restaurant Management Software"
- Tone: "professional, friendly, and persuasive"
- Audience: "restaurant owners and managers"
- Keywords to preserve: {context.get("keywords", [])}
- Glossary (strict mapping): {context.get("glossary", {})}

Instructions:
- Preserve meaning, tone, and SEO intent
- Adapt naturally (not literal translation)
- Respect glossary strictly if provided
- Keep important keywords
- Keep Stracture of the output exactly as the input

Return ONLY the translated text.

Text:
{text}
"""


def build_scoring_prompt(text: str, candidates: List[str]) -> str:
    return f"""
You are a translation quality evaluator.

Original text:
{text}

Target language: {Config.TARGET_LANGUAGE}

Evaluate each translation based on:
- Accuracy
- Fluency
- SEO quality
- Context alignment

Return STRICT JSON:
[
  {{"translation": "...", "score": 0-10}}
]

Translations:
{json.dumps(candidates, ensure_ascii=False, indent=2)}
"""


def build_validation_prompt(original: str, translation: str, context: Dict[str, Any]) -> str:
    return f"""
You are a strict QA reviewer.

Original:
{original}

Translation:
{translation}

Context:
{json.dumps(context, ensure_ascii=False)}

Check:
- Meaning preserved?
- No hallucinations?
- SEO keywords respected?
- Fits context?

Return ONLY:
PASS
or
FAIL: <short reason>
"""


def ollama_chat(prompt: str, temperature: float = 0.5) -> str:
    response = ollama.chat(
        model=Config.LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": temperature},
    )
    return response["message"]["content"].strip()


def generate_candidates(text: str, context: Dict[str, Any], n: int = 3) -> List[str]:
    candidates = []

    for _ in range(n):
        try:
            prompt = build_translation_prompt(text, context)
            result = ollama_chat(prompt, temperature=0.7)
            if result:
                candidates.append(result)
        except Exception as e:
            print(f"⚠️ Candidate generation error: {e}")

    return list(set(candidates))  # deduplicate


def score_candidates(text: str, candidates: List[str]) -> List[Dict[str, Any]]:
    if not candidates:
        return []

    try:
        print(text)
        print(candidates)
        prompt = build_scoring_prompt(text, candidates)
        raw = ollama_chat(prompt, temperature=0.2)
        print("raw", raw)
        cleaned_raw = clean_json_response(raw)
        print("cleaned_raw", cleaned_raw)
        parsed = json.loads(cleaned_raw)
        print("parsed", parsed)
        if isinstance(parsed, list):
            return parsed
    except Exception as e:
        print(f"⚠️ Scoring failed: {e}")

    return [{"translation": c, "score": 5} for c in candidates]




def clean_json_response(raw: str) -> str:
    # Remove ```json ... ``` or ``` blocks
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```", "", raw)

    # Trim spaces
    raw = raw.strip()

    return raw

def select_best(scored: List[Dict[str, Any]]) -> str:
    if not scored:
        return ""

    scored_sorted = sorted(scored, key=lambda x: x.get("score", 0), reverse=True)
    return scored_sorted[0]["translation"]


def validate_translation(original: str, translation: str, context: Dict[str, Any]) -> bool:
    try:
        prompt = build_validation_prompt(original, translation, context)
        result = ollama_chat(prompt, temperature=0)

        return result.startswith("PASS")

    except Exception as e:
        print(f"⚠️ Validation error: {e}")
        return True  # fail-open



def translate(text: str, context: Dict[str, Any] = None) -> str:
    if not text or not text.strip():
        return text
    context = context or {}

    try:
        candidates = generate_candidates(text, context, n=3)

        if not candidates:
            return text

        scored = score_candidates(text, candidates)

        best = select_best(scored)

        if not best:
            return candidates[0]

        is_valid = validate_translation(text, best, context)

        if not is_valid:
            print("⚠️ QA failed, fallback used")
            return candidates[0]

        return best

    except ollama.ResponseError as e:
        print(f"❌ Ollama error: {e}")
        return text

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return text