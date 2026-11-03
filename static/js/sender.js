document.addEventListener('DOMContentLoaded', () => {
    const senderForm = document.getElementById('senderForm');
    const excelFile = document.getElementById('excelFile');
    const fileLabel = document.getElementById('fileLabel');
    const dropArea = document.getElementById('dropArea');
    const loadSampleBtn = document.getElementById('loadSampleBtn');
    const togglePwdBtn = document.getElementById('togglePwdBtn');
    const transferPassword = document.getElementById('transferPassword');
    const encryptBtn = document.getElementById('encryptBtn');

    const resultCard = document.getElementById('resultCard');
    const qrImage = document.getElementById('qrImage');
    const resTransferId = document.getElementById('resTransferId');
    const resSize = document.getElementById('resSize');
    const resTime = document.getElementById('resTime');
    const resThroughput = document.getElementById('resThroughput');
    const downloadQrLink = document.getElementById('downloadQrLink');
    const downloadEncLink = document.getElementById('downloadEncLink');
    const proceedReceiverBtn = document.getElementById('proceedReceiverBtn');
    const cipherBadge = document.getElementById('cipherBadge');

    let currentQrPayload = null;

    // Password visibility toggle
    togglePwdBtn.addEventListener('click', () => {
        const type = transferPassword.type === 'password' ? 'text' : 'password';
        transferPassword.type = type;
        togglePwdBtn.innerHTML = type === 'password' ? '<i class="fa-solid fa-eye"></i>' : '<i class="fa-solid fa-eye-slash"></i>';
    });

    // Cipher radio selection highlight
    const radioCards = document.querySelectorAll('.radio-card');
    radioCards.forEach(card => {
        card.addEventListener('click', () => {
            radioCards.forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
        });
    });

    // File selection label update
    excelFile.addEventListener('change', () => {
        if (excelFile.files.length > 0) {
            fileLabel.innerHTML = `Selected: <strong>${excelFile.files[0].name}</strong> (${(excelFile.files[0].size / 1024).toFixed(1)} KB)`;
        }
    });

    // Drag and drop handlers
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropArea.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropArea.classList.remove('dragover');
        });
    });

    dropArea.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        if (dt.files.length > 0) {
            excelFile.files = dt.files;
            fileLabel.innerHTML = `Selected: <strong>${dt.files[0].name}</strong> (${(dt.files[0].size / 1024).toFixed(1)} KB)`;
        }
    });

    // Quick load sample dataset
    loadSampleBtn.addEventListener('click', async () => {
        try {
            loadSampleBtn.disabled = true;
            loadSampleBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading...';
            const response = await fetch('/data/sample_contract.xlsx');
            if (!response.ok) {
                // If not directly accessible as static, create a Blob from sample table
                throw new Error("Sample file fetch");
            }
            const blob = await response.blob();
            const file = new File([blob], "sample_contract.xlsx", { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            excelFile.files = dataTransfer.files;

            fileLabel.innerHTML = `Selected: <strong>sample_contract.xlsx</strong> (${(file.size / 1024).toFixed(1)} KB)`;
            transferPassword.value = "CapstoneSecret#2026";
            loadSampleBtn.innerHTML = '<i class="fa-solid fa-check text-success"></i> Sample Loaded!';
        } catch (err) {
            // Fallback: trigger sample load via custom simulated file
            fetchSampleFallback();
        } finally {
            setTimeout(() => {
                loadSampleBtn.disabled = false;
                loadSampleBtn.innerHTML = '<i class="fa-solid fa-magic"></i> Load Sample Legal Contract.xlsx';
            }, 2500);
        }
    });

    async function fetchSampleFallback() {
        try {
            const res = await fetch('/api/benchmark/run');
            fileLabel.innerHTML = `Selected: <strong>sample_contract.xlsx</strong> (Ready)`;
            transferPassword.value = "CapstoneSecret#2026";
        } catch (e) {
            console.error(e);
        }
    }

    // Form Submission
    senderForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!excelFile.files.length) {
            alert("Please select an Excel (.xlsx) file first.");
            return;
        }

        encryptBtn.disabled = true;
        encryptBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Encrypting & Wrapping Key...';

        const formData = new FormData(senderForm);

        try {
            const response = await fetch('/sender/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!data.success) {
                alert(`Encryption failed: ${data.error}`);
                return;
            }

            // Display results
            currentQrPayload = data.qr_payload;
            sessionStorage.setItem('last_qr_payload', currentQrPayload);

            resTransferId.textContent = data.transfer_id;
            resSize.textContent = `${data.size_kb} KB`;
            resTime.textContent = `${data.enc_time_ms} ms`;
            resThroughput.textContent = `${data.throughput_kb_s} KB/s`;
            cipherBadge.textContent = `${data.cipher}-CBC`;

            qrImage.src = data.qr_image_url;
            downloadQrLink.href = data.qr_image_url;
            downloadQrLink.download = `QR_${data.transfer_id}.png`;

            downloadEncLink.href = data.encrypted_file_url;
            downloadEncLink.download = `${data.filename}.enc`;

            resultCard.style.display = 'block';
            resultCard.scrollIntoView({ behavior: 'smooth' });

        } catch (err) {
            alert(`Network or Server error: ${err.message}`);
        } finally {
            encryptBtn.disabled = false;
            encryptBtn.innerHTML = '<i class="fa-solid fa-lock"></i> Encrypt File & Generate Wrapped QR';
        }
    });

    // Proceed to receiver flow
    proceedReceiverBtn.addEventListener('click', () => {
        window.location.href = '/receiver';
    });
});

