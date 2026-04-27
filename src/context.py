import re
import json
import hashlib
from ollama import Client
from typing import Dict, Any, List, Optional
from src.config import Config
from src import prompts
SummaryLLMClient = Client(host=Config.SUMMARIZE_LLM_URL)

def infer_content_type(filename: str, path: str = "") -> str:
    name = filename.lower()
    if "product" in name:
        return "product_page"
    if "guest" in name:
        return "guest_user_type"
    if "staff" in name:
        return "staff_user_type"
    if "manager" in name:
        return "manager_user_type"
    if "blog" in name or "article" in name:
        return "blog_post"
    if "checkout" in name:
        return "checkout_page"
    if "about" in name:
        return "about_page"
    if "terms" in name or "privacy" in name:
        return "legal"
    if "pricing" in name:
        return "pricing_page"
    if "landing" in name:
        return "landing_page"
    if "footer" in name:
        return "footer"
    if "seo" in name:
        return "seo_metadata"
    if "/blog/" in path:
        return "blog_post"

    return "general"


def infer_intent(content_type: str) -> str:
    mapping = {
        "product_page": "conversion",
        "checkout_page": "transaction",
        "blog_post": "informational",
        "legal": "compliance",
        "about_page": "branding",
        "landing_page": "conversion",
        "pricing_page": "conversion",
        "footer": "navigation",
        "seo_metadata": "seo",
        "general": "informational",
    }
    return mapping.get(content_type, "informational")



def extract_keywords_basic(text: str, max_keywords: int = 10) -> List[str]:
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    freq: Dict[str, int] = {}

    for w in words:
        freq[w] = freq.get(w, 0) + 1

    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:max_keywords]]


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




def generate_summary(filename: str, content: str) -> str:
    try:
        prompt = prompts.build_summary_prompt(filename, content)
        response = SummaryLLMClient.chat(
            model=Config.SUMMARIZE_LLM,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2},
        )
        summary = response["message"]["content"].strip()
        return summary.replace("\n", " ")

    except Exception as e:
        print(f"⚠️ Summary generation failed: {e}")
        return ""



def generate_global_context(files: List[Dict[str, Any]]) -> str:
    """
    Generate a global context across multiple files for SEO / translation pipeline.
    
    Each file should contain:
    {
        "filename": str,
        "content": str,
        "path": Optional[str]
    }
    """

    try:
        # 🔹 Build compressed input for LLM
        compact_files = []

        for f in files:
            filename = f.get("filename", "unknown")
            content = f.get("content", "")[:2000]  # prevent token explosion
            path = f.get("path", "")

            content_type = infer_content_type(filename, path)

            compact_files.append({
                "filename": filename,
                "content_type": content_type,
                "content": content
            })

        prompt = prompts.build_global_context_prompt(compact_files)

        response = SummaryLLMClient.chat(
            model=Config.SUMMARIZE_LLM,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2},
        )

        raw = response["message"]["content"]
        cleaned = extract_json(raw)
        parsed = json.loads(cleaned)

        if isinstance(parsed, dict):
            return parsed

    except Exception as e:
        print(f"⚠️ Global context generation failed: {e}")

    # fallback
    return Config.GLOBAL_CONTEXT_FALLBACK



def enrich_context_with_llm(
    filename: str,
    content: str,
    base_context: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        prompt = prompts.build_context_prompt(filename, content, base_context)

        response = SummaryLLMClient.chat(
            model=Config.SUMMARIZE_LLM,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2},
        )

        raw = response["message"]["content"]
        cleaned = extract_json(raw)
        parsed = json.loads(cleaned)

        if isinstance(parsed, dict):
            return parsed

    except Exception as e:
        print(f"⚠️ Context enrichment failed: {e}")

    return {}


def compute_content_hash(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()

def build_context(
    filename: str,
    content: str,
    properties: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    properties = properties or {}

    print(f"🔍 Building context for {filename}...")
    content_type = infer_content_type(filename, properties.get("path", ""))
    intent = infer_intent(content_type)
    base_context: Dict[str, Any] = {
        "content_type": content_type,
        "intent": intent,
        "keywords": extract_keywords_basic(content),
        "industry": properties.get("industry", Config.DEFAULT_INDUSTRY),
        "tone": properties.get("tone", Config.DEFAULT_TONE),
        "audience": properties.get("audience", Config.DEFAULT_AUDIENCE),
        "entities": [],
        "glossary": {},
    }
    summary = properties.get("summary")
    if not summary:
        summary = generate_summary(filename, content)
    enriched = enrich_context_with_llm(filename, content, base_context)

    final_context: Dict[str, Any] = {
        **base_context,
        "summary": summary,
    }

    for key, value in enriched.items():
        if value:
            final_context[key] = value
    return final_context