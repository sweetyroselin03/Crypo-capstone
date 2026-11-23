import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { Landing } from './pages/Landing';
import { Overview } from './pages/Overview';
import { Sender } from './pages/Sender';
import { Receiver } from './pages/Receiver';
import { EyeEnrollment } from './pages/EyeEnrollment';
import { Performance } from './pages/Performance';
import { AuditLogs } from './pages/AuditLogs';
import { Settings } from './pages/Settings';
import { About } from './pages/About';
import { NotFound } from './pages/NotFound';

export const App: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-dark-900 text-slate-100 flex">
        {/* Sidebar */}
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0 lg:pl-72">
          <Navbar onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />
          <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/overview" element={<Overview />} />
              <Route path="/encrypt" element={<Sender />} />
              <Route path="/receive" element={<Receiver />} />
              <Route path="/enrollment" element={<EyeEnrollment />} />
              <Route path="/activity" element={<AuditLogs />} />
              <Route path="/performance" element={<Performance />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/about" element={<About />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
};

export default App;
