import React from 'react';
import { CheckCircle2, Award, Sparkles } from 'lucide-react';

export const CompletionScreen = ({ session }) => {
  return (
    <div className="portal-card" style={{ textAlign: 'center', padding: '3.5rem 2rem' }}>
      <div
        style={{
          width: '72px',
          height: '72px',
          borderRadius: '50%',
          background: 'rgba(34, 197, 94, 0.15)',
          color: '#22c55e',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 1.5rem auto'
        }}
      >
        <CheckCircle2 size={42} />
      </div>

      <h2 style={{ fontSize: '1.75rem', marginBottom: '0.75rem', color: '#ffffff' }}>
        Interview Completed Successfully!
      </h2>

      <p style={{ color: '#94a3b8', fontSize: '1rem', maxWidth: '540px', margin: '0 auto 2rem auto', lineHeight: '1.6' }}>
        Thank you for completing your video interview. Your answers and verification documents have been securely uploaded for AI analysis. The hiring team will review your results and contact you shortly.
      </p>

      <div
        style={{
          background: 'rgba(255, 255, 255, 0.04)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '12px',
          padding: '1.25rem',
          maxWidth: '420px',
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          textAlign: 'left'
        }}
      >
        <Sparkles size={24} style={{ color: '#ef4444', flexShrink: 0 }} />
        <div style={{ fontSize: '0.85rem', color: '#cbd5e1' }}>
          <strong>Next Steps:</strong> You may safely close this browser window.
        </div>
      </div>
    </div>
  );
};

export default CompletionScreen;
