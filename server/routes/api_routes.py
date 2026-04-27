from flask import Blueprint
from server.controllers.translation_controller import (
    translate_text_controller,
    detect_language_controller,
    translate_document_controller
)

api_bp = Blueprint('api', __name__)

api_bp.route('/translateText', methods=['POST'])(translate_text_controller)
api_bp.route('/detectLanguage', methods=['POST'])(detect_language_controller)
api_bp.route('/translateDocument', methods=['POST'])(translate_document_controller)
