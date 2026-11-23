# QR Code-Based Secure Key Exchange for Encrypted File Sharing Using AES over Blowfish with Biometric Eye-Scan Authentication

### Course: CSA5106 - Cryptography and Network Security for Web Security
### Capstone Project Team:
- **Y. Pooja Sri**
- **A. Sweety Roselin**
- **Sai Theertha**

---

## 1. Project Overview

This capstone application implements an end-to-end, multi-factor cryptographic exchange platform that allows a sender to securely encrypt an Excel file (`.xlsx`) and share it with a receiver. The receiver must pass a strict, server-enforced three-factor authentication workflow before the original file can be decrypted and viewed:

1. **Ownership:** Scanning the password-protected QR code package containing the wrapped cryptographic material.
2. **Knowledge:** Entering the transfer password used to derive the 256-bit wrapping key via **PBKDF2-HMAC-SHA256 (200,000 iterations)** with **AES-256-GCM** authenticated unwrapping.
3. **Inherence:** Completing live webcam **biometric eye-region authentication** with **Eye Aspect Ratio (EAR) blink liveness analysis** and **512-dimensional Local Binary Pattern (LBP)** cosine similarity matching.

---

## 2. Key Features

- **Excel Workbook Ingestion:** Upload `.xlsx` files, validate format and size, and automatically convert workbook sheets to CSV bytes.
- **Dual Symmetric Ciphers:** Support for both **AES-128-CBC** (hardware-accelerated, NIST standard) and **Blowfish-CBC** (16-round Feistel cipher).
- **HMAC-SHA256 Integrity Tag:** An independent 256-bit HMAC key computes an authentication tag across the canonical payload; constant-time comparison prevents tampering and timing attacks.
- **PBKDF2 Key Wrapping:** Keys, IVs, and HMAC secrets are protected inside the QR code using PBKDF2 (200k iterations) and AES-256-GCM.
- **Strict Server-Enforced State Machine:** State order `QR_OK` &rarr; `PASSWORD_OK` &rarr; `KEY_SHOWN` &rarr; `EYE_ENROLLED` &rarr; `EYE_VERIFIED` &rarr; `DATA_VIEW`. Skipping steps returns `HTTP 403 Forbidden`.
- **Brute-Force & Lockout Defense:** 5 consecutive incorrect passwords or 3 failed eye verifications trigger an automatic **15-minute backend lockout**.
- **Temporary 30-Second Key Reveal:** Masked cipher parameters are temporarily revealed for 30 seconds before auto-advancing to eye enrollment.
- **Biometric Eye-Scan & Blink Liveness:** Webcam capture of 15 frames, OpenCV ROI cropping, CLAHE normalization, and EAR blink detection (closure < 0.17, reopening > 0.22) to block static photos.
- **Real-Time AES vs Blowfish Benchmark:** Monotonic high-resolution timer (`time.perf_counter()`) benchmarks execution time (ms) and throughput (KB/s) visualized with Recharts.
- **Decrypted Data Viewer:** In-browser responsive data table with search, column sorting, and instant download of recovered CSV or reconstructed `.xlsx` Excel files.
- **Sanitized Audit Trails:** Telemetry and security events are logged without exposing passwords, keys, IVs, or biometric templates.

---

## 3. Technology Stack

### Frontend
- **Framework:** React 18, TypeScript, Vite
- **Styling:** Tailwind CSS (Dark navy, cyan, and violet cybersecurity palette)
- **Routing:** React Router v7
- **HTTP Client:** Axios
- **Visualization:** Recharts
- **Icons:** Lucide React
- **QR Decoding:** `jsQR` & `html5-qrcode`

### Backend
- **Framework:** Python 3.13 / 3.11, Flask, Flask-CORS
- **Database:** SQLAlchemy ORM (SQLite for local development, PostgreSQL for production)
- **Cryptography:** PyCryptodome & Python `cryptography`
- **Biometrics & Image Processing:** OpenCV (`opencv-python-headless`), NumPy
- **Spreadsheet Processing:** `openpyxl`
- **WSGI Server:** Gunicorn

