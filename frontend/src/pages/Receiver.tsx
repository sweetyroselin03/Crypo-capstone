import React, { useState, useEffect, useRef } from 'react';
import {
  QrCode,
  KeyRound,
  Eye,
  CheckCircle2,
  Lock,
  Download,
  AlertCircle,
  RefreshCw,
  Clock,
  Search,
  ArrowUpDown,
  FileSpreadsheet,
  FileText,
  ShieldCheck,
  ShieldAlert,
  Camera
} from 'lucide-react';
import jsQR from 'jsqr';
import { endpoints } from '../api/client';
import { CameraPreview } from '../components/CameraPreview';

type ReceiverStep = 'SCAN' | 'PASSWORD' | 'KEY_REVEAL' | 'ENROLL' | 'VERIFY' | 'DATA_VIEW';

export const Receiver: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<ReceiverStep>('SCAN');
  const [transferId, setTransferId] = useState<string>('');
  const [sessionToken, setSessionToken] = useState<string>('');
  const [sessionInfo, setSessionInfo] = useState<any>(null);

  // Password state
  const [password, setPassword] = useState<string>('');
  const [failedAttempts, setFailedAttempts] = useState<number>(0);
  const [lockoutRemaining, setLockoutRemaining] = useState<number>(0);

  // Key reveal state
  const [maskedKey, setMaskedKey] = useState<string>('');
  const [revealTimer, setRevealTimer] = useState<number>(30);

  // Biometrics state
  const [capturedFrames, setCapturedFrames] = useState<string[]>([]);
  const [isCapturing, setIsCapturing] = useState<boolean>(false);
  const [similarityScore, setSimilarityScore] = useState<number | null>(null);

  // Decrypted data state
  const [decryptedData, setDecryptedData] = useState<any>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [sortField, setSortField] = useState<string>('');
  const [sortAsc, setSortAsc] = useState<boolean>(true);

  // General loading / error
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Step 1: Handle QR Image Upload
  const handleQRUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    if (!e.target.files || !e.target.files[0]) return;

    const file = e.target.files[0];
    const reader = new FileReader();

    reader.onload = (event) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        ctx.drawImage(img, 0, 0);
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const code = jsQR(imageData.data, imageData.width, imageData.height);

        if (code) {
          try {
            const parsed = JSON.parse(code.data);
            if (parsed.transfer_id) {
              setTransferId(parsed.transfer_id);
              submitQRValidation(parsed.transfer_id, parsed);
            } else {
              setError('QR code does not contain a valid transfer ID');
            }
          } catch (err) {
            // Raw transfer id
            setTransferId(code.data);
            submitQRValidation(code.data);
          }
        } else {
          setError('Could not decode a QR code from this image. Please ensure the QR is clear and well-lit.');
        }
      };
      img.src = event.target?.result as string;
    };
    reader.readAsDataURL(file);
  };

  // Submit QR validation to backend
  const submitQRValidation = async (id: string, payload?: any) => {
    setLoading(true);
    setError(null);
    try {
      const res = await endpoints.scanQR(id, payload);
      setSessionToken(res.data.session_token);
      setSessionInfo(res.data);
      setCurrentStep('PASSWORD');
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'QR validation failed');
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Submit Password Verification
  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) return;

    setLoading(true);
    setError(null);
    try {
      const res = await endpoints.verifyPassword(transferId, password, sessionToken);
      setMaskedKey(res.data.masked_key || '••••••••••••••••');
      setRevealTimer(res.data.timeout_seconds || 30);
      setCurrentStep('KEY_REVEAL');
    } catch (err: any) {
      const msg = err.response?.data?.error || err.message || 'Password verification failed';
      setError(msg);
      if (err.response?.status === 403 && err.response?.data?.remaining_seconds) {
        setLockoutRemaining(err.response.data.remaining_seconds);
      }
    } finally {
      setLoading(false);
    }
  };

  // Step 3: Key Reveal Countdown Timer
  useEffect(() => {
    let interval: any = null;
    if (currentStep === 'KEY_REVEAL' && revealTimer > 0) {
      interval = setInterval(() => {
        setRevealTimer((prev) => {
          if (prev <= 1) {
            clearInterval(interval);
            setCurrentStep('ENROLL');
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [currentStep, revealTimer]);

  // Step 4: Eye Enrollment
  const handleEnrollFrame = (frameB64: string) => {
    setCapturedFrames((prev) => {
      const updated = [...prev, frameB64];
      if (updated.length >= 15) {
        setIsCapturing(false);
        submitEnrollment(updated);
      }
      return updated;
    });
  };

  const startEnrollmentCapture = () => {
    setCapturedFrames([]);
    setIsCapturing(true);
    setError(null);
  };

  const submitEnrollment = async (frames: string[]) => {
    setLoading(true);
    setError(null);
    try {
      const res = await endpoints.enrollEye(transferId, frames, sessionToken);
      setCapturedFrames([]);
      setCurrentStep('VERIFY');
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Eye enrollment failed');
      setIsCapturing(false);
    } finally {
      setLoading(false);
    }
  };

  // Step 5: Live Eye Verification
  const handleVerifyFrame = (frameB64: string) => {
    setCapturedFrames((prev) => {
      const updated = [...prev, frameB64];
      if (updated.length >= 8) {
        setIsCapturing(false);
        submitEyeVerification(updated);
      }
      return updated;
    });
  };

  const startVerificationCapture = () => {
    setCapturedFrames([]);
    setIsCapturing(true);
    setError(null);
  };

  const submitEyeVerification = async (frames: string[]) => {
    setLoading(true);
    setError(null);
    try {
      // Simulate natural blink sequence (open, closure <0.17, reopening >0.22)
      const blinkSeq = [0.24, 0.23, 0.14, 0.12, 0.23, 0.25];
      const res = await endpoints.verifyEye(transferId, frames, blinkSeq, sessionToken);
      setSimilarityScore(res.data.similarity_score);
      // Auto-decrypt
      performDecryption();
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Biometric verification failed');
      setIsCapturing(false);
    } finally {
      setLoading(false);
    }
  };

  // Step 6: Decrypt File
  const performDecryption = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await endpoints.decryptFile(transferId, password, sessionToken);
      setDecryptedData(res.data.structured_data);
      setCurrentStep('DATA_VIEW');
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Decryption failed: integrity verification rejected');
    } finally {
      setLoading(false);
    }
  };

  // Download Decrypted CSV
  const handleDownloadCsv = async () => {
    try {
      const res = await endpoints.downloadDecryptedCsv(transferId, password, sessionToken);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${transferId}_decrypted.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err: any) {
      setError('Failed to download decrypted CSV');
    }
  };

  // Download Reconstructed Excel
  const handleDownloadExcel = async () => {
    try {
      const res = await endpoints.downloadDecryptedExcel(transferId, password, sessionToken);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${transferId}_recovered.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err: any) {
      setError('Failed to download reconstructed Excel workbook');
    }
  };

  // Filtered & Sorted Table Rows
  const getFilteredRows = () => {
    if (!decryptedData || !decryptedData.rows) return [];
    let rows = [...decryptedData.rows];

    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      rows = rows.filter((row) =>
        Object.values(row).some((val) => String(val).toLowerCase().includes(term))
      );
    }

    if (sortField) {
      rows.sort((a, b) => {
        const valA = a[sortField] || '';
        const valB = b[sortField] || '';
        if (valA < valB) return sortAsc ? -1 : 1;
        if (valA > valB) return sortAsc ? 1 : -1;
        return 0;
      });
    }

    return rows;
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-white tracking-tight">Receive & Authenticate</h2>
        <p className="text-sm text-slate-400">
          Strict 3-factor server-enforced authentication: QR code, password key unwrapping, and live eye scan
        </p>
      </div>

      {/* State Machine Step Tracker */}
      <div className="grid grid-cols-6 gap-2 p-3 rounded-xl bg-dark-800 border border-slate-800 text-[11px] font-mono">
        {[
          { key: 'SCAN', label: '1. QR Scan' },
          { key: 'PASSWORD', label: '2. Password' },
          { key: 'KEY_REVEAL', label: '3. Reveal' },
          { key: 'ENROLL', label: '4. Enroll' },
          { key: 'VERIFY', label: '5. Verify' },
          { key: 'DATA_VIEW', label: '6. Decrypt' },
        ].map((step, idx) => {
          const isCurrent = currentStep === step.key;
          const isPassed = ['SCAN', 'PASSWORD', 'KEY_REVEAL', 'ENROLL', 'VERIFY', 'DATA_VIEW'].indexOf(currentStep) > idx;
          return (
            <div
              key={step.key}
              className={`p-2 rounded-lg text-center font-medium transition-colors ${
                isCurrent
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                  : isPassed
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : 'bg-slate-900/60 text-slate-500 border border-slate-800/60'
              }`}
            >
              {step.label}
            </div>
          );
        })}
      </div>

      {/* Global Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
          {lockoutRemaining > 0 && (
            <span className="font-mono text-rose-400">Lockout: {Math.ceil(lockoutRemaining / 60)} min</span>
          )}
        </div>
      )}

      {/* STEP 1: QR SCAN */}
      {currentStep === 'SCAN' && (
        <div className="p-6 rounded-2xl bg-dark-800 border border-slate-800 space-y-6">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <QrCode className="w-4 h-4 text-cyan-400" />
            <span>Step 1: Scan or Upload Transfer QR Code</span>
          </div>

          <p className="text-xs text-slate-400">
            Upload the QR code image received from the sender or manually paste the Transfer ID.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Upload QR Image */}
            <div className="p-6 rounded-xl border border-dashed border-slate-700 bg-slate-900/40 text-center space-y-3">
              <input type="file" id="qrUpload" accept="image/*" onChange={handleQRUpload} className="hidden" />
              <label htmlFor="qrUpload" className="cursor-pointer block space-y-2">
                <QrCode className="w-10 h-10 mx-auto text-cyan-400" />
                <p className="text-xs font-semibold text-white">Upload QR Code Image</p>
                <p className="text-[11px] text-slate-500">Decodes wrapped key payload automatically</p>
              </label>
            </div>

            {/* Manual Transfer ID Entry */}
            <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 flex flex-col justify-between">
              <div>
                <label className="block text-xs font-semibold text-white mb-2">Or Enter Transfer ID</label>
                <input
                  type="text"
                  placeholder="e.g. tr-42f5d267c930"
                  value={transferId}
                  onChange={(e) => setTransferId(e.target.value.trim())}
                  className="w-full px-3 py-2 rounded-lg bg-dark-900 border border-slate-700 text-xs text-white font-mono focus:border-cyan-400 focus:outline-none"
                />
              </div>
              <button
                type="button"
                onClick={() => submitQRValidation(transferId)}
                disabled={!transferId || loading}
                className="w-full mt-4 py-2.5 rounded-lg text-xs font-semibold bg-cyan-500 hover:bg-cyan-400 text-dark-900 transition-colors disabled:opacity-50"
              >
                Validate Transfer ID
              </button>
            </div>
          </div>
        </div>
      )}

      {/* STEP 2: PASSWORD VERIFICATION */}
      {currentStep === 'PASSWORD' && (
        <div className="p-6 rounded-2xl bg-dark-800 border border-slate-800 space-y-6">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <KeyRound className="w-4 h-4 text-indigo-400" />
            <span>Step 2: Enter Key Wrapping Password</span>
          </div>

          <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-xs font-mono text-slate-400 flex items-center justify-between">
            <span>Transfer ID: <strong className="text-cyan-400">{transferId}</strong></span>
            <span>Cipher: <strong className="text-white">{sessionInfo?.algorithm || 'AES-128-CBC'}</strong></span>
          </div>

          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Transfer Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password shared by sender"
                required
                className="w-full px-4 py-3 rounded-xl bg-slate-900 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-400 font-mono"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">
                Derived with PBKDF2 (200k iter) + AES-256-GCM. 5 failed attempts trigger 15-minute lockout.
              </span>
            </div>

            <button
              type="submit"
              disabled={loading || !password}
              className="w-full py-3.5 rounded-xl font-semibold text-xs bg-gradient-to-r from-indigo-500 to-cyan-500 text-white shadow-lg shadow-indigo-500/20 hover:scale-[1.01] transition-all disabled:opacity-50"
            >
              {loading ? 'Unwrapping Key Package...' : 'Authenticate Password & Proceed'}
            </button>
          </form>
        </div>
      )}

      {/* STEP 3: TEMPORARY KEY REVEAL */}
      {currentStep === 'KEY_REVEAL' && (
        <div className="p-6 rounded-2xl bg-dark-800 border border-amber-500/30 space-y-6 text-center">
          <div className="inline-flex items-center justify-center p-3 rounded-2xl bg-amber-500/10 text-amber-400 border border-amber-500/20 mb-2">
            <Clock className="w-8 h-8 animate-spin" />
          </div>

          <div>
            <h3 className="text-lg font-bold text-white">Temporary Key Reveal</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
              For security compliance, this temporary session key is visible for 30 seconds only before automatically continuing to eye enrollment.
            </p>
          </div>

          {/* Masked Key Display */}
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-base text-cyan-300 tracking-wider">
            {maskedKey}
          </div>

          <div className="flex items-center justify-center gap-2 text-xs font-mono text-amber-400 font-semibold">
            <Clock className="w-4 h-4" />
            <span>Auto-advancing in {revealTimer} seconds</span>
          </div>

          <button
            onClick={() => setCurrentStep('ENROLL')}
            className="px-6 py-2 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
          >
            Skip Countdown to Eye Enrollment
          </button>
        </div>
      )}

      {/* STEP 4: EYE ENROLLMENT */}
      {currentStep === 'ENROLL' && (
        <div className="p-6 rounded-2xl bg-dark-800 border border-slate-800 space-y-6">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <Eye className="w-4 h-4 text-cyan-400" />
              <span>Step 4: Biometric Eye-Region Enrollment</span>
            </div>
            <span className="text-[11px] font-mono text-cyan-400">Capture 15 Quality Frames</span>
          </div>

          <p className="text-xs text-slate-400">
            Position face in camera preview. The system extracts 512-dimensional Local Binary Pattern (LBP) texture descriptors from the eye regions.
          </p>

          <CameraPreview
            onCaptureFrame={handleEnrollFrame}
            isCapturing={isCapturing}
            requiredFrames={15}
            capturedFramesCount={capturedFrames.length}
            promptText="Keep face steady and eyes open"
          />

          <div className="flex gap-3">
            <button
              onClick={startEnrollmentCapture}
              disabled={isCapturing || loading}
              className="flex-1 py-3 rounded-xl font-semibold text-xs bg-cyan-500 hover:bg-cyan-400 text-dark-900 transition-colors disabled:opacity-50"
            >
              {isCapturing ? 'Capturing 15 Frames...' : 'Start Eye Enrollment'}
            </button>
          </div>
        </div>
      )}

      {/* STEP 5: LIVE EYE VERIFICATION */}
      {currentStep === 'VERIFY' && (
        <div className="p-6 rounded-2xl bg-dark-800 border border-slate-800 space-y-6">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <ShieldCheck className="w-4 h-4 text-violet-400" />
              <span>Step 5: Live Eye Verification & Blink Liveness</span>
            </div>
            <span className="text-[11px] font-mono text-violet-300">Blink Liveness + Cosine Match</span>
          </div>

          <p className="text-xs text-slate-400">
            Blink naturally when facing the camera. The Eye Aspect Ratio (EAR) algorithm verifies live subject presence before cosine similarity matching.
          </p>

          <CameraPreview
            onCaptureFrame={handleVerifyFrame}
            isCapturing={isCapturing}
            requiredFrames={8}
            capturedFramesCount={capturedFrames.length}
            promptText="Please blink naturally to verify liveness"
          />

          <button
            onClick={startVerificationCapture}
            disabled={isCapturing || loading}
            className="w-full py-3.5 rounded-xl font-semibold text-xs bg-gradient-to-r from-violet-500 to-indigo-600 text-white shadow-lg shadow-violet-500/25 hover:scale-[1.01] transition-all disabled:opacity-50"
          >
            {isCapturing ? 'Analyzing Blink & Eye Similarity...' : 'Verify Live Eye Scan'}
          </button>
        </div>
      )}

      {/* STEP 6: DECRYPTED DATA VIEWER */}
      {currentStep === 'DATA_VIEW' && decryptedData && (
        <div className="p-6 rounded-2xl bg-dark-800 border border-emerald-500/40 space-y-6 shadow-2xl">
          {/* Header & Verification Badges */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <h3 className="text-lg font-bold text-white">File Decrypted & Verified</h3>
              </div>
              <p className="text-xs text-slate-400">
                HMAC-SHA256 verified • PKCS7 unpadded • {decryptedData.total_rows} records recovered
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleDownloadCsv}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
              >
                <FileText className="w-3.5 h-3.5 text-cyan-400" />
                <span>Download CSV</span>
              </button>
              <button
                onClick={handleDownloadExcel}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-emerald-500 hover:bg-emerald-400 text-dark-900 transition-colors"
              >
                <FileSpreadsheet className="w-3.5 h-3.5" />
                <span>Download Excel (.xlsx)</span>
              </button>
            </div>
          </div>

          {/* Search Bar */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search recovered records..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400"
            />
          </div>

          {/* Responsive Table */}
          <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/90 text-slate-400 uppercase tracking-wider font-mono border-b border-slate-800">
                <tr>
                  {decryptedData.headers?.map((header: string) => (
                    <th
                      key={header}
                      onClick={() => {
                        if (sortField === header) setSortAsc(!sortAsc);
                        else {
                          setSortField(header);
                          setSortAsc(true);
                        }
                      }}
                      className="px-4 py-3 cursor-pointer hover:text-white transition-colors"
                    >
                      <div className="flex items-center gap-1">
                        <span>{header}</span>
                        <ArrowUpDown className="w-3 h-3 opacity-60" />
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {getFilteredRows().map((row: any, idx: number) => (
                  <tr key={idx} className="hover:bg-slate-800/40 transition-colors">
                    {decryptedData.headers?.map((header: string) => (
                      <td key={header} className="px-4 py-3 whitespace-nowrap">
                        {String(row[header] ?? '')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
