# Production Deployment Guide: Vercel & Render

## Course CSA5106 Capstone Project
**Title:** QR Code-Based Secure Key Exchange for Encrypted File Sharing  
**Architecture:** React SPA on Vercel + Python Flask API on Render + PostgreSQL / S3

---

## 1. Architectural Strategy & Vercel Compatibility Evaluation

### Can the Flask Backend run purely on Vercel Serverless Functions?
While simple Flask applications can run on Vercel Serverless Functions (`@vercel/python`), this capstone project requires:
1. **OpenCV & Biometric Image Processing:** `opencv-python-headless` and numpy require native binary libraries and memory footprints that exceed serverless cold-start and execution size budgets.
2. **Persistent Encrypted File Storage:** Transfers require persistent access to stored `.enc` packages across multiple receiver authentication steps. Serverless container filesystems are strictly ephemeral.
3. **Execution Limits:** High-iteration PBKDF2 (200,000 iterations) and multi-frame LBP feature extraction benefit significantly from dedicated container workers.

**Conclusion:** The recommended and stable architecture is:
- **Frontend:** React + TypeScript + Vite deployed on **Vercel** (Global CDN, instant HTTPS).
- **Backend:** Flask + Gunicorn deployed on **Render** (Python Web Service with persistent storage).

---

## 2. Deploying the Backend on Render

### Step 1: Create a Render Account
1. Visit [render.com](https://render.com) and sign in with your GitHub account (`sweetyroselin03`).

### Step 2: Create a New Web Service
1. Click **New +** > **Web Service**.
2. Connect your GitHub repository: `https://github.com/sweetyroselin03/Crypo-capstone`.
3. Configure the service settings:
   - **Name:** `crypto-capstone-api`
   - **Region:** Any (e.g. `Oregon (US West)` or `Frankfurt (EU)`)
   - **Branch:** `main`
   - **Root Directory:** `backend`
   - **Runtime:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`
   - **Plan:** Free or Starter

### Step 3: Configure Environment Variables
Under the **Environment** tab on Render, add the following key-value pairs:

| Variable | Value / Description |
|---|---|
| `FLASK_ENV` | `production` |
| `FLASK_DEBUG` | `0` |
| `SECRET_KEY` | *(Click "Generate" or enter a 32+ char random string)* |
| `CORS_ORIGINS` | `*` *(or your Vercel URL once deployed)* |
| `STORAGE_TYPE` | `local` |
| `STORAGE_DIR` | `/opt/render/project/src/storage` |
| `EYE_SIMILARITY_THRESHOLD` | `0.90` |
| `MAX_PASSWORD_ATTEMPTS` | `5` |
| `MAX_EYE_ATTEMPTS` | `3` |
| `LOCKOUT_DURATION_MINUTES` | `15` |
| `SESSION_EXPIRY_MINUTES` | `60` |

*(Optional)* If using Render PostgreSQL, create a **PostgreSQL** database on Render, copy its **Internal Database URL**, and set `DATABASE_URL`.

### Step 4: Deploy & Verify
1. Click **Create Web Service**.
2. Wait for the build and container start to complete.
3. Test your live endpoint in your browser:
   ```
   https://crypto-capstone-api.onrender.com/api/health
   ```
   Expected response:
   ```json
   {
     "status": "healthy",
     "service": "Crypto Capstone API",
     "course": "CSA5106 - Cryptography and Network Security",
     "version": "1.0.0"
   }
   ```

---

## 3. Deploying the Frontend on Vercel

### Step 1: Create a Vercel Account
1. Visit [vercel.com](https://vercel.com) and log in with GitHub.

### Step 2: Import the Repository
1. Click **Add New...** > **Project**.
2. Select your repository: `sweetyroselin03/Crypo-capstone`.
3. In the project configuration:
   - **Framework Preset:** `Vite`
   - **Root Directory:** Click **Edit** and select `frontend`.
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
   - **Install Command:** `npm install`

### Step 3: Configure Environment Variables
Expand the **Environment Variables** section and add:

| Key | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://crypto-capstone-api.onrender.com/api` *(Your Render URL)* |

### Step 4: Deploy
1. Click **Deploy**.
2. Vercel will build the React SPA and assign a public HTTPS domain:
   ```
   https://crypo-capstone.vercel.app
   ```
3. Open the public URL in any browser or mobile device. Because Vercel serves via HTTPS, camera access (`navigator.mediaDevices.getUserMedia`) is fully supported!

---

## 4. End-to-End Live Verification Checklist

Once deployed:
1. **Access Web App:** Open your public Vercel HTTPS URL.
2. **Sender Workflow:** Go to **Encrypt & Share**, upload an `.xlsx` file, select `AES-128-CBC`, set a password, and click **Encrypt**. Download the `.enc` file and the QR code image.
3. **Receiver Workflow:** Open **Receive File**, upload the QR code image, verify your password, observe the 30-second temporary key reveal, complete eye enrollment (15 frames), blink for live eye verification, and view the decrypted spreadsheet.
4. **Performance Benchmark:** Navigate to **Performance** and run the live high-resolution AES vs Blowfish benchmark to inspect the measured encryption time and throughput charts.
