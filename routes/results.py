import time
from flask import Blueprint, render_template, jsonify, request
from database import SessionLocal, Transfer, AuditLog
from crypto.aes import AESCipher
from crypto.blowfish import BlowfishCipher

results_bp = Blueprint('results', __name__)


@results_bp.route('/comparison', methods=['GET'])
def comparison_page():
    db = SessionLocal()
    try:
        transfers = db.query(Transfer).order_by(Transfer.created_at.desc()).limit(20).all()
        return render_template('comparison.html', transfers=transfers)
    finally:
        db.close()


@results_bp.route('/admin/audit-logs', methods=['GET'])
def audit_logs_page():
    db = SessionLocal()
    try:
        logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()
        return render_template('audit_logs.html', logs=logs)
    finally:
        db.close()


@results_bp.route('/api/benchmark/run', methods=['GET', 'POST'])
def run_benchmark():
    """
    Runs real-time comparative benchmark of AES-128 vs Blowfish across
    payload sizes (10 KB, 50 KB, 100 KB, 250 KB, 500 KB, 1000 KB).
    """
    sizes_kb = [10, 50, 100, 250, 500, 1000]
    results = []

    for size_kb in sizes_kb:
        payload = b"Z" * (size_kb * 1024)

        # AES Benchmark (average of 3 runs)
        aes_times = []
        for _ in range(3):
            _, _, _, t_ms = AESCipher.encrypt(payload)
            aes_times.append(t_ms)
        avg_aes_ms = sum(aes_times) / len(aes_times)
        aes_throughput = size_kb / max(avg_aes_ms / 1000.0, 1e-6)

        # Blowfish Benchmark (average of 3 runs)
        bf_times = []
        for _ in range(3):
            _, _, _, t_ms = BlowfishCipher.encrypt(payload)
            bf_times.append(t_ms)
        avg_bf_ms = sum(bf_times) / len(bf_times)
        bf_throughput = size_kb / max(avg_bf_ms / 1000.0, 1e-6)

        results.append({
            "size_kb": size_kb,
            "aes_time_ms": round(avg_aes_ms, 3),
            "aes_throughput_kb_s": round(aes_throughput, 1),
            "blowfish_time_ms": round(avg_bf_ms, 3),
            "blowfish_throughput_kb_s": round(bf_throughput, 1)
        })

    return jsonify({"success": True, "benchmark_data": results})