---

## 4. Project Directory Structure

```
Crypto - CP/
├── backend/
│   ├── app/
│   │   ├── __init__.py         # Flask app factory, CORS, security headers
│   │   ├── config.py           # Database, storage, lockout configuration
│   │   ├── models.py           # SQLAlchemy tables (transfers, sessions, audit_logs)
│   │   ├── database.py         # SQLAlchemy instance
│   │   ├── storage.py          # Storage backend abstraction (Local / S3)
│   │   ├── crypto/
│   │   │   ├── ciphers.py      # AES-128-CBC, Blowfish-CBC, HMAC-SHA256
│   │   │   ├── keywrap.py      # PBKDF2 (200k iter) + AES-256-GCM wrapping
│   │   │   ├── excel_handler.py# Excel to CSV conversion & Excel reconstruction
│   │   │   └── benchmark.py    # Monotonic high-resolution timer benchmark
│   │   ├── biometric/
│   │   │   ├── detector.py     # OpenCV Haar Cascade eye detection & LBP extractor
│   │   │   ├── liveness.py     # EAR blink detection sequence evaluator
│   │   │   └── matcher.py      # Cosine similarity matching & template encryption
│   │   ├── routes/
│   │   │   ├── health.py       # Health checks and dashboard KPI stats
│   │   │   ├── transfers.py    # Sender encryption, QR code & file download
│   │   │   ├── receiver.py     # Password unwrap, state machine & file decrypt
│   │   │   ├── biometrics.py   # Eye enrollment & live verification endpoints
│   │   │   ├── benchmark.py    # Performance benchmark execution API
│   │   │   └── audit.py        # Sanitized security audit logs
│   │   └── utils/
│   │       └── security.py     # Session validation & audit logger
│   ├── tests/                  # Automated pytest suite (12 tests)
│   ├── requirements.txt        # Python production dependencies
│   ├── wsgi.py                 # WSGI entrypoint for Gunicorn
│   ├── Procfile                # Render web service start command
│   ├── render.yaml             # Render infrastructure-as-code blueprint
│   └── .env.example            # Backend environment template
├── frontend/
│   ├── src/
│   │   ├── api/client.ts       # Axios client with dynamic base URL
│   │   ├── components/         # Sidebar, Navbar, CameraPreview, etc.
│   │   ├── pages/              # Landing, Overview, Sender, Receiver, Performance, etc.
│   │   ├── App.tsx             # Route definitions
│   │   ├── main.tsx            # Entry point
│   │   └── index.css           # Tailwind & glassmorphism styles
│   ├── package.json            # Node dependencies
│   ├── vite.config.ts          # Vite build configuration
│   ├── tailwind.config.js      # Cybersecurity theme styling
│   ├── vercel.json             # SPA routing rewrite rule
│   └── .env.example            # Frontend environment template
├── README.md                   # Full capstone documentation
├── DEPLOYMENT.md               # Exact Vercel & Render step-by-step instructions
├── SECURITY.md                 # Security architecture & academic disclaimers
└── vercel.json                 # Root monorepo Vercel configuration
```

---

## 5. Local Development Setup

### Prerequisites
- Python 3.10+ (Tested on Python 3.13)
- Node.js 18+ & npm

### Backend Setup
```bash
# 1. Navigate to backend directory
cd backend

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Run automated tests
python -m pytest tests -v

# 4. Start Flask development server
python wsgi.py
# Backend runs on http://localhost:5000
```

### Frontend Setup
```bash
# 1. Open a new terminal in the frontend directory
cd frontend

# 2. Install npm dependencies
npm install

# 3. Start Vite development server
npm run dev
# Frontend runs on http://localhost:5173
```

---

