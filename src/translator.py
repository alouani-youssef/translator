import ollama
from src.config import Config


def translate(text: str) -> str:
    if not text.strip():
        return text

    prompt = (
        f"You are SEO manager and you have to translate the following text to {Config.TARGET_LANGUAGE}. for a website content "
        f"Return ONLY the translated text, no explanation, no quotes:\n\n{text}"
    )

    try:
        response = ollama.chat(
            model=Config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return response["message"]["content"].strip()

    except ollama.ResponseError as e:
        print(f"  ❌ Ollama error: {e}")
        return text

    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return text