import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  FileSpreadsheet,
  ShieldCheck,
  ShieldAlert,
  Download,
  Lock,
  Activity,
  ArrowUpRight,
  RefreshCw,
  Clock,
  CheckCircle2,
  XCircle,
  Cpu
} from 'lucide-react';
import { endpoints } from '../api/client';

export const Overview: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await endpoints.getStats();
      setStats(res.data);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Security Overview</h2>
          <p className="text-sm text-slate-400">
            Real-time telemetry, transfer statistics, and authentication attempt logs
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchStats}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <Link
            to="/encrypt"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-gradient-to-r from-cyan-500 to-indigo-600 text-white shadow-md shadow-cyan-500/20 hover:scale-[1.02] transition-all"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>New Transfer</span>
          </Link>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={fetchStats} className="underline hover:text-white">Retry</button>
        </div>
      )}

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Total Transfers */}
        <div className="p-5 rounded-2xl bg-dark-800 border border-slate-800 relative overflow-hidden">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-slate-400">Total Encrypted Transfers</span>
            <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <Lock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-white font-mono">
            {stats ? stats.total_transfers : '--'}
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">AES-128 & Blowfish encrypted</span>
        </div>

        {/* Completed Decryptions */}
        <div className="p-5 rounded-2xl bg-dark-800 border border-slate-800 relative overflow-hidden">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-slate-400">Successful Decryptions</span>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-white font-mono">
            {stats ? stats.completed_decryptions : '--'}
          </div>
          <span className="text-[11px] text-emerald-400/80 mt-1 block font-medium">3-Factor Verified</span>
        </div>

        {/* Failed Attempts */}
        <div className="p-5 rounded-2xl bg-dark-800 border border-slate-800 relative overflow-hidden">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-slate-400">Blocked Attempts</span>
            <div className="p-2 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-white font-mono">
            {stats ? stats.failed_attempts : '--'}
          </div>
          <span className="text-[11px] text-rose-400/80 mt-1 block font-medium">Password & Eye-scan failures</span>
        </div>

        {/* Algorithm Split */}
        <div className="p-5 rounded-2xl bg-dark-800 border border-slate-800 relative overflow-hidden">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-slate-400">Cipher Allocation</span>
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-center gap-3 mt-1">
            <div className="text-xs font-mono">
              <span className="text-cyan-400 font-bold text-lg">
                {stats?.algorithms ? stats.algorithms['AES-128-CBC'] : 0}
              </span>
              <span className="text-slate-500 text-[10px] ml-1">AES</span>
            </div>
            <span className="text-slate-600">|</span>
            <div className="text-xs font-mono">
              <span className="text-indigo-400 font-bold text-lg">
                {stats?.algorithms ? stats.algorithms['Blowfish-CBC'] : 0}
              </span>
              <span className="text-slate-500 text-[10px] ml-1">Blowfish</span>
            </div>
          </div>
          <span className="text-[11px] text-slate-500 mt-2 block">Dual-engine support</span>
        </div>
      </div>

      {/* Grid: Recent Activity & Architecture */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Audit Activity */}
        <div className="lg:col-span-2 p-6 rounded-2xl bg-dark-800 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-semibold text-white">Recent Security Events</h3>
            </div>
            <Link to="/activity" className="text-xs text-cyan-400 hover:text-cyan-300 font-medium flex items-center gap-1">
              <span>View All Logs</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="space-y-3">
            {stats?.recent_activity && stats.recent_activity.length > 0 ? (
              stats.recent_activity.map((item: any) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 text-xs"
                >
                  <div className="flex items-center gap-3">
                    {item.success ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    ) : (
                      <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                    )}
                    <div>
                      <span className="font-mono font-semibold text-slate-200">{item.event_type}</span>
                      <p className="text-[11px] text-slate-500">
                        Transfer: {item.transfer_id || 'System'}
                      </p>
                    </div>
                  </div>
                  <div className="text-right text-[11px] font-mono text-slate-400 flex items-center gap-1">
                    <Clock className="w-3 h-3 text-slate-500" />
                    <span>{item.event_timestamp ? new Date(item.event_timestamp).toLocaleTimeString() : '--'}</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500 py-6 text-center">No recent security activity recorded yet.</p>
            )}
          </div>
        </div>

        {/* Quick Workflow Navigation */}
        <div className="p-6 rounded-2xl bg-dark-800 border border-slate-800 space-y-5">
          <h3 className="text-sm font-semibold text-white">Workflow Quick Actions</h3>

          <div className="space-y-3">
            <Link
              to="/encrypt"
              className="block p-4 rounded-xl bg-gradient-to-r from-cyan-950/40 to-slate-900 border border-cyan-500/20 hover:border-cyan-500/40 transition-colors"
            >
              <div className="flex items-center justify-between text-xs font-semibold text-cyan-300 mb-1">
                <span>Sender Flow</span>
                <ArrowUpRight className="w-4 h-4 text-cyan-400" />
              </div>
              <p className="text-[11px] text-slate-400">
                Upload Excel, convert to CSV, select cipher, and generate wrapped QR package.
              </p>
            </Link>

            <Link
              to="/receive"
              className="block p-4 rounded-xl bg-gradient-to-r from-indigo-950/40 to-slate-900 border border-indigo-500/20 hover:border-indigo-500/40 transition-colors"
            >
              <div className="flex items-center justify-between text-xs font-semibold text-indigo-300 mb-1">
                <span>Receiver Flow</span>
                <ArrowUpRight className="w-4 h-4 text-indigo-400" />
              </div>
              <p className="text-[11px] text-slate-400">
                Scan QR code, enter password, verify webcam eye-scan with blink liveness.
              </p>
            </Link>

            <Link
              to="/performance"
              className="block p-4 rounded-xl bg-gradient-to-r from-slate-900 to-slate-950 border border-slate-800 hover:border-slate-700 transition-colors"
            >
              <div className="flex items-center justify-between text-xs font-semibold text-slate-300 mb-1">
                <span>Performance Benchmark</span>
                <ArrowUpRight className="w-4 h-4 text-slate-400" />
              </div>
              <p className="text-[11px] text-slate-500">
                Compare AES-128-CBC vs Blowfish-CBC encryption time and throughput.
              </p>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
