import os
import secrets
from flask import Blueprint, request, jsonify
from app.crypto.benchmark import BenchmarkEngine
from app.models import Benchmark
from app.database import db

benchmark_bp = Blueprint("benchmark", __name__)

@benchmark_bp.route("/benchmark", methods=["POST"])
def run_benchmark():
    """
    Module 4: Real AES vs Blowfish Performance Benchmark
    Measures encryption time (ms), decryption time (ms), file size (KB), and throughput (KB/s)
    using monotonic high-resolution timer over multiple iterations.
    """
    file_bytes = None
    if "file" in request.files:
        f = request.files["file"]
        file_bytes = f.read()

    iterations = int(request.form.get("iterations", 5))

    # If no file uploaded, generate realistic 100KB test payload
    if not file_bytes or len(file_bytes) == 0:
        file_bytes = secrets.token_bytes(100 * 1024)  # 100 KB payload

    results = BenchmarkEngine.run_benchmark(file_bytes, iterations=iterations)

    # Store in database
    for algo_key in ["aes", "blowfish"]:
        item = results[algo_key]
        rec = Benchmark(
            id=secrets.token_hex(16),
            algorithm=item["algorithm"],
            file_size_kb=item["file_size_kb"],
            encryption_time_ms=item["encryption_time_ms"],
            decryption_time_ms=item["decryption_time_ms"],
            throughput_kbps=item["throughput_kbps"]
        )
        db.session.add(rec)
    db.session.commit()

    return jsonify(results), 200


@benchmark_bp.route("/benchmark/history", methods=["GET"])
def get_benchmark_history():
    """Return historical benchmark results."""
    records = Benchmark.query.order_by(Benchmark.created_at.desc()).limit(20).all()
    return jsonify([r.to_dict() for r in records]), 200
