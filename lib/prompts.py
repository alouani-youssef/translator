import json
from typing import List, Dict, Any



def build_summary_prompt(
    filename: str,
    content: str,
    target_language: str = "English"
) -> str:
    return f"""
You are a content analyst.

Task:
Summarize the file for translation context.

Constraints:
- Output language: {target_language}
- One short paragraph
- No explanations
- No formatting

Input:
File: {filename}
Content:
\"\"\"
{content[:3000]}
\"\"\"
"""



def build_context_prompt(
    filename: str,
    content: str,
    base_context: Dict[str, Any],
    target_language: str = "English"
) -> str:
    return f"""
You are a structured data extractor.

Task:
Extract translation context.

Output language for VALUES: {target_language}

JSON SCHEMA:
{{
  "industry": "string",
  "tone": "string",
  "audience": "string",
  "keywords": ["string"],
  "entities": ["string"],
  "glossary": {{"source_term": "target_term"}}
}}

Rules:
- Output ONLY valid JSON
- No extra text
- All values MUST be in {target_language}
- Keep fields short and precise

Example:
{{
  "industry": "Restaurant SaaS",
  "tone": "Professional and friendly",
  "audience": "Restaurant owners",
  "keywords": ["POS", "orders"],
  "entities": ["Stripe"],
  "glossary": {{"order": "commande"}}
}}

Input:
File: {filename}
Base context: {json.dumps(base_context, ensure_ascii=False)}

Content:
\"\"\"
{content[:2000]}
\"\"\"
"""



def build_global_context_prompt(
    compact_files: List[Dict[str, Any]],
    target_language: str = "English"
) -> str:
    return f"""
You are a structured aggregator.

Task:
Merge multiple file contexts into ONE global context.

Output language: {target_language}

JSON SCHEMA:
{{
  "industry": "string",
  "tone": "string",
  "audience": "string",
  "keywords": ["string"],
  "entities": ["string"],
  "glossary": {{"source_term": "target_term"}},
  "summary": "string"
}}

Rules:
- Output ONLY valid JSON
- Merge duplicates
- Keep consistency
- All values in {target_language}

Input:
{json.dumps(compact_files, ensure_ascii=False)}
"""


def build_translation_draft_prompt(
    texts: List[str],
    context: Dict[str, Any],
    source_language: str,
    target_language: str
) -> str:
    glossary = json.dumps(context.get("glossary", {}), ensure_ascii=False)

    return f"""
You are a professional translation engine.

Task:
Translate the following list of strings from {source_language} to {target_language}.

Context:
- Industry: {context.get('industry', 'General')}
- Summary: {context.get('summary', '')}

Constraint Hierarchy (Priority 1 is most important):
1. MEANING: Preserve the original meaning exactly. No omissions or additions.
2. TECHNICAL: Preserve all placeholders ({{{{name}}}}, %s, :var, {{var}}), numbers, and brand names.
3. GLOSSARY: Use the provided glossary terms strictly.

Glossary:
{glossary}

Output:
Return ONLY a raw JSON array of translated strings.

Example:
["translated_text_1", "translated_text_2"]

Texts:
{json.dumps(texts, ensure_ascii=False)}
"""



def build_translation_refine_prompt(
    draft_translations: List[str],
    context: Dict[str, Any],
    target_language: str
) -> str:
    tone = context.get("tone", "")
    audience = context.get("audience", "")

    return f"""
You are a localization expert and senior editor in {target_language}.

Input: 
You are provided with a DRAFT translation in {target_language} that needs refinement for natural flow and professional impact.

Task:
Improve the fluency and style of the draft translations.

Constraint Hierarchy (Priority 1 is most important):
1. PRESERVATION: DO NOT change placeholders ({{{{name}}}}, %s, :var, {{var}}), numbers, or brand names.
2. MEANING: Keep the meaning unchanged. The translation must remain faithful to the original intent. DO NOT sacrifice accuracy for the sake of fluency or style.
3. STYLE: Adapt the text to the specified tone and audience to sound like a native professional.

Style Specifications:
- Tone: {tone}
- Audience: {audience}

Rules:
- Avoid literal translation, but ensure the core message remains identical to the source.
- Ensure natural phrasing in {target_language}.
- If the draft is already excellent, keep it as is.

Output:
Return ONLY a raw JSON array of refined strings.

Input (Draft Translations):
{json.dumps(draft_translations, ensure_ascii=False)}
"""


def build_json_repair_prompt(raw_output: str) -> str:
    return f"""
You are a JSON repair tool.

Fix the output to be valid JSON.

Rules:
- Return ONLY valid JSON
- No explanation
- Keep content unchanged

Input:
{raw_output}
"""

def build_validation_prompt(
    source_text: str,
    translated_text: str,
    source_lang: str,
    target_lang: str
) -> str:
    return f"""
You are a translation QA system.

Task:
Validate if the translation from {source_lang} to {target_lang} is correct, natural, and preserves all technical elements.

Input:
- Source ({source_lang}): "{source_text}"
- Translation ({target_lang}): "{translated_text}"

Criteria for is_valid=true:
1. The meaning is identical to the source.
2. All placeholders ({{{{name}}}}, %s, :var, {{var}}) are exactly the same as in the source.
3. No hallucinated content.
4. Fluency is natural for the target audience.

Output:
Return ONLY a valid JSON object. DO NOT include any explanation or extra text.

JSON Schema:
{{
  "is_valid": boolean,
  "error_type": "meaning|fluency|structure|placeholder|none",
  "reason": "short explanation in English"
}}
"""



def build_fix_translation_prompt(
    source_text: str,
    bad_translation: str,
    target_language: str
) -> str:
    return f"""
You are a senior translation editor specialized in {target_language}.

Task:
Fix the following translation from the source text. 

Source (Original):
"{source_text}"

Current Bad Translation ({target_language}):
"{bad_translation}"

Examples of correct behavior:
Example 1:
Source: "Settings"
Bad Translation: "Config"
Corrected Translation: "الإعدادات"

Example 2:
Source: "From the Inside Out"
Bad Translation: "Hallucinated interpretation"
Corrected Translation: "من الداخل إلى الخارج"

Instructions:
- Fix grammatical errors, fluency issues, or placeholder corruption.
- DO NOT translate the source back to English.
- DO NOT provide any explanation, commentary, or introduction.
- Return ONLY the corrected translation in {target_language}.

Corrected Translation:
"""

def build_batch_metadata(

    context: Dict[str, Any],

    size_margin_pct: float = 0.2,

) -> Dict[str, Any]:

    return {

        "tone": context.get("tone", ""),

        "audience": context.get("audience", ""),

        "glossary": context.get("glossary", {}),

        "entities": context.get("entities", []),

        "constraints": {

            "preserve_placeholders": True,

            "size_margin_pct": size_margin_pct,

        }

    }