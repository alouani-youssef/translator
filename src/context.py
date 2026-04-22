import re
import json
import ollama
from typing import Dict, Any, List
from src.config import Config



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
        "general": "informational",
    }
    return mapping.get(content_type, "informational")


def extract_keywords_basic(text: str, max_keywords: int = 10) -> List[str]:
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    freq = {}

    for w in words:
        freq[w] = freq.get(w, 0) + 1

    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:max_keywords]]


# =========================
# LLM Enrichment
# =========================

def build_context_prompt(filename: str, content: str, base_context: Dict[str, Any]) -> str:
    return f"""
You are an expert content strategist and SEO analyst.

Analyze the following file and generate structured context for translation.

File name: {filename}
Base context: {json.dumps(base_context, ensure_ascii=False)}

Content:
\"\"\"
{content[:2000]}
\"\"\"

Return STRICT JSON with:
- industry
- tone
- audience
- keywords (list)
- entities (list of important names, brands, concepts)
- glossary (key terms mapping if needed)

Rules:
- Be concise
- No explanations
"""


def enrich_with_llm(filename: str, content: str, base_context: Dict[str, Any]) -> Dict[str, Any]:
    try:
        prompt = build_context_prompt(filename, content, base_context)

        response = ollama.chat(
            model=Config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3},
        )

        parsed = json.loads(response["message"]["content"])

        return parsed if isinstance(parsed, dict) else {}

    except Exception as e:
        print(f"⚠️ Context enrichment failed: {e}")
        return {}


# =========================
# Main Builder
# =========================

def build_context(
    filename: str,
    content: str,
    properties: Dict[str, Any] = None
) -> Dict[str, Any]:

    properties = properties or {}

    # Step 1: Heuristic base
    content_type = infer_content_type(filename, properties.get("path", ""))
    intent = infer_intent(content_type)

    base_context = {
        "content_type": content_type,
        "intent": intent,
        "keywords": extract_keywords_basic(content),
        "industry": properties.get("industry", "unknown"),
        "tone": properties.get("tone", "neutral"),
        "audience": properties.get("audience", "general"),
    }

    # Step 2: LLM enrichment
    enriched = enrich_with_llm(filename, content, base_context)

    # Step 3: Merge (LLM overrides heuristics when valid)
    final_context = {
        **base_context,
        **enriched
    }

    return final_context