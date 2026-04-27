import json
from typing import List, Dict, Any

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

def build_global_context_prompt(compact_files: List[Dict[str, Any]]) -> str:
    return f"""
You are an expert global SEO and content strategist.

You are analyzing a full application containing multiple content files.

Your task is to generate a SINGLE unified global context that represents the entire system.

Files:
{json.dumps(compact_files, ensure_ascii=False, indent=2)}

Return ONLY a raw JSON object with this structure:

{{
  "industry": "string describing the overall industry",
  "tone": "global tone of all content",
  "audience": "primary target audience",
  "keywords": ["most important global keywords"],
  "entities": ["brands", "products", "services mentioned across files"],
  "glossary": {{
    "source_term": "standardized_term"
  }},
  "summary": "1 paragraph describing the entire system"
}}

Rules:
- Be consistent across files
- Merge repeated concepts
- Avoid duplication
- No explanations
- Output ONLY valid JSON
"""

def build_batch_prompt(
    texts: List[str],
    context: Dict[str, Any],
    source_language: str,
    target_language: str,
    global_summary: str = "",
    size_rules: List[str] = None,
    size_margin_pct: float = 0.2
) -> str:
    glossary = json.dumps(context.get("glossary", {}), ensure_ascii=False)
    entities = context.get("entities", [])
    parts = [
        f"Translate from {source_language} to {target_language}.",
    ]
    if global_summary:
        parts.append(f"Project: {global_summary}")
    
    rule_size = f"The length of each translation should be within {size_margin_pct:.0%} of the original text's length."
    if size_rules:
        rule_size = f"Strict size constraints (max {size_margin_pct:.0%} diff):\n" + "\n".join(size_rules)

    parts += [
        f"Tone: {context.get('tone', '')} | Audience: {context.get('audience', '')}",
        f"Glossary: {glossary}" if context.get("glossary") else "",
        f"Preserve entities: {entities}" if entities else "",
        f"Rules: Keep placeholders ({{{{name}}}}, %s, :var) and brand names unchanged. {rule_size} Return ONLY a JSON array of translated strings, same order as input.",
        f"\nTexts:\n{json.dumps(texts, ensure_ascii=False, indent=2)}",
    ]
    return "\n".join(p for p in parts if p)

def build_validation_prompt(
    source_text: str,
    translated_text: str,
    source_lang: str,
    target_lang: str
) -> str:
    return f"""
        You are an expert linguist and quality assurance specialist.
        Verify if the following translation is accurate and maintains the original meaning and structure.
        
        Source ({source_lang}): {source_text}
        Translation ({target_lang}): {translated_text}
        
        Rules:
        - Check for meaning preservation.
        - Check for structural integrity (placeholders, variables).
        - Check for natural phrasing in the target language.
        
        Return ONLY a JSON object with:
        {{
          "is_valid": true/false,
          "reason": "MANDATORY detailed explanation if is_valid is false, else empty string"
        }}
    """
