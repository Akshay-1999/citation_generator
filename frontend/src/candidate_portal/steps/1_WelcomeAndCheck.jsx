import React, { useEffect, useRef } from 'react';
import { Camera, Mic, CheckCircle2, AlertCircle, ArrowRight, ShieldCheck } from 'lucide-react';

export const WelcomeAndCheck = ({ onNext, mediaRecorder, session }) => {
  const { stream, hasPermissions, permissionError, requestPermissions } = mediaRecorder;
  const videoRef = useRef(null);

  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  return (
    <div className="portal-card">
      <h2>Welcome to your AI Video Interview</h2>
      <p className="subtitle">
        Position: <strong>{session?.job_position || 'Software Engineer'}</strong>
      </p>

      {/* Instructions */}
      <div style={{ background: 'rgba(255, 255, 255, 0.05)', padding: '16px', borderRadius: '10px', marginBottom: '1.5rem' }}>
        <h4 style={{ fontSize: '0.9rem', marginBottom: '8px', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <ShieldCheck size={16} /> Before you begin:
        </h4>
        <ul style={{ paddingLeft: '1.2rem', fontSize: '0.85rem', color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <li>Ensure you are in a quiet, well-lit environment.</li>
          <li>You will answer <strong>5 questions</strong> one-by-one with up to 2 minutes per answer.</li>
          <li>Your camera and microphone will record your answers for AI evaluation.</li>
        </ul>
      </div>

      {/* Hardware Preview */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h4 style={{ fontSize: '0.9rem', marginBottom: '10px' }}>Camera & Microphone Check</h4>
        <div className="video-preview-box">
          {stream ? (
            <video ref={videoRef} autoPlay playsInline muted />
          ) : (
            <div style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8' }}>
              <Camera size={40} style={{ marginBottom: '10px', opacity: 0.5 }} />
              <p>Camera preview will appear here</p>
            </div>
          )}
        </div>
      </div>

      {/* Permission Buttons & Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        {!hasPermissions ? (
          <button onClick={requestPermissions} className="portal-btn-primary">
            <Camera size={16} /> Enable Camera & Microphone
          </button>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#4ade80', fontSize: '0.88rem', fontWeight: 600 }}>
            <CheckCircle2 size={18} /> Devices Ready
          </div>
        )}

        {permissionError && (
          <div style={{ color: '#f87171', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <AlertCircle size={14} /> {permissionError}
          </div>
        )}

        <button
          onClick={onNext}
          disabled={!hasPermissions}
          className="portal-btn-primary"
          style={{ opacity: hasPermissions ? 1 : 0.4, cursor: hasPermissions ? 'pointer' : 'not-allowed' }}
        >
          Proceed to Verification <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
};

export default WelcomeAndCheck;
