import React from 'react';
import { Shield, BookOpen, Users, Key, Eye, Lock, Cpu, Server } from 'lucide-react';

export const About: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Title */}
      <div>
        <h2 className="text-2xl font-bold text-white tracking-tight">About the Capstone Project</h2>
        <p className="text-sm text-slate-400">
          Course CSA5106: Cryptography and Network Security for Web Security
        </p>
      </div>

      {/* Main Project Details Card */}
      <div className="p-6 rounded-2xl bg-dark-800 border border-slate-800 space-y-6">
        <div>
          <span className="text-[11px] font-mono text-cyan-400 uppercase tracking-widest block mb-1">
            Official Project Title
          </span>
          <h3 className="text-lg font-bold text-white leading-snug">
            QR Code-Based Secure Key Exchange for Encrypted File Sharing Using AES over Blowfish with Biometric Eye-Scan Authentication
          </h3>
        </div>

        {/* Project Team */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
            <Users className="w-4 h-4 text-cyan-400" />
            <span>Project Team Members</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-xs font-mono">
            <div className="p-3 rounded-lg bg-dark-900 border border-slate-800 text-center">
              <span className="text-slate-200 font-bold block">Y. Pooja Sri</span>
              <span className="text-slate-500 text-[10px]">Cryptography & Architecture</span>
            </div>
            <div className="p-3 rounded-lg bg-dark-900 border border-slate-800 text-center">
              <span className="text-cyan-300 font-bold block">A. Sweety Roselin</span>
              <span className="text-slate-500 text-[10px]">Full-Stack & Biometrics</span>
            </div>
            <div className="p-3 rounded-lg bg-dark-900 border border-slate-800 text-center">
              <span className="text-indigo-300 font-bold block">Sai Theertha</span>
              <span className="text-slate-500 text-[10px]">Security & Deployment</span>
            </div>
          </div>
        </div>

        {/* Technical Architecture Overview */}
        <div className="space-y-4">
          <h4 className="text-sm font-semibold text-white">System Architecture & Cryptographic Flow</h4>
          <div className="space-y-3 text-xs text-slate-300 font-mono">
            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 flex items-start gap-3">
              <div className="p-1.5 rounded bg-cyan-500/10 text-cyan-400 mt-0.5">
                <Lock className="w-4 h-4" />
              </div>
              <div>
                <strong className="text-white">1. Symmetric Encryption:</strong> Excel workbook (.xlsx) converted to CSV bytes and encrypted with AES-128-CBC or Blowfish-CBC using PKCS7 padding.
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 flex items-start gap-3">
              <div className="p-1.5 rounded bg-indigo-500/10 text-indigo-400 mt-0.5">
                <Shield className="w-4 h-4" />
              </div>
              <div>
                <strong className="text-white">2. Integrity Authentication:</strong> Independent 256-bit HMAC key computes HMAC-SHA256 authentication tag across version, transfer ID, IV, and ciphertext.
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 flex items-start gap-3">
              <div className="p-1.5 rounded bg-violet-500/10 text-violet-400 mt-0.5">
                <Key className="w-4 h-4" />
              </div>
              <div>
                <strong className="text-white">3. Key Wrapping (PBKDF2 + AES-GCM):</strong> PBKDF2-HMAC-SHA256 derives 256-bit key (200,000 iterations). AES-256-GCM protects secrets inside QR code with authenticated associated data.
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 flex items-start gap-3">
              <div className="p-1.5 rounded bg-emerald-500/10 text-emerald-400 mt-0.5">
                <Eye className="w-4 h-4" />
              </div>
              <div>
                <strong className="text-white">4. Biometric Eye-Scan & Blink Liveness:</strong> Webcam captures 15 frames, extracts eye regions via OpenCV, applies CLAHE, and computes 512-dim LBP texture vector with blink EAR check.
              </div>
            </div>
          </div>
        </div>

        {/* Deployment Stack */}
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
          <span className="text-xs font-semibold text-white">Target Production Deployment</span>
          <div className="flex flex-wrap gap-2 text-[11px] font-mono text-slate-300">
            <span className="px-2.5 py-1 rounded bg-slate-800 border border-slate-700">Frontend: Vercel (React + Vite + Tailwind)</span>
            <span className="px-2.5 py-1 rounded bg-slate-800 border border-slate-700">Backend: Render (Flask + Gunicorn WSGI)</span>
            <span className="px-2.5 py-1 rounded bg-slate-800 border border-slate-700">Database: PostgreSQL</span>
            <span className="px-2.5 py-1 rounded bg-slate-800 border border-slate-700">Storage: S3 / Persistent Object Storage</span>
          </div>
        </div>
      </div>
    </div>
  );
};
