from pydantic import BaseModel, Field
from typing import List, Optional

class TranslateTextRequest(BaseModel):
    contents: List[str] = Field(..., description="Array of strings to translate")
    targetLanguageCode: str = Field(..., description="ISO-639-1 code (e.g. 'fr')")
    sourceLanguageCode: Optional[str] = Field(None, description="ISO-639-1 code (e.g. 'en'). Auto-detect if omitted.")
    mimeType: Optional[str] = Field("text/plain", description="'text/plain' or 'text/html'")

class DetectLanguageRequest(BaseModel):
    content: str = Field(..., description="Text to detect language for")
