import os
from dotenv import load_dotenv

load_dotenv()
 
class Config:
    LLM_URL: str = os.getenv("LLM_URL", "http://localhost:11434")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3")
    TARGET_LANGUAGE: str = os.getenv("TARGET_LANGUAGE", "Arabic")
    SOURCE_LANGUAGE: str = os.getenv("SOURCE_LANGUAGE", "English")
    INPUT_FOLDER: str = os.getenv("INPUT_FOLDER", "./content/en")
    OUTPUT_FOLDER: str = os.getenv("OUTPUT_FOLDER", "./content/ar")
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "5"))