import os
from flask import Flask, jsonify
from flask_cors import CORS
from app.config import Config
from app.database import db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": Config.CORS_ORIGINS}}, supports_credentials=True)

    # Initialize extensions
    db.init_app(app)

    # Ensure storage and instance directories exist
    os.makedirs(app.config["LOCAL_STORAGE_DIR"], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "..", "instance"), exist_ok=True)

    # Register blueprints
    from app.routes.health import health_bp
    from app.routes.transfers import transfers_bp
    from app.routes.receiver import receiver_bp
    from app.routes.biometrics import biometrics_bp
    from app.routes.benchmark import benchmark_bp
    from app.routes.audit import audit_bp

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(transfers_bp, url_prefix="/api")
    app.register_blueprint(receiver_bp, url_prefix="/api")
    app.register_blueprint(biometrics_bp, url_prefix="/api")
    app.register_blueprint(benchmark_bp, url_prefix="/api")
    app.register_blueprint(audit_bp, url_prefix="/api")

    # Security headers
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # Centralized error handlers
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request"}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"error": "Unauthorized"}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"error": "Forbidden: invalid workflow transition or access denied"}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return jsonify({"error": "File size exceeds permitted maximum limit"}), 413

    @app.errorhandler(500)
    def internal_server_error(e):
        return jsonify({"error": "An internal server error occurred"}), 500

    # Create tables
    with app.app_context():
        db.create_all()

    return app
