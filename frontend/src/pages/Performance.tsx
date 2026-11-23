import React, { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { Cpu, RefreshCw, AlertCircle, FileSpreadsheet, CheckCircle2, History } from 'lucide-react';
import { endpoints } from '../api/client';

export const Performance: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [iterations, setIterations] = useState<number>(5);
  const [benchmarkResult, setBenchmarkResult] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const runBenchmark = async () => {
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      if (file) formData.append('file', file);
      formData.append('iterations', String(iterations));

      const res = await endpoints.runBenchmark(formData);
      setBenchmarkResult(res.data);
      fetchHistory();
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Benchmark execution failed');
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await endpoints.getBenchmarkHistory();
      setHistory(res.data);
    } catch (err) {
      // Ignore background history failure
    }
  };

  useEffect(() => {
    runBenchmark();
    fetchHistory();
  }, []);

  // Format data for Recharts
  const chartData = benchmarkResult
    ? [
        {
          name: 'AES-128-CBC',
          encryptionMs: benchmarkResult.aes.encryption_time_ms,
          decryptionMs: benchmarkResult.aes.decryption_time_ms,
          throughput: benchmarkResult.aes.throughput_kbps,
        },
        {
          name: 'Blowfish-CBC',
          encryptionMs: benchmarkResult.blowfish.encryption_time_ms,
          decryptionMs: benchmarkResult.blowfish.decryption_time_ms,
          throughput: benchmarkResult.blowfish.throughput_kbps,
        },
      ]
    : [];

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Title */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Performance Comparison</h2>
          <p className="text-sm text-slate-400">
            Real high-resolution monotonic timer benchmark comparing AES-128-CBC vs Blowfish-CBC
          </p>
        </div>
        <button
          onClick={runBenchmark}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-cyan-500 hover:bg-cyan-400 text-dark-900 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>{loading ? 'Benchmarking...' : 'Rerun Benchmark'}</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Control Card */}
      <div className="p-5 rounded-2xl bg-dark-800 border border-slate-800 flex flex-wrap items-center justify-between gap-4 text-xs font-mono">
        <div className="flex items-center gap-3">
          <label className="text-slate-400">Custom Benchmark File (Optional):</label>
          <input
            type="file"
            onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
            className="text-xs text-slate-300 file:mr-2 file:py-1 file:px-3 file:rounded file:border-0 file:bg-slate-700 file:text-slate-200"
          />
        </div>

        <div className="flex items-center gap-2">
          <label className="text-slate-400">Iterations:</label>
          <select
            value={iterations}
            onChange={(e) => setIterations(Number(e.target.value))}
            className="px-2 py-1 rounded bg-slate-900 border border-slate-700 text-white"
          >
            <option value={1}>1 (Fast)</option>
            <option value={5}>5 (Averaged)</option>
            <option value={10}>10 (Accurate)</option>
          </select>
        </div>
      </div>

      {/* Benchmark Visualizations */}
      {benchmarkResult && (
        <div className="space-y-6">
          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Encryption & Decryption Time Chart */}
            <div className="p-6 rounded-2xl bg-dark-800 border border-slate-800 space-y-4">
              <h3 className="text-sm font-semibold text-white">Execution Time (ms) - Lower is Better</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                    <XAxis dataKey="name" stroke="#94A3B8" fontSize={11} />
                    <YAxis stroke="#94A3B8" fontSize={11} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', fontSize: '11px' }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                    <Bar dataKey="encryptionMs" name="Encryption Time (ms)" fill="#38BDF8" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="decryptionMs" name="Decryption Time (ms)" fill="#818CF8" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Throughput Chart */}
            <div className="p-6 rounded-2xl bg-dark-800 border border-slate-800 space-y-4">
              <h3 className="text-sm font-semibold text-white">Throughput (KB/s) - Higher is Better</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                    <XAxis dataKey="name" stroke="#94A3B8" fontSize={11} />
                    <YAxis stroke="#94A3B8" fontSize={11} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', fontSize: '11px' }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                    <Bar dataKey="throughput" name="Throughput (KB/s)" fill="#10B981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Metrics Table */}
          <div className="p-6 rounded-2xl bg-dark-800 border border-slate-800 space-y-4">
            <h3 className="text-sm font-semibold text-white">Live Benchmark Summary</h3>
            <div className="overflow-x-auto rounded-xl border border-slate-800">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-900 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3">Cipher Algorithm</th>
                    <th className="px-4 py-3">Payload Size</th>
                    <th className="px-4 py-3">Encryption Time</th>
                    <th className="px-4 py-3">Decryption Time</th>
                    <th className="px-4 py-3">Throughput (KB/s)</th>
                    <th className="px-4 py-3">Iterations</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  <tr className="hover:bg-slate-800/30">
                    <td className="px-4 py-3 font-semibold text-cyan-400">AES-128-CBC</td>
                    <td className="px-4 py-3">{benchmarkResult.aes.file_size_kb} KB</td>
                    <td className="px-4 py-3">{benchmarkResult.aes.encryption_time_ms} ms</td>
                    <td className="px-4 py-3">{benchmarkResult.aes.decryption_time_ms} ms</td>
                    <td className="px-4 py-3 font-bold text-emerald-400">{benchmarkResult.aes.throughput_kbps} KB/s</td>
                    <td className="px-4 py-3">{iterations}</td>
                  </tr>
                  <tr className="hover:bg-slate-800/30">
                    <td className="px-4 py-3 font-semibold text-indigo-400">Blowfish-CBC</td>
                    <td className="px-4 py-3">{benchmarkResult.blowfish.file_size_kb} KB</td>
                    <td className="px-4 py-3">{benchmarkResult.blowfish.encryption_time_ms} ms</td>
                    <td className="px-4 py-3">{benchmarkResult.blowfish.decryption_time_ms} ms</td>
                    <td className="px-4 py-3 font-bold text-emerald-400">{benchmarkResult.blowfish.throughput_kbps} KB/s</td>
                    <td className="px-4 py-3">{iterations}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="text-[11px] text-slate-500 font-mono">
              * Throughput calculated as File Size (KB) / Encryption Time (s). Performance varies based on host CPU hardware and native instruction acceleration.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
