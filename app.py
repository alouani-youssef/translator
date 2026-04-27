from flask import Flask
from flasgger import Swagger
from server.routes import api_bp
from src.config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec_1',
                "route": '/apispec_1.json',
                "rule_filter": lambda rule: True,  
                "model_filter": lambda tag: True,  
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
    
    app.register_blueprint(api_bp)

    @app.route('/')
    def index():
        return "Translator API is running. Visit <a href='/docs'>/docs</a> for Swagger documentation."

    return app

if __name__ == '__main__':
    app = create_app()
    debug_mode = Config.DEPLOYMENT_MODE == "development"
    app.run(host=Config.HOST, port=Config.PORT, debug=debug_mode)
