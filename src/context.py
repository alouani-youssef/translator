import re
import json
import hashlib
from ollama import Client
from typing import Dict, Any, List, Optional
from src.config import Config
print(f"Lunching Summary Client On : {Config.SUMMARIZE_LLM_URL}. The Model Is Used For Content Management")
llm_summary_client = Client(host=Config.SUMMARIZE_LLM_URL)

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


def build_summary_prompt(filename: str, content: str) -> str:
    return f"""
    You are an expert content strategist.
    Summarize the following file, in a single pharagraph, because it will be used as a context for translation:
    File name: {filename}
    Content:
    \"\"\"
    {content}
    \"\"\"
    Rules:
    - Plain text only
    - No JSON
    - No explanation
    - Keep it short and clear
"""


def generate_summary(filename: str, content: str) -> str:
    try:
        prompt = build_summary_prompt(filename, content)
        response = llm_summary_client.chat(
            model=Config.SUMMARIZE_LLM,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2},
        )
        summary = response["message"]["content"].strip()
        return summary.replace("\n", " ")

    except Exception as e:
        print(f"⚠️ Summary generation failed: {e}")
        return ""

def build_context_prompt(
    filename: str,
    content: str,
    base_context: Dict[str, Any]
) -> str:
    return f"""
You are an expert content strategist and SEO analyst for a Restaurant Management SaaS.

Analyze the following file and generate structured context.

File name: {filename}
Base context: {json.dumps(base_context, ensure_ascii=False)}

Content (first 2000 chars):
\"\"\"
{content[:2000]}
\"\"\"

Return ONLY a raw JSON object with these exact keys:

{{
  "industry": "string describing the industry",
  "tone": "string describing the writing tone",
  "audience": "string describing the target audience",
  "keywords": ["list", "of", "important", "keywords"],
  "entities": ["list", "of", "important", "brand", "or", "product", "names"],
  "glossary": {{"source_term": "target_term"}}
}}

Rules:
- No summary here
- Be concise
- No prose outside JSON
"""


def enrich_context_with_llm(
    filename: str,
    content: str,
    base_context: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        prompt = build_context_prompt(filename, content, base_context)

        response = llm_summary_client.chat(
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
        "industry": properties.get("industry", "Restaurant Management Software"),
        "tone": properties.get("tone", "professional, friendly, and persuasive"),
        "audience": properties.get("audience", "restaurant owners and managers"),
        "entities": [],
        "glossary": {},
    }

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