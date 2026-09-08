import React, { useState } from 'react';
import { X, Award, CheckCircle2, AlertTriangle, Video, FileText, ChevronRight, BarChart3, User, Calendar, ExternalLink } from 'lucide-react';
import InterviewStatusBadge from './InterviewStatusBadge';

export const InterviewReportModal = ({ isOpen, onClose, candidate, reportData }) => {
  const [activeTab, setActiveTab] = useState('summary'); // 'summary' | 'turns' | 'identity'
  const [selectedTurn, setSelectedTurn] = useState(1);

  if (!isOpen) return null;

  // Fallback demo data if report is still loading or mock
  const report = reportData || {
    overall_score: candidate?.interview_score || 85,
    recommendation: 'Strong Hire',
    communication_score: 88,
    technical_score: 82,
    resume_consistency_score: 90,
    summary: 'Candidate demonstrated deep hands-on expertise in backend architecture, API design, and distributed systems. Spoke clearly with structured responses matching claims on resume.',
    strengths: [
      'Strong problem-solving methodology and technical depth in PostgreSQL optimization.',
      'Clear, articulate communication with concise answers.',
      'Accurate alignment between declared project experience and live technical explanations.'
    ],
    weaknesses: [
      'Could elaborate more on edge-case handling in asynchronous job pipelines.',
      'Slight hesitation on concurrency lock strategies.'
    ],
    turns: [
      {
        turn_number: 1,
        question_text: 'Can you walk us through your most challenging architecture project and your specific contributions?',
        transcript: 'In my last role, I led the migration of our monolith data service to a decoupled microservice architecture using FastAPI and PostgreSQL...',
        duration: '1m 45s',
        score: 88,
        feedback: 'Structured answer following the STAR method. Good technical clarity.'
      },
      {
        turn_number: 2,
        question_text: 'How do you handle heavy asynchronous background video processing and transcoding at scale?',
        transcript: 'We decoupled the ingestion API from the transcoding worker using Celery and Redis message queues...',
        duration: '2m 10s',
        score: 85,
        feedback: 'Clear architectural understanding of queue backpressure and job retries.'
      }
    ]
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '900px', width: '90%', maxHeight: '90vh' }}>
        {/* Header */}
        <div className="modal-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h3>AI Video Interview Assessment</h3>
              <InterviewStatusBadge status={candidate?.interview_status || 'COMPLETED'} />
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Candidate: <strong>{candidate?.name || 'Candidate'}</strong> | Role: {candidate?.position || 'Software Engineer'}
            </p>
          </div>
          <button onClick={onClose} className="icon-btn close-btn" title="Close" type="button">
            <X size={18} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--glass-border)', padding: '0 1.5rem', background: '#f8fafc', gap: '8px' }}>
          <button
            onClick={() => setActiveTab('summary')}
            style={{
              padding: '10px 16px',
              border: 'none',
              background: 'none',
              borderBottom: activeTab === 'summary' ? '2px solid var(--brand-primary)' : '2px solid transparent',
              color: activeTab === 'summary' ? 'var(--brand-primary)' : 'var(--text-secondary)',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Overview & Scores
          </button>
          <button
            onClick={() => setActiveTab('turns')}
            style={{
              padding: '10px 16px',
              border: 'none',
              background: 'none',
              borderBottom: activeTab === 'turns' ? '2px solid var(--brand-primary)' : '2px solid transparent',
              color: activeTab === 'turns' ? 'var(--brand-primary)' : 'var(--text-secondary)',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Question Turns & Video
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body" style={{ maxHeight: 'calc(90vh - 180px)', overflowY: 'auto' }}>
          {activeTab === 'summary' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* Score Cards Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
                <div style={{ padding: '16px', borderRadius: '10px', background: '#f8fafc', border: '1px solid #e2e8f0', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>Overall Score</div>
                  <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--brand-primary)', marginTop: '4px' }}>
                    {report.overall_score}/100
                  </div>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#16a34a', marginTop: '2px' }}>
                    {report.recommendation}
                  </div>
                </div>

                <div style={{ padding: '16px', borderRadius: '10px', background: '#f8fafc', border: '1px solid #e2e8f0', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>Communication</div>
                  <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#0f172a', marginTop: '4px' }}>
                    {report.communication_score}%
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Clarity & Pace</div>
                </div>

                <div style={{ padding: '16px', borderRadius: '10px', background: '#f8fafc', border: '1px solid #e2e8f0', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>Technical Depth</div>
                  <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#0f172a', marginTop: '4px' }}>
                    {report.technical_score}%
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Accuracy & Concepts</div>
                </div>

                <div style={{ padding: '16px', borderRadius: '10px', background: '#f8fafc', border: '1px solid #e2e8f0', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>Resume Consistency</div>
                  <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#0f172a', marginTop: '4px' }}>
                    {report.resume_consistency_score}%
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Claim Verification</div>
                </div>
              </div>

              {/* Executive Summary */}
              <div style={{ padding: '16px', borderRadius: '10px', background: '#ffffff', border: '1px solid #e2e8f0' }}>
                <h4 style={{ fontSize: '0.9rem', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <FileText size={16} /> Executive AI Summary
                </h4>
                <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                  {report.summary}
                </p>
              </div>

              {/* Strengths & Weaknesses */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div style={{ padding: '16px', borderRadius: '10px', background: '#f0fdf4', border: '1px solid #bbf7d0' }}>
                  <h4 style={{ fontSize: '0.88rem', color: '#166534', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <CheckCircle2 size={16} /> Key Strengths
                  </h4>
                  <ul style={{ paddingLeft: '1.2rem', fontSize: '0.82rem', color: '#15803d', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {report.strengths?.map((s, idx) => (
                      <li key={idx}>{s}</li>
                    ))}
                  </ul>
                </div>

                <div style={{ padding: '16px', borderRadius: '10px', background: '#fffbeb', border: '1px solid #fef08a' }}>
                  <h4 style={{ fontSize: '0.88rem', color: '#92400e', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <AlertTriangle size={16} /> Improvement Areas
                  </h4>
                  <ul style={{ paddingLeft: '1.2rem', fontSize: '0.82rem', color: '#b45309', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {report.weaknesses?.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'turns' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {report.turns?.map((turn) => (
                <div
                  key={turn.turn_number}
                  style={{
                    padding: '16px',
                    borderRadius: '10px',
                    background: '#ffffff',
                    border: '1px solid #e2e8f0',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--brand-primary)' }}>
                      Question {turn.turn_number}
                    </span>
                    <span style={{ fontSize: '0.8rem', color: '#64748b' }}>
                      Score: <strong>{turn.score}/100</strong> • Duration: {turn.duration}
                    </span>
                  </div>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#0f172a' }}>
                    {turn.question_text}
                  </div>
                  <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px', fontSize: '0.84rem', color: '#334155', fontStyle: 'italic' }}>
                    "{turn.transcript}"
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#475569' }}>
                    <strong>AI Feedback:</strong> {turn.feedback}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <button type="button" onClick={onClose} className="cancel-btn">
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default InterviewReportModal;
