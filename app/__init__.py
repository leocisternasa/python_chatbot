from flask import Flask, jsonify
from app.config import load_configurations, configure_logging
from .views import webhook_blueprint
from openai import OpenAIError


def create_app():
    app = Flask(__name__)

    # Load configurations and logging settings
    load_configurations(app)
    configure_logging()

    # Import and register blueprints, if any
    app.register_blueprint(webhook_blueprint)

    @app.errorhandler(OpenAIError)
    def handle_openai_error(error):
        app.logger.error(f"OpenAI error: {str(error)}")
        return jsonify({"status": "error", "message": "Servicio temporalmente no disponible"}), 503

    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.error(f"Unexpected error: {str(error)}")
        return jsonify({"status": "error", "message": "Error interno del servidor"}), 500

    return app
