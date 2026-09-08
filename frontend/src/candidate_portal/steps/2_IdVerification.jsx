import React, { useState, useRef } from 'react';
import { Upload, Camera, CheckCircle2, ArrowRight, ArrowLeft } from 'lucide-react';

export const IdVerification = ({ onNext, onBack, sessionHook, mediaRecorder }) => {
  const [idFile, setIdFile] = useState(null);
  const [selfieData, setSelfieData] = useState(null);
  const [docType, setDocType] = useState('PAN');
  const [isUploading, setIsUploading] = useState(false);
  const videoRef = useRef(null);

  const { stream } = mediaRecorder;

  React.useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  // Capture webcam selfie frame
  const captureSelfie = () => {
    if (!videoRef.current) return;
    const canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg');
    setSelfieData(dataUrl);
  };

  const handleProceed = async () => {
    setIsUploading(true);
    try {
      if (sessionHook?.uploadDocuments && idFile && selfieData) {
        await sessionHook.uploadDocuments(idFile, selfieData);
      }
      onNext();
    } catch (err) {
      console.error('Error saving documents:', err);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="portal-card">
      <h2>Identity Verification</h2>
      <p className="subtitle">Please provide your Government ID proof and a quick webcam selfie.</p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '2rem' }}>
        {/* ID Document Upload */}
        <div style={{ background: 'rgba(255, 255, 255, 0.04)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <h4 style={{ fontSize: '0.9rem', marginBottom: '12px' }}>1. Upload Government ID</h4>
          <div style={{ marginBottom: '12px' }}>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                borderRadius: '6px',
                background: '#0f172a',
                color: '#fff',
                border: '1px solid rgba(255, 255, 255, 0.2)'
              }}
            >
              <option value="PAN">PAN Card</option>
              <option value="AADHAR">Aadhaar Card</option>
              <option value="PASSPORT">Passport</option>
              <option value="DRIVING_LICENSE">Driving License</option>
            </select>
          </div>

          <label
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '24px',
              border: '2px dashed rgba(255, 255, 255, 0.2)',
              borderRadius: '8px',
              cursor: 'pointer'
            }}
          >
            <Upload size={24} style={{ marginBottom: '8px', color: '#38bdf8' }} />
            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
              {idFile ? idFile.name : 'Click to select ID photo / PDF'}
            </span>
            <input
              type="file"
              accept="image/*,.pdf"
              style={{ display: 'none' }}
              onChange={(e) => setIdFile(e.target.files[0])}
            />
          </label>
        </div>

        {/* Webcam Selfie Capture */}
        <div style={{ background: 'rgba(255, 255, 255, 0.04)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <h4 style={{ fontSize: '0.9rem', marginBottom: '12px' }}>2. Live Webcam Selfie</h4>
          <div style={{ width: '100%', height: '140px', background: '#090d16', borderRadius: '8px', overflow: 'hidden', marginBottom: '10px' }}>
            {selfieData ? (
              <img src={selfieData} alt="Selfie" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            ) : (
              <video ref={videoRef} autoPlay playsInline muted style={{ width: '100%', height: '100%', objectFit: 'cover', transform: 'scaleX(-1)' }} />
            )}
          </div>
          <button
            type="button"
            onClick={selfieData ? () => setSelfieData(null) : captureSelfie}
            className="portal-btn-secondary"
            style={{ width: '100%', fontSize: '0.85rem', padding: '8px' }}
          >
            <Camera size={14} style={{ marginRight: '6px' }} />
            {selfieData ? 'Retake Selfie' : 'Take Snapshot'}
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <button onClick={onBack} className="portal-btn-secondary">
          <ArrowLeft size={16} style={{ marginRight: '6px' }} /> Back
        </button>
        <button
          onClick={handleProceed}
          className="portal-btn-primary"
          disabled={isUploading}
        >
          {isUploading ? 'Saving...' : 'Start Interview'} <ArrowRight size={16} style={{ marginLeft: '6px' }} />
        </button>
      </div>
    </div>
  );
};

export default IdVerification;
