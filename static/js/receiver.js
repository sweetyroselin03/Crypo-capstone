document.addEventListener('DOMContentLoaded', () => {
    // Current Step Tracker
    let currentStep = 1;
    let activeStream = null;
    let enrollInterval = null;
    let verifyInterval = null;
    let countdownInterval = null;
    let secretKeyData = null;
    let isKeyMasked = true;

    // UI Elements
    const alertBanner = document.getElementById('alertBanner');

    // Stepper navigation indicators
    const stepIndicators = {
        1: document.getElementById('stepIndicator1'),
        2: document.getElementById('stepIndicator2'),
        3: document.getElementById('stepIndicator3'),
        4: document.getElementById('stepIndicator4'),
        5: document.getElementById('stepIndicator5'),
        6: document.getElementById('stepIndicator6')
    };

    // Step Panels
    const stepPanels = {
        1: document.getElementById('panelStep1'),
        2: document.getElementById('panelStep2'),
        3: document.getElementById('panelStep3'),
        4: document.getElementById('panelStep4'),
        5: document.getElementById('panelStep5'),
        6: document.getElementById('panelStep6')
    };

    // ==========================================
    // UTILITY FUNCTIONS
    // ==========================================
    function showAlert(message, type = 'danger') {
        alertBanner.className = `alert-box alert-${type}`;
        alertBanner.innerHTML = `<i class="fa-solid fa-${type === 'danger' ? 'triangle-exclamation' : 'circle-check'}"></i> <span>${message}</span>`;
        alertBanner.style.display = 'flex';
        alertBanner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function hideAlert() {
        alertBanner.style.display = 'none';
    }

    function setStep(stepNumber) {
        currentStep = stepNumber;
        hideAlert();

        // Update stepper nav bar
        for (let i = 1; i <= 6; i++) {
            stepPanels[i].style.display = (i === stepNumber) ? 'block' : 'none';
            stepIndicators[i].classList.remove('active', 'completed');

            if (i < stepNumber) {
                stepIndicators[i].classList.add('completed');
            } else if (i === stepNumber) {
                stepIndicators[i].classList.add('active');
            }
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    async function stopCamera() {
        if (activeStream) {
            activeStream.getTracks().forEach(track => track.stop());
            activeStream = null;
        }
        if (enrollInterval) clearInterval(enrollInterval);
        if (verifyInterval) clearInterval(verifyInterval);
    }

    async function startCamera(videoElement) {
        await stopCamera();
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' }
            });
            videoElement.srcObject = stream;
            activeStream = stream;
            return true;
        } catch (err) {
            showAlert(`Camera access error: ${err.message}. If camera is unavailable, you can use simulated capture.`, 'danger');
            return false;
        }
    }

    function captureVideoFrameBase64(videoElement, canvasElement) {
        if (!videoElement.videoWidth) return null;
        canvasElement.width = videoElement.videoWidth;
        canvasElement.height = videoElement.videoHeight;
        const ctx = canvasElement.getContext('2d');
        ctx.drawImage(videoElement, 0, 0, canvasElement.width, canvasElement.height);
        return canvasElement.toDataURL('image/jpeg', 0.85);
    }

    // ==========================================
    // STEP 1: QR Scan Logic
    // ==========================================
    const qrVideo = document.getElementById('qrVideo');
    const qrCanvas = document.getElementById('qrCanvas');
    const startQrCameraBtn = document.getElementById('startQrCameraBtn');
    const stopQrCameraBtn = document.getElementById('stopQrCameraBtn');
    const qrDropArea = document.getElementById('qrDropArea');
    const qrFileInput = document.getElementById('qrFileInput');
    const qrRawText = document.getElementById('qrRawText');
    const submitQrTokenBtn = document.getElementById('submitQrTokenBtn');

    // Auto-load last generated QR token from sender session if available
    const cachedToken = sessionStorage.getItem('last_qr_payload');
    if (cachedToken) {
        qrRawText.value = cachedToken;
    }

    startQrCameraBtn.addEventListener('click', async () => {
        const ok = await startCamera(qrVideo);
        if (ok) {
            startQrCameraBtn.style.display = 'none';
            stopQrCameraBtn.style.display = 'inline-flex';
            scanQrStream();
        }
    });

    stopQrCameraBtn.addEventListener('click', async () => {
        await stopCamera();
        startQrCameraBtn.style.display = 'inline-flex';
        stopQrCameraBtn.style.display = 'none';
    });

    function scanQrStream() {
        if (!activeStream) return;
        const frameB64 = captureVideoFrameBase64(qrVideo, qrCanvas);
        if (frameB64) {
            // Send frame to backend QR decoder
            fetch('/api/receiver/qr-scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ qr_image_b64: frameB64 })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    stopCamera();
                    handleQrSuccess(data);
                } else {
                    if (activeStream) setTimeout(scanQrStream, 800);
                }
            })
            .catch(() => {
                if (activeStream) setTimeout(scanQrStream, 1000);
            });
        } else {
            setTimeout(scanQrStream, 500);
        }
    }

    // QR Image File Upload
    qrFileInput.addEventListener('change', () => {
        if (qrFileInput.files.length > 0) {
            const formData = new FormData();
            formData.append('qr_image', qrFileInput.files[0]);

            fetch('/api/receiver/qr-scan', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    handleQrSuccess(data);
                } else {
                    showAlert(`QR Scan error: ${data.error}`);
                }
            })
            .catch(err => showAlert(`QR Scan failed: ${err.message}`));
        }
    });

    // Manual QR Token Submit
    submitQrTokenBtn.addEventListener('click', () => {
        const token = qrRawText.value.trim();
        if (!token) {
            showAlert("Please paste a wrapped QR payload token.");
            return;
        }

        fetch('/api/receiver/qr-scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ qr_payload: token })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                handleQrSuccess(data);
            } else {
                showAlert(`Invalid QR Token: ${data.error}`);
            }
        })
        .catch(err => showAlert(`Submission failed: ${err.message}`));
    });

    function handleQrSuccess(data) {
        document.getElementById('step2TransferId').textContent = data.transfer_id;
        showAlert(`QR verified for Transfer ID: ${data.transfer_id} (${data.cipher}-CBC)`, 'success');
        setTimeout(() => setStep(2), 700);
    }

    // ==========================================
    // STEP 2: Password Logic
    // ==========================================
    const passwordForm = document.getElementById('passwordForm');
    const receiverPassword = document.getElementById('receiverPassword');
    const toggleRecvPwdBtn = document.getElementById('toggleRecvPwdBtn');
    const attemptsLeftLabel = document.getElementById('attemptsLeftLabel');

    toggleRecvPwdBtn.addEventListener('click', () => {
        const type = receiverPassword.type === 'password' ? 'text' : 'password';
        receiverPassword.type = type;
        toggleRecvPwdBtn.innerHTML = type === 'password' ? '<i class="fa-solid fa-eye"></i>' : '<i class="fa-solid fa-eye-slash"></i>';
    });

    passwordForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const pwd = receiverPassword.value.trim();
        if (!pwd) return;

        try {
            const response = await fetch('/api/receiver/verify-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: pwd })
            });

            const data = await response.json();

            if (data.success) {
                showAlert("Password verified! Proceeding to secret key reveal.", "success");
                loadSecretKey();
            } else {
                showAlert(data.error);
                if (data.error.includes("locked")) {
                    attemptsLeftLabel.textContent = "TRANSFER LOCKED. Try again in 15 minutes.";
                    attemptsLeftLabel.style.color = "var(--accent-danger)";
                }
            }
        } catch (err) {
            showAlert(`Password verification failed: ${err.message}`);
        }
    });

    // ==========================================
    // STEP 3: Secret Key Reveal Logic
    // ==========================================
    const keyVal = document.getElementById('keyVal');
    const ivVal = document.getElementById('ivVal');
    const keyCipher = document.getElementById('keyCipher');
    const revealKeyBtn = document.getElementById('revealKeyBtn');
    const copyKeyBtn = document.getElementById('copyKeyBtn');
    const countdownTimer = document.getElementById('countdownTimer');
    const countdownBar = document.getElementById('countdownBar');
    const proceedToEnrollBtn = document.getElementById('proceedToEnrollBtn');

    async function loadSecretKey() {
        try {
            const res = await fetch('/api/receiver/secret-key');
            const data = await res.json();
            if (!data.success) {
                showAlert(`Failed to retrieve secret key: ${data.error}`);
                return;
            }

            secretKeyData = data;
            keyCipher.textContent = `${data.cipher}-CBC`;
            isKeyMasked = true;
            updateKeyDisplay();
            setStep(3);
            startKeyCountdown(data.auto_hide_seconds || 30);
        } catch (err) {
            showAlert(`Key reveal error: ${err.message}`);
        }
    }

    function updateKeyDisplay() {
        if (!secretKeyData) return;
        if (isKeyMasked) {
            keyVal.textContent = "••••••••••••••••••••••••••••••••";
            ivVal.textContent = "••••••••••••••••••••••••••••••••";
            keyVal.classList.add('masked-code');
            ivVal.classList.add('masked-code');
            revealKeyBtn.innerHTML = '<i class="fa-solid fa-eye"></i> Reveal Key';
        } else {
            keyVal.textContent = secretKeyData.key_hex;
            ivVal.textContent = secretKeyData.iv_hex;
            keyVal.classList.remove('masked-code');
            ivVal.classList.remove('masked-code');
            revealKeyBtn.innerHTML = '<i class="fa-solid fa-eye-slash"></i> Mask Key';
        }
    }

    revealKeyBtn.addEventListener('click', () => {
        isKeyMasked = !isKeyMasked;
        updateKeyDisplay();
    });

    copyKeyBtn.addEventListener('click', () => {
        if (secretKeyData) {
            navigator.clipboard.writeText(secretKeyData.key_hex);
            copyKeyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
            setTimeout(() => {
                copyKeyBtn.innerHTML = '<i class="fa-solid fa-copy"></i> Copy Key Hex';
            }, 2000);
        }
    });

    function startKeyCountdown(totalSeconds) {
        if (countdownInterval) clearInterval(countdownInterval);
        let remaining = totalSeconds;
        countdownTimer.textContent = remaining;
        countdownBar.style.width = '100%';

        countdownInterval = setInterval(() => {
            remaining--;
            countdownTimer.textContent = remaining;
            const pct = (remaining / totalSeconds) * 100;
            countdownBar.style.width = `${pct}%`;

            if (remaining <= 0) {
                clearInterval(countdownInterval);
                isKeyMasked = true;
                updateKeyDisplay();
                revealKeyBtn.disabled = true;
                countdownTimer.textContent = "0 (Auto-hidden)";
                showAlert("Secret key auto-hidden after 30 seconds for security compliance.", "info");
            }
        }, 1000);
    }

    proceedToEnrollBtn.addEventListener('click', () => {
        if (countdownInterval) clearInterval(countdownInterval);
        setStep(4);
        initEnrollmentStep();
    });

    // ==========================================
    // STEP 4: Eye Scan Enrollment (Train Mode)
    // ==========================================
    const enrollVideo = document.getElementById('enrollVideo');
    const enrollCanvas = document.getElementById('enrollCanvas');
    const enrollProgressBar = document.getElementById('enrollProgressBar');
    const enrollProgressLabel = document.getElementById('enrollProgressLabel');
    const enrollFeedback = document.getElementById('enrollFeedback');
    const startEnrollCaptureBtn = document.getElementById('startEnrollCaptureBtn');
    const reEnrollBtn = document.getElementById('reEnrollBtn');
    let enrollFramesCaptured = 0;

    async function initEnrollmentStep() {
        enrollFramesCaptured = 0;
        enrollProgressBar.style.width = '0%';
        enrollProgressBar.textContent = '0%';
        enrollProgressLabel.textContent = 'Captured 0 / 20 quality frames';
        await startCamera(enrollVideo);
    }

    startEnrollCaptureBtn.addEventListener('click', () => {
        startEnrollCaptureBtn.disabled = true;
        startEnrollCaptureBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scanning Eyes (Hold Still)...';
        enrollInterval = setInterval(sendEnrollFrame, 350);
    });

    async function sendEnrollFrame() {
        const frameB64 = captureVideoFrameBase64(enrollVideo, enrollCanvas);
        if (!frameB64) return;

        try {
            const res = await fetch('/api/receiver/eye-train-frame', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ frame: frameB64 })
            });

            const data = await res.json();

            if (data.quality_error) {
                enrollFeedback.innerHTML = `<i class="fa-solid fa-triangle-exclamation text-warning"></i> ${data.message}`;
                return;
            }

            if (data.success) {
                enrollFramesCaptured = data.captured;
                const pct = Math.round((enrollFramesCaptured / data.target) * 100);
                enrollProgressBar.style.width = `${pct}%`;
                enrollProgressBar.textContent = `${pct}%`;
                enrollProgressLabel.textContent = `Captured ${enrollFramesCaptured} / ${data.target} quality frames`;
                enrollFeedback.innerHTML = `<i class="fa-solid fa-check text-success"></i> ${data.message}`;

                if (enrollFramesCaptured >= data.target) {
                    clearInterval(enrollInterval);
                    finalizeEnrollment();
                }
            }
        } catch (err) {
            console.error(err);
        }
    }

    async function finalizeEnrollment() {
        enrollFeedback.innerHTML = '<i class="fa-solid fa-gear fa-spin"></i> Synthesizing & Encrypting Biometric Template...';
        try {
            const res = await fetch('/api/receiver/eye-enroll-complete', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                showAlert("Biometric eye template enrolled and encrypted at rest!", "success");
                stopCamera();
                setTimeout(() => {
                    setStep(5);
                    initVerificationStep();
                }, 1000);
            } else {
                showAlert(`Enrollment finalization error: ${data.error}`);
            }
        } catch (err) {
            showAlert(`Enrollment failed: ${err.message}`);
        }
    }

    reEnrollBtn.addEventListener('click', async () => {
        clearInterval(enrollInterval);
        await fetch('/api/receiver/eye-re-enroll', { method: 'POST' });
        initEnrollmentStep();
        startEnrollCaptureBtn.disabled = false;
        startEnrollCaptureBtn.innerHTML = '<i class="fa-solid fa-camera"></i> Start Eye Scan Capture';
        showAlert("Enrollment buffer reset. Ready to capture again.", "info");
    });

    // ==========================================
    // STEP 5: Eye Scan Verification Logic
    // ==========================================
    const verifyVideo = document.getElementById('verifyVideo');
    const verifyCanvas = document.getElementById('verifyCanvas');
    const livenessPrompt = document.getElementById('livenessPrompt');
    const simScoreLabel = document.getElementById('simScoreLabel');
    const simMeterBar = document.getElementById('simMeterBar');
    const eyeAttemptsLabel = document.getElementById('eyeAttemptsLabel');
    const verifyFeedback = document.getElementById('verifyFeedback');
    const startVerifyBtn = document.getElementById('startVerifyBtn');

    async function initVerificationStep() {
        await startCamera(verifyVideo);
        simScoreLabel.textContent = '0.00%';
        simMeterBar.style.width = '0%';
        verifyFeedback.innerHTML = '<i class="fa-solid fa-shield"></i> Look into camera and blink naturally to satisfy liveness check.';
    }

    startVerifyBtn.addEventListener('click', () => {
        startVerifyBtn.disabled = true;
        startVerifyBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Verifying Biometrics...';
        verifyInterval = setInterval(sendVerifyFrame, 400);
    });

    async function sendVerifyFrame() {
        const frameB64 = captureVideoFrameBase64(verifyVideo, verifyCanvas);
        if (!frameB64) return;

        try {
            const res = await fetch('/api/receiver/eye-verify-frame', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ frame: frameB64 })
            });

            const data = await res.json();

            // Handle Liveness check challenge
            if (data.liveness_pending) {
                livenessPrompt.innerHTML = `<i class="fa-solid fa-eye-slash text-warning"></i> <strong>Liveness Challenge:</strong> ${data.prompt}`;
                verifyFeedback.innerHTML = `<i class="fa-solid fa-circle-exclamation text-warning"></i> ${data.prompt}`;
                return;
            }

            // Quality feedback
            if (data.quality_error) {
                verifyFeedback.innerHTML = `<i class="fa-solid fa-triangle-exclamation text-warning"></i> ${data.message}`;
                return;
            }

            // Similarity updates
            if (data.similarity !== undefined) {
                const simPct = Math.round(data.similarity * 100);
                simScoreLabel.textContent = `${simPct}%`;
                simMeterBar.style.width = `${Math.max(0, simPct)}%`;
            }

            if (data.success && data.match) {
                clearInterval(verifyInterval);
                livenessPrompt.innerHTML = '<i class="fa-solid fa-circle-check text-success"></i> <strong>Liveness Verified & Match Confirmed!</strong>';
                verifyFeedback.innerHTML = `<i class="fa-solid fa-check text-success"></i> ${data.message}`;
                showAlert("Biometric Match Confirmed! Unlocking confidential file.", "success");
                stopCamera();
                setTimeout(() => {
                    setStep(6);
                    loadDecryptedData();
                }, 1200);
            } else {
                if (data.attempts_left !== undefined) {
                    eyeAttemptsLabel.textContent = `Verification Attempts Left: ${data.attempts_left}`;
                }
                if (data.locked) {
                    clearInterval(verifyInterval);
                    verifyFeedback.innerHTML = `<i class="fa-solid fa-lock text-danger"></i> Maximum attempts exceeded. Transfer locked for 15 minutes.`;
                    showAlert("TRANSFER LOCKED: 3 failed eye attempts exceeded. 15 minute security lockout active.", "danger");
                    startVerifyBtn.disabled = true;
                } else {
                    verifyFeedback.innerHTML = `<i class="fa-solid fa-xmark text-danger"></i> ${data.message}`;
                }
            }
        } catch (err) {
            console.error(err);
        }
    }

    // ==========================================
    // STEP 6: Decrypted Data View & Download
    // ==========================================
    const decFileName = document.getElementById('decFileName');
    const decTimeLabel = document.getElementById('decTimeLabel');
    const tableHead = document.getElementById('tableHead');
    const tableBody = document.getElementById('tableBody');
    const downloadDecryptedBtn = document.getElementById('downloadDecryptedBtn');

    async function loadDecryptedData() {
        try {
            const res = await fetch('/api/receiver/view-data');
            const data = await res.json();

            if (!data.success) {
                showAlert(`Decryption error: ${data.error}`);
                return;
            }

            decFileName.textContent = data.filename;
            decTimeLabel.textContent = `${data.dec_time_ms} ms (${data.cipher}-CBC)`;
            downloadDecryptedBtn.href = data.download_excel_url;

            // Render table header
            tableHead.innerHTML = `<tr>${data.columns.map(col => `<th>${col}</th>`).join('')}</tr>`;

            // Render table rows
            tableBody.innerHTML = data.rows.map(row => {
                return `<tr>${data.columns.map(col => `<td>${row[col] !== undefined ? row[col] : ''}</td>`).join('')}</tr>`;
            }).join('');

            showAlert(`File successfully decrypted in memory! ${data.total_rows} records loaded.`, "success");

        } catch (err) {
            showAlert(`Failed to load decrypted data: ${err.message}`);
        }
    }
});

