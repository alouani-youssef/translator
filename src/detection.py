from lingua import Language, LanguageDetectorBuilder
from typing import Optional

target_languages = [
                Language.ARABIC,
                Language.FRENCH,
                Language.ENGLISH,
                Language.SPANISH,
                Language.CHINESE,
                Language.HEBREW,
                Language.PERSIAN,
                Language.TURKISH
]
class LanguageDetectorService:
    def __init__(self, languages: Optional[list[Language]] = None):
        if languages:
            self.detector = LanguageDetectorBuilder.from_languages(*languages).build()
        else:        
            self.detector = LanguageDetectorBuilder.from_languages(*target_languages).build()

    def detect(self, text: str) -> Optional[str]:
        if not text or not text.strip():
            return None

        language = self.detector.detect_language_of(text)

        if language is None:
            return None
        
        return language.iso_code_639_1.name.lower()

    def detect_with_confidence(self, text: str) -> list[dict[str, any]]:
        if not text or not text.strip():
            return []

        confidence_values = self.detector.compute_language_confidence_values(text)
        
        results = []
        for cv in confidence_values[:3]:
            results.append({
                "languageCode": cv.language.iso_code_639_1.name.lower(),
                "confidence": cv.value
            })
        
        return results