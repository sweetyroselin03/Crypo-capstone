import React, { useState } from 'react';
import { Eye, ShieldCheck, Camera, AlertCircle, RefreshCw, Layers } from 'lucide-react';
import { CameraPreview } from '../components/CameraPreview';

export const EyeEnrollment: React.FC = () => {
  const [frames, setFrames] = useState<string[]>([]);
  const [isCapturing, setIsCapturing] = useState<boolean>(false);
  const [completed, setCompleted] = useState<boolean>(false);

  const handleCapture = (frameB64: string) => {
    setFrames((prev) => {
      const updated = [...prev, frameB64];
      if (updated.length >= 15) {
        setIsCapturing(false);
        setCompleted(true);
      }
      return updated;
    });
  };

  const startCapture = () => {
    setFrames([]);
    setCompleted(false);
    setIsCapturing(true);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-white tracking-tight">Eye-Region Biometric Enrollment</h2>
        <p className="text-sm text-slate-400">
          Module 2: Webcam-based periocular feature extraction and template registration
        </p>
      </div>

      <div className="p-6 rounded-2xl bg-dark-800 border border-slate-800 space-y-6">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <Camera className="w-4 h-4 text-cyan-400" />
            <span>Biometric Camera Feed</span>
          </div>
          <span className="text-xs font-mono text-cyan-400">LBP 512-dim Descriptors</span>
        </div>

        <p className="text-xs text-slate-400">
          The enrollment module captures 15 sequential frames, detects eye ROIs using OpenCV, normalizes with CLAHE, and extracts a 512-dimensional feature vector.
        </p>

        <CameraPreview
          onCaptureFrame={handleCapture}
          isCapturing={isCapturing}
          requiredFrames={15}
          capturedFramesCount={frames.length}
          promptText="Keep face centered and eyes visible"
        />

        <div className="flex items-center justify-between pt-2">
          <button
            onClick={startCapture}
            disabled={isCapturing}
            className="px-6 py-3 rounded-xl font-semibold text-xs bg-cyan-500 hover:bg-cyan-400 text-dark-900 transition-colors disabled:opacity-50"
          >
            {isCapturing ? 'Capturing 15 Frames...' : 'Start Enrollment Capture'}
          </button>

          {completed && (
            <div className="flex items-center gap-2 text-xs font-mono text-emerald-400">
              <ShieldCheck className="w-4 h-4" />
              <span>15 Frames Processed & Aggregated</span>
            </div>
          )}
        </div>
      </div>

      {/* Technical Methodology Banner */}
      <div className="p-6 rounded-2xl bg-dark-800 border border-slate-800 space-y-4">
        <h3 className="text-sm font-semibold text-white">Biometric Pipeline Details</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono text-slate-300">
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
            <span className="text-cyan-400 font-bold block">1. Localization</span>
            <p className="text-[11px] text-slate-400">Frontal face & eye ROI detection with 64x64 spatial cropping.</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
            <span className="text-indigo-400 font-bold block">2. Normalization</span>
            <p className="text-[11px] text-slate-400">Contrast Limited Adaptive Histogram Equalization (CLAHE).</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
            <span className="text-violet-400 font-bold block">3. Feature Vector</span>
            <p className="text-[11px] text-slate-400">Local Binary Patterns (LBP) with 512-dim L2 unit normalization.</p>
          </div>
        </div>
      </div>
    </div>
  );
};
