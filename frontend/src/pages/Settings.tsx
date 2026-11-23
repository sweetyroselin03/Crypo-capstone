import React, { useState } from 'react';
import { Settings as SettingsIcon, Save, RefreshCw, CheckCircle2, AlertCircle, Link } from 'lucide-react';
import { getApiBaseUrl, setApiBaseUrl, endpoints } from '../api/client';

export const Settings: React.FC = () => {
  const [apiUrl, setApiUrl] = useState<string>(getApiBaseUrl());
  const [similarityThreshold, setSimilarityThreshold] = useState<number>(0.90);
  const [status, setStatus] = useState<string | null>(null);
  const [testing, setTesting] = useState<boolean>(false);

  const handleSave = () => {
    setApiBaseUrl(apiUrl);
    setStatus('Settings saved successfully.');
    setTimeout(() => setStatus(null), 3000);
  };

  const testConnection = async () => {
    setTesting(true);
    setStatus(null);
    try {
      const res = await endpoints.health();
      if (res.data?.status === 'healthy') {
        setStatus('Backend connection verified! API status: HEALTHY');
      } else {
        setStatus('Received response but health status was not healthy.');
      }
    } catch (err: any) {
      setStatus(`Connection failed: ${err.message}`);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-white tracking-tight">System Settings</h2>
        <p className="text-sm text-slate-400">
          Configure API endpoints, biometric thresholds, and deployment parameters
        </p>
      </div>

      {status && (
        <div className="p-4 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-xs text-cyan-300 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
          <span>{status}</span>
        </div>
      )}

      <div className="p-6 rounded-2xl bg-dark-800 border border-slate-800 space-y-6">
        <h3 className="text-sm font-semibold text-white">Backend API Endpoint</h3>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            API Base URL (e.g. Render backend URL or local /api proxy)
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              placeholder="https://crypto-capstone-api.onrender.com/api"
              className="flex-1 px-3.5 py-2.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white font-mono focus:outline-none focus:border-cyan-400"
            />
            <button
              onClick={testConnection}
              disabled={testing}
              className="px-4 py-2.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 transition-colors flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${testing ? 'animate-spin' : ''}`} />
              <span>Test API</span>
            </button>
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">
            Used by Vercel frontend in production to communicate with the Render Flask API.
          </span>
        </div>

        <div className="pt-4 border-t border-slate-800 space-y-4">
          <h3 className="text-sm font-semibold text-white">Cryptographic & Biometric Parameters</h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Biometric Cosine Similarity Threshold
              </label>
              <input
                type="number"
                step="0.01"
                min="0.5"
                max="1.0"
                value={similarityThreshold}
                onChange={(e) => setSimilarityThreshold(Number(e.target.value))}
                className="w-full px-3.5 py-2 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white font-mono focus:outline-none"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">Default: 0.90 (Demo Setting)</span>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                PBKDF2 Iterations
              </label>
              <input
                type="text"
                disabled
                value="200,000 iterations"
                className="w-full px-3.5 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-400 font-mono"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">Server-enforced constant</span>
            </div>
          </div>
        </div>

        <div className="pt-4 flex justify-end">
          <button
            onClick={handleSave}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-semibold bg-cyan-500 hover:bg-cyan-400 text-dark-900 transition-colors"
          >
            <Save className="w-3.5 h-3.5" />
            <span>Save Settings</span>
          </button>
        </div>
      </div>
    </div>
  );
};
