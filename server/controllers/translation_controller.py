from flask import request, jsonify
from server.services.translation_service import TranslationService, DetectionService
from server.dtos.translation_dto import TranslateTextRequest, DetectLanguageRequest
from pydantic import ValidationError

translation_service = TranslationService()
detection_service = DetectionService()

def translate_text_controller():
    """
    Translate Text
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          id: TranslateTextRequest
          required:
            - contents
            - targetLanguageCode
          properties:
            contents:
              type: array
              items:
                type: string
              example: ["Hello world"]
            targetLanguageCode:
              type: string
              example: "fr"
            sourceLanguageCode:
              type: string
              example: "en"
            mimeType:
              type: string
              default: "text/plain"
    responses:
      200:
        description: Successful translation
        schema:
          properties:
            translations:
              type: array
              items:
                properties:
                  translatedText:
                    type: string
                  detectedLanguageCode:
                    type: string
    """
    try:
        data = request.json
        req = TranslateTextRequest(**data)
        
        translations = translation_service.translate_text(
            contents=req.contents,
            target_lang=req.targetLanguageCode,
            source_lang=req.sourceLanguageCode
        )
        
        return jsonify({"translations": translations})
    
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def detect_language_controller():
    """
    Detect Language
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          id: DetectLanguageRequest
          required:
            - content
          properties:
            content:
              type: string
              example: "Hola mundo"
    responses:
      200:
        description: Detected languages with confidence
        schema:
          properties:
            languages:
              type: array
              items:
                properties:
                  languageCode:
                    type: string
                  confidence:
                    type: number
    """
    try:
        data = request.json
        req = DetectLanguageRequest(**data)
        
        languages = detection_service.detect_language(req.content)
        
        return jsonify({"languages": languages})
    
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def translate_document_controller():
    """
    Translate Document
    ---
    responses:
      501:
        description: Not implemented yet
    """
    return jsonify({"error": "Not implemented yet"}), 501
