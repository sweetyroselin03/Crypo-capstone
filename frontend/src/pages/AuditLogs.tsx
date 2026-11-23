import React, { useState, useEffect } from 'react';
import { Activity, ShieldCheck, CheckCircle2, XCircle, Clock, Filter, RefreshCw } from 'lucide-react';
import { endpoints } from '../api/client';

export const AuditLogs: React.FC = () => {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [filterType, setFilterType] = useState<string>('ALL');

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const res = await endpoints.getAuditLogs(100);
      setLogs(res.data);
    } catch (err) {
      console.warn('Failed to load audit logs', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const filteredLogs = logs.filter((l) => {
    if (filterType === 'ALL') return true;
    if (filterType === 'SUCCESS') return l.success;
    if (filterType === 'FAILED') return !l.success;
    return true;
  });

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Security Audit Logs</h2>
          <p className="text-sm text-slate-400">
            Immutable system audit trails with strict secret sanitization
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-mono">
            <ShieldCheck className="w-4 h-4" />
            <span>Zero Secrets Sanitized</span>
          </div>
          <button
            onClick={fetchLogs}
            disabled={loading}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex items-center gap-2 p-2 rounded-xl bg-dark-800 border border-slate-800 text-xs font-medium">
        <Filter className="w-4 h-4 text-slate-500 ml-2" />
        <button
          onClick={() => setFilterType('ALL')}
          className={`px-3 py-1.5 rounded-lg transition-colors ${
            filterType === 'ALL' ? 'bg-cyan-500 text-dark-900 font-bold' : 'text-slate-400 hover:text-white'
          }`}
        >
          All Events ({logs.length})
        </button>
        <button
          onClick={() => setFilterType('SUCCESS')}
          className={`px-3 py-1.5 rounded-lg transition-colors ${
            filterType === 'SUCCESS' ? 'bg-emerald-500 text-dark-900 font-bold' : 'text-slate-400 hover:text-white'
          }`}
        >
          Success Only
        </button>
        <button
          onClick={() => setFilterType('FAILED')}
          className={`px-3 py-1.5 rounded-lg transition-colors ${
            filterType === 'FAILED' ? 'bg-rose-500 text-white font-bold' : 'text-slate-400 hover:text-white'
          }`}
        >
          Failed / Blocked
        </button>
      </div>

      {/* Log Feed */}
      <div className="p-6 rounded-2xl bg-dark-800 border border-slate-800 space-y-3">
        {filteredLogs.length > 0 ? (
          filteredLogs.map((log) => (
            <div
              key={log.id}
              className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 gap-3 text-xs"
            >
              <div className="flex items-center gap-3">
                {log.success ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                ) : (
                  <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                )}
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-white">{log.event_type}</span>
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                        log.success ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                      }`}
                    >
                      {log.success ? 'PASSED' : 'BLOCKED'}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                    Transfer: {log.transfer_id || 'System Event'} • {JSON.stringify(log.metadata || {})}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400 shrink-0">
                <Clock className="w-3.5 h-3.5 text-slate-500" />
                <span>{new Date(log.event_timestamp).toLocaleString()}</span>
              </div>
            </div>
          ))
        ) : (
          <p className="text-xs text-slate-500 text-center py-8">No audit logs matching criteria.</p>
        )}
      </div>
    </div>
  );
};
