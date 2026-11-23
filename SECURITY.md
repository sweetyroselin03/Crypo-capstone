# Security Policy & Cryptographic Architecture

## Course CSA5106 Capstone Project
**Title:** QR Code-Based Secure Key Exchange for Encrypted File Sharing Using AES over Blowfish with Biometric Eye-Scan Authentication  
**Team:** Y. Pooja Sri, A. Sweety Roselin, Sai Theertha

---

## 1. Cryptographic Security Model

The system employs a defense-in-depth, three-factor authentication mechanism designed to prevent unauthorized access, replay attacks, man-in-the-middle tampering, and brute-force key guessing.

```
+-----------------------------------------------------------------------------------+
|                                 SENDER WORKFLOW                                   |
|                                                                                   |
|  [Excel .xlsx] ---> [CSV Bytes] ---> [AES-128-CBC / Blowfish-CBC Encryption]      |
|                                                 |                                 |
|                                     [HMAC-SHA256 Integrity Tag]                   |
|                                                 |                                 |
|  [Password + Salt] ---> [PBKDF2-HMAC-SHA256] ---> [AES-256-GCM Key Wrapping]     |
|                                                 |                                 |
|                                         [Wrapped QR Code]                         |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        RECEIVER AUTHENTICATION WORKFLOW                           |
|                                                                                   |
|  1. QR_OK:          Decode wrapped package & bind session token                   |
|  2. PASSWORD_OK:    PBKDF2 (200k iter) + AES-256-GCM key unwrap                   |
|  3. KEY_SHOWN:      Temporary 30-second masked key preview window                 |
|  4. EYE_ENROLLED:   15-frame webcam capture & 512-dim LBP periocular vector       |
|  5. EYE_VERIFIED:   EAR blink liveness (<0.17 / >0.22) + Cosine similarity (0.90) |
|  6. DATA_VIEW:      HMAC-SHA256 verified, decrypted CSV displayed & exportable   |
+-----------------------------------------------------------------------------------+
```

---

## 2. Cryptographic Specifications

### A. Symmetric Ciphers
- **AES-128-CBC:** NIST standard 128-bit key size with a 16-byte cryptographically secure random Initialization Vector (IV). Uses PKCS7 padding. Hardware-accelerated via AES-NI instructions.
- **Blowfish-CBC:** 128-bit key size with an 8-byte IV and 16-round Feistel structure. Uses PKCS7 padding.
- **Key & IV Uniqueness:** Every transfer generates freshly sampled keys and IVs using `Crypto.Random.get_random_bytes()`. Keys are never reused.

### B. Message Authentication & Integrity
- **HMAC-SHA256:** A dedicated, independent 256-bit HMAC key is generated for every transfer.
- **Canonical Serialization:** Authenticated over `f"{version}:{transfer_id}:{algorithm}:{iv_b64}:{ciphertext_b64}"`.
- **Constant-Time Verification:** Verified with `hmac.compare_digest()` to eliminate timing attack vectors before ciphertext is decrypted.

### C. Password-Based Key Wrapping
- **PBKDF2-HMAC-SHA256:** Derives a 256-bit wrapping key from the transfer password using a unique 16-byte random salt and **200,000 iterations**.
- **AES-256-GCM:** Protects the file encryption key, IV, HMAC key, and cipher metadata. Authenticated associated data (AAD) binds the payload to the unique transfer ID.

---

## 3. Strict Server-Enforced State Machine

The backend enforces state progression at the database and API level. Client-side attempts to skip steps or call `/api/transfers/<id>/decrypt` before achieving `EYE_VERIFIED` are rejected with **HTTP 403 Forbidden**.

### Lockout Defenses
1. **Password Verification:** 5 consecutive failed attempts trigger an automatic **15-minute lockout**.
2. **Biometric Verification:** 3 consecutive failed eye scans trigger an automatic **15-minute lockout**.
3. **Session Expiration:** Receiver sessions expire automatically after 60 minutes.

---

## 4. Biometric Methodology & Academic Disclaimers

### Eye-Region / Periocular Feature Extraction
- **Image Preprocessing:** Face and eye ROI localization using OpenCV Haar Cascades, resized to 64x64, normalized using Contrast Limited Adaptive Histogram Equalization (CLAHE).
- **Descriptor:** Local Binary Patterns (LBP) partitioned into 4 spatial quadrants producing a 512-dimensional normalized feature vector.
- **Liveness Detection:** Eye Aspect Ratio (EAR) sequence requiring eye closure below **0.17** and reopening above **0.22** to reject static photo presentation attacks.
- **Matching:** Cosine similarity against enrolled template with a demonstration threshold of **0.90**.

### Important Academic Disclaimer
> [!IMPORTANT]
> This application demonstrates webcam-based periocular biometric analysis for Course CSA5106. Standard commercial webcams lack near-infrared (NIR) illumination and high-magnification iris optics, and therefore do not provide medical-grade iris recognition accuracy. The 0.90 cosine similarity threshold is configured for demonstration purposes.

---

## 5. Audit Log Sanitization

Audit logs record system telemetry and authentication events. All entries are strictly sanitized:
- **Zero Plaintext Secrets:** Passwords, wrapping keys, encryption keys, IVs, HMAC secrets, and biometric templates are **never** logged or written to disk.
