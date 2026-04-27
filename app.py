from flask import Flask
from flasgger import Swagger
from server.routes.api_routes import api_bp
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    
    # Configure Swagger
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec_1',
                "route": '/apispec_1.json',
                "rule_filter": lambda rule: True,  # all in
                "model_filter": lambda tag: True,  # all in
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/docs"
    }
    
    app.config['SWAGGER'] = {
        'title': 'Translator API',
        'uiversion': 3
    }
    
    Swagger(app, config=swagger_config)
    
    # Register Blueprints
    app.register_blueprint(api_bp)

    @app.route('/')
    def index():
        return "Translator API is running. Visit <a href='/docs'>/docs</a> for Swagger documentation."

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5005, debug=True)