## 6. REST API Endpoint Reference

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/health` | Service health status | Public |
| `GET` | `/api/stats` | Dashboard KPI metrics and recent activity | Public |
| `POST` | `/api/transfers` | Upload Excel, encrypt, and generate wrapped QR package | Public |
| `GET` | `/api/transfers/<id>/status` | Public status of a transfer | Public |
| `GET` | `/api/transfers/<id>/qr` | Download QR code PNG image | Public |
| `GET` | `/api/transfers/<id>/download` | Download encrypted payload (`.enc`) | Public |
| `POST` | `/api/transfers/<id>/scan` | Validate QR code and initialize receiver session (`QR_OK`) | Public |
| `POST` | `/api/transfers/<id>/password` | Unwrap keys via PBKDF2 + AES-GCM (`PASSWORD_OK` / `KEY_SHOWN`) | Session Bearer |
| `POST` | `/api/transfers/<id>/key-reveal` | Check 30-second key reveal status | Session Bearer |
| `POST` | `/api/transfers/<id>/eye/enroll` | Enroll 15-frame webcam eye-region template (`EYE_ENROLLED`) | Session Bearer |
| `POST` | `/api/transfers/<id>/eye/verify` | Verify EAR blink liveness & cosine match (`EYE_VERIFIED`) | Session Bearer |
| `POST` | `/api/transfers/<id>/decrypt` | Verify HMAC-SHA256, decrypt CSV data (`DATA_VIEW`) | Session Bearer |
| `POST` | `/api/transfers/<id>/download-csv` | Download recovered CSV | Session Bearer |
| `POST` | `/api/transfers/<id>/download-excel` | Download reconstructed `.xlsx` Excel workbook | Session Bearer |
| `POST` | `/api/benchmark` | Execute live AES vs Blowfish benchmark | Public |
| `GET` | `/api/benchmark/history` | Historical benchmark results | Public |
| `GET` | `/api/audit-logs` | Sanitized immutable security activity logs | Public |

---

## 7. Automated Testing Results

The test suite covers cryptographic round-trips, tampering rejection, password lockouts, biometric similarity, blink liveness, and workflow transitions:

```bash
backend/tests/test_biometrics.py::test_cosine_similarity PASSED          [  8%]
backend/tests/test_biometrics.py::test_enrollment_template_aggregation PASSED [ 16%]
backend/tests/test_biometrics.py::test_blink_liveness_detection PASSED   [ 25%]
backend/tests/test_crypto.py::test_aes_encryption_decryption_roundtrip PASSED [ 33%]
backend/tests/test_crypto.py::test_blowfish_encryption_decryption_roundtrip PASSED [ 41%]
backend/tests/test_crypto.py::test_key_and_iv_uniqueness PASSED          [ 50%]
backend/tests/test_crypto.py::test_hmac_tampering_rejection PASSED       [ 58%]
backend/tests/test_crypto.py::test_key_wrapping_and_unwrapping PASSED    [ 66%]
backend/tests/test_crypto.py::test_wrong_password_unwrapping_rejection PASSED [ 75%]
backend/tests/test_excel.py::test_excel_to_csv_and_back PASSED           [ 83%]
backend/tests/test_state_machine.py::test_full_workflow_and_state_machine PASSED [ 91%]
backend/tests/test_state_machine.py::test_password_lockout PASSED        [100%]

============================= 12 passed in 6.05s ==============================
```

---

## 8. Deployment Overview

- **Frontend on Vercel:** Point Vercel to the `frontend/` directory, set `VITE_API_BASE_URL` to your Render URL, and build with `npm run build`.
- **Backend on Render:** Connect your repository to Render Web Services, set Root Directory to `backend/`, and deploy using `gunicorn wsgi:app`.
- **Detailed Step-by-Step Instructions:** See [DEPLOYMENT.md](file:///c:/Users/trasr/Downloads/Crypto%20-%20CP/DEPLOYMENT.md) for screenshots, variable configurations, and production checklist.

---

## 9. Academic Disclaimer

This project was built for course **CSA5106 - Cryptography and Network Security for Web Security**. Standard consumer webcams lack near-infrared (NIR) sensors and specialized optical hardware, and therefore cannot provide medical-grade iris recognition. The webcam-based periocular analysis and blink liveness detection are implemented as educational cybersecurity demonstration models.
