import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  ShieldCheck,
  FileSpreadsheet,
  Download,
  Eye,
  Activity,
  BarChart3,
  Settings,
  Info,
  Lock,
  ChevronRight,
  ShieldAlert
} from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const navItems = [
    { name: 'Overview', path: '/overview', icon: LayoutDashboard },
    { name: 'Encrypt & Share', path: '/encrypt', icon: FileSpreadsheet, badge: 'Sender' },
    { name: 'Receive File', path: '/receive', icon: Download, badge: 'Receiver' },
    { name: 'Eye Enrollment', path: '/enrollment', icon: Eye },
    { name: 'Security Activity', path: '/activity', icon: Activity },
    { name: 'Performance', path: '/performance', icon: BarChart3 },
    { name: 'Settings', path: '/settings', icon: Settings },
    { name: 'About Project', path: '/about', icon: Info },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 flex flex-col w-72 bg-dark-800 border-r border-slate-800 transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Logo / Header */}
        <div className="flex items-center gap-3 px-6 h-20 border-b border-slate-800/80 bg-dark-900/40">
          <div className="flex items-center justify-center w-11 h-11 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 shadow-lg shadow-cyan-500/20">
            <Lock className="w-6 h-6 text-white" />
          </div>
          <div>
            <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-cyan-400 via-sky-300 to-indigo-300 bg-clip-text text-transparent">
              CryptoGuard
            </span>
            <span className="block text-[11px] font-mono text-cyan-400/80 uppercase tracking-widest">
              CSA5106 Capstone
            </span>
          </div>
        </div>

        {/* Security Status Card */}
        <div className="px-4 py-3 mx-4 my-4 rounded-lg bg-slate-900/80 border border-slate-800/80">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-slate-400">Security Engine</span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              ONLINE
            </span>
          </div>
          <p className="text-[11px] text-slate-500 font-mono">
            AES-128 / Blowfish + Eye Scan
          </p>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-4 space-y-1.5 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-gradient-to-r from-cyan-500/15 to-indigo-500/10 text-cyan-400 border border-cyan-500/25 shadow-sm shadow-cyan-500/10 font-semibold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`
                }
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-4 h-4" />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-slate-800 text-slate-300 border border-slate-700">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* Footer / Team Info */}
        <div className="p-4 border-t border-slate-800/80 bg-dark-900/60">
          <div className="text-[11px] text-slate-400">
            <p className="font-semibold text-slate-300 mb-0.5">Project Team:</p>
            <p className="text-slate-500 leading-tight">Y. Pooja Sri • A. Sweety Roselin • Sai Theertha</p>
          </div>
        </div>
      </aside>
    </>
  );
};
