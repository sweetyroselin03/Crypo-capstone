import React, { useState } from 'react';
import {
  FileSpreadsheet,
  Upload,
  Lock,
  QrCode,
  Download,
  Copy,
  Check,
  RefreshCw,
  AlertCircle,
  ShieldCheck,
  Cpu,
  Layers,
  ArrowRight
} from 'lucide-react';
import { endpoints, getApiBaseUrl } from '../api/client';

export const Sender: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [algorithm, setAlgorithm] = useState<string>('AES-128-CBC');
  const [password, setPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  // Success result state
  const [result, setResult] = useState<any>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (!selected.name.toLowerCase().endsWith('.xlsx')) {
        setError('Please upload an Excel workbook (.xlsx)');
        setFile(null);
        return;
      }
      setError(null);
      setFile(selected);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const selected = e.dataTransfer.files[0];
      if (!selected.name.toLowerCase().endsWith('.xlsx')) {
        setError('Please upload an Excel workbook (.xlsx)');
        setFile(null);
        return;
      }
      setError(null);
      setFile(selected);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select an Excel file (.xlsx)');
      return;
    }
    if (password.length < 8) {
      setError('Key wrapping password must be at least 8 characters long');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('algorithm', algorithm);
    formData.append('password', password);

    try {
      const res = await endpoints.createTransfer(formData);
      setResult(res.data);
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Encryption and key wrapping failed');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const resetForm = () => {
    setFile(null);
    setPassword('');
    setConfirmPassword('');
    setResult(null);
    setError(null);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Title */}
      <div>
        <h2 className="text-2xl font-bold text-white tracking-tight">Encrypt & Share File</h2>
        <p className="text-sm text-slate-400">
          Module 1: Excel to CSV conversion, cipher encryption, HMAC integrity, and PBKDF2 key wrapping
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {!result ? (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Step 1: Upload Excel File */}
          <div className="p-6 rounded-2xl bg-dark-800 border border-slate-800 space-y-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <span className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 flex items-center justify-center text-xs font-mono">
                1
              </span>
              <span>Upload Excel File (.xlsx)</span>
            </div>

            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${
                file
                  ? 'border-cyan-500/50 bg-cyan-500/5'
                  : 'border-slate-700 hover:border-slate-600 bg-slate-900/40'
              }`}
            >
              <input
                type="file"
                id="excelFile"
                accept=".xlsx"
                onChange={handleFileChange}
                className="hidden"
              />
              <label htmlFor="excelFile" className="cursor-pointer space-y-2 block">
                <FileSpreadsheet className={`w-12 h-12 mx-auto ${file ? 'text-cyan-400' : 'text-slate-500'}`} />
                {file ? (
                  <div>
                    <p className="text-sm font-semibold text-white">{file.name}</p>
                    <p className="text-xs text-slate-400 font-mono">{(file.size / 1024).toFixed(1)} KB • Valid Excel Workbook</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm font-medium text-slate-300">Click to browse or drag and drop your .xlsx workbook</p>
                    <p className="text-xs text-slate-500">Auto-converts to CSV bytes before symmetric encryption</p>
                  </div>
                )}
              </label>
            </div>
          </div>

          {/* Step 2: Choose Algorithm */}
          <div className="p-6 rounded-2xl bg-dark-800 border border-slate-800 space-y-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <span className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 flex items-center justify-center text-xs font-mono">
                2
              </span>
              <span>Select Cryptographic Cipher</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <label
                className={`p-4 rounded-xl border cursor-pointer transition-all flex flex-col justify-between ${
                  algorithm === 'AES-128-CBC'
                    ? 'border-cyan-500 bg-cyan-500/10 text-white shadow-sm shadow-cyan-500/20'
                    : 'border-slate-800 bg-slate-900/40 text-slate-400 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="algorithm"
                      value="AES-128-CBC"
                      checked={algorithm === 'AES-128-CBC'}
                      onChange={() => setAlgorithm('AES-128-CBC')}
                      className="accent-cyan-400"
                    />
                    <span className="font-semibold text-sm text-white">AES-128-CBC (Default)</span>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300">128-bit</span>
                </div>
                <p className="text-xs text-slate-400">
                  NIST standard 16-byte block cipher with PKCS7 padding. Hardware accelerated for maximum throughput.
                </p>
              </label>

              <label
                className={`p-4 rounded-xl border cursor-pointer transition-all flex flex-col justify-between ${
                  algorithm === 'Blowfish-CBC'
                    ? 'border-indigo-500 bg-indigo-500/10 text-white shadow-sm shadow-indigo-500/20'
                    : 'border-slate-800 bg-slate-900/40 text-slate-400 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="algorithm"
                      value="Blowfish-CBC"
                      checked={algorithm === 'Blowfish-CBC'}
                      onChange={() => setAlgorithm('Blowfish-CBC')}
                      className="accent-indigo-400"
                    />
                    <span className="font-semibold text-sm text-white">Blowfish-CBC</span>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300">64-bit IV</span>
                </div>
                <p className="text-xs text-slate-400">
                  16-round Feistel cipher with 8-byte blocks and independent HMAC-SHA256 authentication tag.
                </p>
              </label>
            </div>
          </div>

          {/* Step 3: Key Wrapping Password */}
          <div className="p-6 rounded-2xl bg-dark-800 border border-slate-800 space-y-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <span className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 flex items-center justify-center text-xs font-mono">
                3
              </span>
              <span>Key Wrapping Password (PBKDF2-HMAC-SHA256)</span>
            </div>

            <p className="text-xs text-slate-400">
              This password will derive a 256-bit wrapping key with <strong>200,000 PBKDF2 iterations</strong> to wrap the file encryption key, IV, and HMAC secret via AES-256-GCM. Share this password out-of-band with the receiver.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Transfer Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Minimum 8 characters"
                  required
                  className="w-full px-3.5 py-2.5 rounded-lg bg-slate-900 border border-slate-700 text-sm text-white focus:outline-none focus:border-cyan-400 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Confirm Password</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter password"
                  required
                  className="w-full px-3.5 py-2.5 rounded-lg bg-slate-900 border border-slate-700 text-sm text-white focus:outline-none focus:border-cyan-400 font-mono"
                />
              </div>
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading || !file}
            className="w-full py-4 rounded-xl font-semibold text-sm bg-gradient-to-r from-cyan-500 via-sky-500 to-indigo-600 text-white shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 hover:scale-[1.01] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Encrypting & Generating Wrapped QR Code...</span>
              </>
            ) : (
              <>
                <Lock className="w-4 h-4" />
                <span>Encrypt File & Generate QR Package</span>
              </>
            )}
          </button>
        </form>
      ) : (
        /* Result Artifacts Display */
        <div className="space-y-6">
          <div className="p-6 rounded-2xl bg-dark-800 border border-cyan-500/40 shadow-xl space-y-6">
            <div className="flex items-center gap-3 pb-4 border-b border-slate-800">
              <div className="p-3 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Transfer Package Ready</h3>
                <p className="text-xs text-slate-400">
                  File successfully encrypted with {result.algorithm}. Provide both artifacts to receiver.
                </p>
              </div>
            </div>

            {/* Transfer ID Box */}
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-[10px] text-slate-500 font-mono uppercase tracking-wider block">Transfer ID</span>
                <span className="text-base font-bold font-mono text-cyan-400">{result.transfer_id}</span>
              </div>
              <button
                onClick={() => handleCopyId(result.transfer_id)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 flex items-center gap-1.5 transition-colors"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied' : 'Copy ID'}</span>
              </button>
            </div>

            {/* Artifact 1: QR Code */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
              <div className="flex flex-col items-center p-6 rounded-xl bg-slate-900/60 border border-slate-800">
                <span className="text-xs font-semibold text-slate-300 mb-4 flex items-center gap-1.5">
                  <QrCode className="w-4 h-4 text-cyan-400" />
                  <span>Artifact 1: Wrapped Key QR Code</span>
                </span>
                <div className="p-3 bg-white rounded-xl shadow-lg mb-4">
                  <img src={result.qr_data_url} alt="Key Wrap QR Code" className="w-52 h-52 object-contain" />
                </div>
                <a
                  href={`${getApiBaseUrl()}/transfers/${result.transfer_id}/qr`}
                  download={`${result.transfer_id}-keywrap-qr.png`}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-cyan-500 hover:bg-cyan-400 text-dark-900 transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download QR Image</span>
                </a>
              </div>

              {/* Artifact 2: Encrypted Package */}
              <div className="flex flex-col justify-between p-6 rounded-xl bg-slate-900/60 border border-slate-800 h-full">
                <div className="space-y-3">
                  <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                    <Lock className="w-4 h-4 text-indigo-400" />
                    <span>Artifact 2: Encrypted Payload (.enc)</span>
                  </span>
                  <div className="p-3 rounded-lg bg-slate-950 text-xs font-mono text-slate-400 space-y-1">
                    <p><strong className="text-slate-300">File:</strong> {result.original_filename}</p>
                    <p><strong className="text-slate-300">Cipher:</strong> {result.algorithm}</p>
                    <p><strong className="text-slate-300">Integrity:</strong> HMAC-SHA256 verified</p>
                    <p><strong className="text-slate-300">Protection:</strong> PBKDF2 (200k) + AES-256-GCM</p>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    The encrypted file bytes are stored persistently. Plaintext keys and HMAC secrets are NOT included in the file.
                  </p>
                </div>

                <div className="pt-4 space-y-2">
                  <a
                    href={`${getApiBaseUrl()}/transfers/${result.transfer_id}/download`}
                    className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 transition-colors"
                  >
                    <Download className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Download Encrypted File (.enc)</span>
                  </a>
                  <button
                    onClick={resetForm}
                    className="w-full text-center text-xs text-slate-400 hover:text-white py-2"
                  >
                    Encrypt Another File
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
