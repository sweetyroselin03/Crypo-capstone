import React from 'react';
import { Link } from 'react-router-dom';
import {
  ShieldCheck,
  QrCode,
  Eye,
  KeyRound,
  FileSpreadsheet,
  Cpu,
  ArrowRight,
  Lock,
  Layers,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';

export const Landing: React.FC = () => {
  return (
    <div className="space-y-16 pb-16">
      {/* Hero Section */}
      <section className="relative pt-12 pb-8 text-center px-4 overflow-hidden">
        {/* Glow Effects */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[300px] bg-gradient-to-tr from-cyan-500/20 via-indigo-500/20 to-purple-500/10 blur-[100px] pointer-events-none rounded-full" />

        <div className="relative max-w-4xl mx-auto space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/80 border border-cyan-500/30 text-xs font-mono text-cyan-300">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            CSA5106 Capstone Project • Production Ready
          </div>

          <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-white leading-tight">
            Secure Key Exchange for{' '}
            <span className="bg-gradient-to-r from-cyan-400 via-sky-300 to-indigo-400 bg-clip-text text-transparent">
              Encrypted File Sharing
            </span>
          </h1>

          <p className="text-base sm:text-lg text-slate-300 max-w-2xl mx-auto leading-relaxed">
            Multi-factor cryptographic exchange using <strong>AES-128-CBC</strong> over <strong>Blowfish-CBC</strong>,
            password-derived key wrapping with <strong>PBKDF2</strong>, and strict server-enforced{' '}
            <strong>biometric eye-region authentication</strong>.
          </p>

          {/* Action CTAs */}
          <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
            <Link
              to="/encrypt"
              className="inline-flex items-center gap-2.5 px-6 py-3.5 rounded-xl font-semibold text-sm bg-gradient-to-r from-cyan-500 to-indigo-600 text-white shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 hover:scale-[1.02] transition-all"
            >
              <FileSpreadsheet className="w-4 h-4" />
              <span>Encrypt & Share File (Sender)</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            <Link
              to="/receive"
              className="inline-flex items-center gap-2.5 px-6 py-3.5 rounded-xl font-semibold text-sm bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-700 shadow-md transition-all hover:scale-[1.02]"
            >
              <QrCode className="w-4 h-4 text-cyan-400" />
              <span>Receive & Authenticate (Receiver)</span>
            </Link>
          </div>
        </div>
      </section>

      {/* 3-Factor Defense Explanation */}
      <section className="max-w-6xl mx-auto px-4">
        <div className="text-center mb-10 space-y-2">
          <h2 className="text-2xl sm:text-3xl font-bold text-white">Three-Factor Receiver Authentication</h2>
          <p className="text-sm text-slate-400 max-w-xl mx-auto">
            Strict, server-enforced state machine requiring ownership, knowledge, and biometric inherence.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Factor 1 */}
          <div className="p-6 rounded-2xl bg-dark-800/80 border border-slate-800 hover:border-cyan-500/40 transition-colors shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                <QrCode className="w-6 h-6" />
              </div>
              <span className="text-xs font-mono text-cyan-400 font-semibold px-2 py-0.5 rounded bg-cyan-500/10">
                Factor 1: Ownership
              </span>
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">QR Code Exchange</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Wrapped key package delivered via QR code. Contains AES-256-GCM protected cipher parameters,
              HMAC key, IV, and cryptographic salt. No plaintext keys or passwords.
            </p>
          </div>

          {/* Factor 2 */}
          <div className="p-6 rounded-2xl bg-dark-800/80 border border-slate-800 hover:border-indigo-500/40 transition-colors shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <KeyRound className="w-6 h-6" />
              </div>
              <span className="text-xs font-mono text-indigo-400 font-semibold px-2 py-0.5 rounded bg-indigo-500/10">
                Factor 2: Knowledge
              </span>
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">Key Wrapping Password</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Sender password derives a 256-bit wrapping key via PBKDF2-HMAC-SHA256 (200,000 iterations).
              5 incorrect attempts trigger an automatic 15-minute backend lockout.
            </p>
          </div>

          {/* Factor 3 */}
          <div className="p-6 rounded-2xl bg-dark-800/80 border border-slate-800 hover:border-violet-500/40 transition-colors shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-xl bg-violet-500/10 text-violet-400 border border-violet-500/20">
                <Eye className="w-6 h-6" />
              </div>
              <span className="text-xs font-mono text-violet-400 font-semibold px-2 py-0.5 rounded bg-violet-500/10">
                Factor 3: Inherence
              </span>
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">Biometric Eye-Scan</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Webcam-based periocular analysis with blink liveness verification (EAR check).
              512-dimensional LBP feature vector matched with cosine similarity (threshold 0.90).
            </p>
          </div>
        </div>
      </section>

      {/* Cryptographic Architecture Comparison */}
      <section className="max-w-6xl mx-auto px-4">
        <div className="p-8 rounded-3xl bg-gradient-to-b from-dark-800 to-dark-900 border border-slate-800 shadow-xl">
          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 mb-8 pb-6 border-b border-slate-800">
            <div>
              <h3 className="text-xl font-bold text-white">Dual Cipher Support & Performance Engine</h3>
              <p className="text-xs text-slate-400 mt-1">
                Comparing symmetric ciphers under identical payload conditions
              </p>
            </div>
            <Link
              to="/performance"
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 transition-colors flex items-center gap-1.5"
            >
              <Cpu className="w-4 h-4" />
              <span>Run Live Benchmark</span>
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-bold text-cyan-400">AES-128-CBC</span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                  NIST Standard
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                128-bit key, 16-byte block size, PKCS7 padding. Hardware accelerated with AES-NI instructions for superior throughput on large datasets.
              </p>
              <ul className="text-xs text-slate-300 space-y-1.5 font-mono">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Key Size: 16 bytes (128 bits)</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
                  <span>IV Size: 16 bytes</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Integrity: HMAC-SHA256 authenticated tag</span>
                </li>
              </ul>
            </div>

            <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-bold text-indigo-400">Blowfish-CBC</span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                  Schneier Cipher
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Variable-length key symmetric block cipher with 8-byte block size and 16-round Feistel structure. Excellent efficiency on memory-constrained systems.
              </p>
              <ul className="text-xs text-slate-300 space-y-1.5 font-mono">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Key Size: 16 bytes (128 bits)</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
                  <span>IV Size: 8 bytes</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Integrity: Independent HMAC-SHA256 key</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Security Disclaimer Banner */}
      <section className="max-w-6xl mx-auto px-4">
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-200/90 leading-relaxed">
            <strong className="text-amber-300 font-semibold">Academic Capstone Disclaimer:</strong> This web application demonstrates webcam-based eye-region (periocular) biometrics with blink liveness analysis for Course CSA5106. Standard webcams do not provide medical-grade iris scanning accuracy or dedicated near-infrared illumination.
          </div>
        </div>
      </section>
    </div>
  );
};
