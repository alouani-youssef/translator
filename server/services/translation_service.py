from src.translator import translate_batch
from src.detection import LanguageDetectorService
from src.config import Config
from typing import List, Dict, Any, Optional

class TranslationService:
    def __init__(self):
        self._detector = LanguageDetectorService()

    def translate_text(self, contents: List[str], target_lang: str, source_lang: Optional[str] = None) -> List[Dict[str, Any]]:
        # Default context for translation
        context = {
            "summary": Config.GLOBAL_CONTEXT_FALLBACK,
            "industry": Config.DEFAULT_INDUSTRY,
            "tone": Config.DEFAULT_TONE,
            "audience": Config.DEFAULT_AUDIENCE,
            "entities": [],
            "glossary": {}
        }

        # If source language is not provided, detect it from the first content
        detected_source = None
        if not source_lang and contents:
            detected_source = self._detector.detect(contents[0])
            source_lang = detected_source or Config.SOURCE_LANGUAGE

        results = translate_batch(
            texts=contents,
            context=context,
            source_language=source_lang,
            target_language=target_lang
        )

        translations = []
        for res in results:
            item = {
                "translatedText": res["translation"]
            }
            if not source_lang or detected_source:
                item["detectedLanguageCode"] = res.get("detected_input") or detected_source
            translations.append(item)
        
        return translations

class DetectionService:
    def __init__(self):
        self._detector = LanguageDetectorService()

    def detect_language(self, content: str) -> List[Dict[str, Any]]:
        return self._detector.detect_with_confidence(content)
