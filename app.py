import os
from flask import Flask, render_template, redirect, url_for, jsonify
from database import init_db
from routes.sender import sender_bp
from routes.receiver import receiver_bp
from routes.results import results_bp

app = Flask(__name__)

# Security configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'crypto-cp-capstone-quantum-secret-2026')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True when served over HTTPS

# Initialize Database
init_db()

# Register Blueprints
app.register_blueprint(sender_bp)
app.register_blueprint(receiver_bp)
app.register_blueprint(results_bp)


@app.route('/')
def index():
    return render_template('index.html')


@app.errorhandler(403)
def forbidden(e):
    return jsonify({"error": "Forbidden: Request is unauthorized or out-of-order in session flow."}), 403


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Requested resource was not found."}), 404


@app.errorhandler(423)
def locked(e):
    return jsonify({"error": "Resource is locked due to security limits."}), 423


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": f"Internal server error: {str(e)}"}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"\n=======================================================")
    print(f" Crypto-Biometric Secure Key Exchange System")
    print(f" Server running at: http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    app.run(host='0.0.0.0', port=port, debug=True)

