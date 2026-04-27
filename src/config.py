import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TRANSLATION_LLM_URL: str = os.getenv("TRANSLATION_LLM_URL", "http://localhost:11434")
    TRANSLATION_LLM: str = os.getenv("TRANSLATION_LLM", "llama3")

    SUMMARIZE_LLM_URL: str = os.getenv("SUMMARIZE_LLM_URL", "http://localhost:11434")
    SUMMARIZE_LLM: str = os.getenv("SUMMARIZE_LLM", "llama3")

    FALLBACK_TRANSLATION_LLM: str = os.getenv("FALLBACK_TRANSLATION_LLM", "llama3.1:8b")
    FALLBACK_TRANSLATION_LLM_URL: str = os.getenv("FALLBACK_TRANSLATION_LLM_URL", "http://localhost:11434")

    VALIDATION_LLM: str = os.getenv("VALIDATION_LLM", "llama3")
    VALIDATION_LLM_URL: str = os.getenv("VALIDATION_LLM_URL", "http://localhost:11434")


    TARGET_LANGUAGE: str = os.getenv("TARGET_LANGUAGE", "Arabic")
    SOURCE_LANGUAGE: str = os.getenv("SOURCE_LANGUAGE", "English")
    INPUT_FOLDER: str = os.getenv("INPUT_FOLDER", "./content/en")
    OUTPUT_FOLDER: str = os.getenv("OUTPUT_FOLDER", "./content/ar")
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "5"))
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/translator")

    SIZE_MARGIN_PRIMARY: float = 0.4
    SIZE_MARGIN_FALLBACK: float = 1.2

    
    DEFAULT_INDUSTRY: str = "Restaurant Management Software"
    DEFAULT_TONE: str = "professional, friendly, and persuasive"
    DEFAULT_AUDIENCE: str = "restaurant owners and managers"

    GLOBAL_CONTEXT_FALLBACK: str = "Restaurant management software helps restaurant owners and managers streamline daily operations such as orders, staff coordination, inventory, and performance tracking. It improves efficiency, reduces errors, and provides data-driven insights to support better decision-making. By optimizing workflows and enhancing service speed and accuracy, it also improves customer satisfaction. Overall, it acts as a strategic tool that helps restaurants operate more smoothly, grow sustainably, and deliver better dining experiences."