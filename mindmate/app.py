"""
╔══════════════════════════════════════════════════════════════╗
║          MindMate — AI Mental Health Companion               ║
║          Flask Backend  |  app.py  (Entry Point)            ║
╚══════════════════════════════════════════════════════════════╝

HOW TO RUN:
    pip install -r requirements.txt
    python app.py

API BASE URL: http://localhost:5000
"""

from flask import Flask
from flask_cors import CORS

from config import Config
from extensions import db, bcrypt, jwt
from routes.auth_routes   import auth_bp
from routes.chat_routes   import chat_bp
from routes.mood_routes   import mood_bp
from routes.dashboard_routes import dashboard_bp


def create_app(config_class=Config):
    """
    Application Factory — creates and configures the Flask app.
    Using the factory pattern makes the app easy to test and extend.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ── Initialize extensions ───────────────────────────────────
    CORS(app, supports_credentials=True)   # Allow cross-origin requests (frontend ↔ backend)
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    # ── Register Blueprints (route groups) ──────────────────────
    app.register_blueprint(auth_bp,      url_prefix="/api/auth")
    app.register_blueprint(chat_bp,      url_prefix="/api")
    app.register_blueprint(mood_bp,      url_prefix="/api")
    app.register_blueprint(dashboard_bp, url_prefix="/api")

    # ── Create DB tables if they don't exist ────────────────────
    with app.app_context():
        db.create_all()
        print("✅ Database tables created / verified.")

    # ── Health-check route ──────────────────────────────────────
    @app.route("/")
    def index():
        return {"status": "ok", "app": "MindMate API", "version": "1.0.0"}, 200

    return app


# ── Run the app ─────────────────────────────────────────────────
if __name__ == "__main__":
    app = create_app()
    print("🚀 MindMate backend running at http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
