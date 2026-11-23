import React, { useRef, useState, useEffect } from 'react';
import { Camera, CameraOff, RefreshCw, AlertCircle, CheckCircle, Eye } from 'lucide-react';

interface CameraPreviewProps {
  onCaptureFrame?: (frameBase64: string) => void;
  isCapturing?: boolean;
  requiredFrames?: number;
  capturedFramesCount?: number;
  promptText?: string;
}

export const CameraPreview: React.FC<CameraPreviewProps> = ({
  onCaptureFrame,
  isCapturing = false,
  requiredFrames = 15,
  capturedFramesCount = 0,
  promptText = 'Center eyes inside target reticle'
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cameraActive, setCameraActive] = useState<boolean>(false);

  const startCamera = async () => {
    setError(null);
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera access API is not supported in this browser. Please use HTTPS or Chrome/Firefox.');
      }
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
        audio: false,
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        videoRef.current.play();
      }
      setCameraActive(true);
    } catch (err: any) {
      console.warn('Webcam access error:', err);
      setError(err.message || 'Unable to access camera. Please allow camera permissions in browser settings.');
      setCameraActive(false);
    }
  };

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      setStream(null);
    }
    setCameraActive(false);
  };

  useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
    };
  }, []);

  // Frame capture loop when isCapturing is true
  useEffect(() => {
    let intervalId: any = null;
    if (isCapturing && cameraActive && onCaptureFrame) {
      intervalId = setInterval(() => {
        captureSingleFrame();
      }, 150); // capture frame every 150ms
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isCapturing, cameraActive]);

  const captureSingleFrame = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (video.videoWidth === 0 || video.videoHeight === 0) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const frameB64 = canvas.toDataURL('image/jpeg', 0.85);
    if (onCaptureFrame) {
      onCaptureFrame(frameB64);
    }
  };

  // Mock synthetic frame generator for environments without physical webcams
  const handleSyntheticCapture = () => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    canvas.width = 320;
    canvas.height = 240;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Draw eye simulator patch
    ctx.fillStyle = '#1E293B';
    ctx.fillRect(0, 0, 320, 240);
    ctx.fillStyle = '#F8FAFC';
    ctx.beginPath();
    ctx.ellipse(160, 120, 70, 35, 0, 0, 2 * Math.PI);
    ctx.fill();
    ctx.fillStyle = '#0284C7';
    ctx.beginPath();
    ctx.arc(160, 120, 25, 0, 2 * Math.PI);
    ctx.fill();
    ctx.fillStyle = '#0F172A';
    ctx.beginPath();
    ctx.arc(160, 120, 12, 0, 2 * Math.PI);
    ctx.fill();

    const mockFrame = canvas.toDataURL('image/jpeg', 0.85);
    if (onCaptureFrame) {
      onCaptureFrame(mockFrame);
    }
  };

  return (
    <div className="relative flex flex-col items-center w-full max-w-lg mx-auto overflow-hidden rounded-2xl bg-dark-800 border border-slate-700/80 shadow-2xl">
      {/* Viewport Area */}
      <div className="relative w-full aspect-[4/3] bg-slate-950 flex items-center justify-center overflow-hidden">
        <video
          ref={videoRef}
          playsInline
          muted
          className={`w-full h-full object-cover transform scale-x-[-1] ${!cameraActive ? 'hidden' : 'block'}`}
        />

        {/* Reticle / Eye Guide Overlay */}
        {cameraActive && (
          <div className="absolute inset-0 pointer-events-none flex flex-col items-center justify-center">
            {/* Target Reticle */}
            <div className="relative w-64 h-28 border-2 border-dashed border-cyan-400/70 rounded-3xl shadow-[0_0_20px_rgba(6,182,212,0.3)] flex items-center justify-around px-4">
              {/* Left Eye Target */}
              <div className="w-20 h-16 border border-cyan-300/60 rounded-full flex items-center justify-center">
                <div className="w-4 h-4 rounded-full border border-cyan-400 animate-ping" />
              </div>
              {/* Center Crosshair */}
              <div className="w-2 h-2 rounded-full bg-cyan-400/80" />
              {/* Right Eye Target */}
              <div className="w-20 h-16 border border-cyan-300/60 rounded-full flex items-center justify-center">
                <div className="w-4 h-4 rounded-full border border-cyan-400 animate-ping" />
              </div>
            </div>
            <span className="mt-4 px-3 py-1 text-xs font-mono font-medium rounded-full bg-slate-900/80 text-cyan-300 border border-cyan-500/30 backdrop-blur-sm">
              {promptText}
            </span>
          </div>
        )}

        {/* Camera Inactive / Permission Error State */}
        {!cameraActive && (
          <div className="flex flex-col items-center text-center p-6 space-y-3">
            <CameraOff className="w-12 h-12 text-slate-500" />
            <p className="text-sm text-slate-300 font-medium">Camera access required for eye-scan authentication</p>
            {error && <p className="text-xs text-rose-400 max-w-xs">{error}</p>}
            <div className="flex gap-2">
              <button
                onClick={startCamera}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-cyan-500 hover:bg-cyan-400 text-dark-900 transition-colors"
              >
                Enable Camera
              </button>
              <button
                onClick={handleSyntheticCapture}
                className="px-3 py-2 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
                title="Capture test frame if camera is unavailable"
              >
                Simulate Frame
              </button>
            </div>
          </div>
        )}

        {/* Hidden capture canvas */}
        <canvas ref={canvasRef} className="hidden" />
      </div>

      {/* Progress / Status Bar */}
      <div className="w-full p-4 bg-dark-900/90 border-t border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Eye className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-medium text-slate-300">
            {isCapturing ? 'Analyzing Frames...' : cameraActive ? 'Camera Active' : 'Standby'}
          </span>
        </div>

        {isCapturing && (
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-cyan-400">
              {capturedFramesCount} / {requiredFrames} frames
            </span>
            <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-indigo-500 transition-all duration-200"
                style={{ width: `${Math.min(100, (capturedFramesCount / requiredFrames) * 100)}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
