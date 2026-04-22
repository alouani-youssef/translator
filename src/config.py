import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TRANSLATION_LLM_URL: str = os.getenv("TRANSLATION_LLM_URL", "http://localhost:11434")
    TRANSLATION_LLM: str = os.getenv("TRANSLATION_LLM", "llama3")


    SUMMARIZE_LLM_URL: str = os.getenv("SUMMARIZE_LLM_URL", "http://localhost:11434")
    SUMMARIZE_LLM: str = os.getenv("SUMMARIZE_LLM", "llama3")


    TARGET_LANGUAGE: str = os.getenv("TARGET_LANGUAGE", "Arabic")
    SOURCE_LANGUAGE: str = os.getenv("SOURCE_LANGUAGE", "English")
    INPUT_FOLDER: str = os.getenv("INPUT_FOLDER", "./content/en")
    OUTPUT_FOLDER: str = os.getenv("OUTPUT_FOLDER", "./content/ar")
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "5"))
    N_CANDIDATES: int = int(os.getenv("N_CANDIDATES", "3"))
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")