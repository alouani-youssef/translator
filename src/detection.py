from lingua import Language, LanguageDetectorBuilder
from typing import Optional


class LanguageDetectorService:
    def __init__(self, languages: Optional[list[Language]] = None):
        if languages:
            self.detector = LanguageDetectorBuilder.from_languages(*languages).build()
        else:
            self.detector = LanguageDetectorBuilder.from_all_languages().build()

    def detect(self, text: str) -> Optional[str]:
        if not text or not text.strip():
            return None

        language = self.detector.detect_language_of(text)

        if language is None:
            return None
        
        return language.iso_code_639_1.name.lower()