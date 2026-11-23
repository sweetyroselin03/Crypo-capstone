import time
import os
from typing import Dict, Any, List
from app.crypto.ciphers import CryptoEngine

class BenchmarkEngine:
    """Benchmark engine comparing AES-128-CBC and Blowfish-CBC on real execution."""

    @staticmethod
    def run_benchmark(data_bytes: bytes, iterations: int = 5) -> Dict[str, Any]:
        """
        Run real cryptographic benchmark measuring encryption, decryption time,
        and throughput for AES-128-CBC vs Blowfish-CBC using high-resolution monotonic timer.
        """
        file_size_bytes = len(data_bytes)
        file_size_kb = file_size_bytes / 1024.0

        results = {}

        for algo in ["AES-128-CBC", "Blowfish-CBC"]:
            enc_times: List[float] = []
            dec_times: List[float] = []

            for _ in range(iterations):
                key, iv, hmac_key = CryptoEngine.generate_keys_and_iv(algo)

                # Monotonic timer for encryption
                t0 = time.perf_counter()
                ciphertext = CryptoEngine.encrypt(data_bytes, algo, key, iv)
                t1 = time.perf_counter()
                enc_times.append((t1 - t0) * 1000.0)  # ms

                # Monotonic timer for decryption
                t2 = time.perf_counter()
                recovered = CryptoEngine.decrypt(ciphertext, algo, key, iv)
                t3 = time.perf_counter()
                dec_times.append((t3 - t2) * 1000.0)  # ms

                # Verification check
                assert recovered == data_bytes, "Round-trip benchmark data mismatch"

            avg_enc_ms = sum(enc_times) / len(enc_times)
            avg_dec_ms = sum(dec_times) / len(dec_times)

            # Throughput = KB / seconds
            enc_sec = avg_enc_ms / 1000.0
            throughput_kbps = (file_size_kb / enc_sec) if enc_sec > 0 else 0.0

            results[algo] = {
                "algorithm": algo,
                "file_size_kb": round(file_size_kb, 3),
                "encryption_time_ms": round(avg_enc_ms, 3),
                "decryption_time_ms": round(avg_dec_ms, 3),
                "throughput_kbps": round(throughput_kbps, 2),
                "iterations": iterations,
            }

        # Calculate comparative metrics
        aes_throughput = results["AES-128-CBC"]["throughput_kbps"]
        bf_throughput = results["Blowfish-CBC"]["throughput_kbps"]
        diff_pct = 0.0
        if bf_throughput > 0:
            diff_pct = round(((aes_throughput - bf_throughput) / bf_throughput) * 100, 2)

        return {
            "file_size_kb": round(file_size_kb, 3),
            "file_size_bytes": file_size_bytes,
            "aes": results["AES-128-CBC"],
            "blowfish": results["Blowfish-CBC"],
            "throughput_difference_percentage": diff_pct,
            "summary": "AES-128-CBC is hardware-accelerated on modern CPUs; Blowfish provides variable-key lightweight encryption."
        }
