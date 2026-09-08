import React from 'react';
import { Clock, CheckCircle2, AlertCircle, Loader2, Send, PlayCircle, XCircle } from 'lucide-react';

const STATUS_CONFIG = {
  CREATED: { label: 'Created', bg: '#f1f5f9', color: '#475569', icon: Clock },
  EMAIL_SENT: { label: 'Invite Sent', bg: '#eff6ff', color: '#2563eb', icon: Send },
  STARTED: { label: 'Started', bg: '#fef3c7', color: '#d97706', icon: PlayCircle },
  IN_PROGRESS: { label: 'In Progress', bg: '#fef3c7', color: '#d97706', icon: PlayCircle },
  SUBMITTED: { label: 'Submitted', bg: '#f0fdf4', color: '#16a34a', icon: CheckCircle2 },
  PROCESSING: { label: 'AI Processing', bg: '#faf5ff', color: '#9333ea', icon: Loader2, spin: true },
  COMPLETED: { label: 'Completed', bg: '#ecfdf5', color: '#059669', icon: CheckCircle2 },
  FAILED: { label: 'Failed', bg: '#fef2f2', color: '#dc2626', icon: XCircle },
  EXPIRED: { label: 'Expired', bg: '#f3f4f6', color: '#9ca3af', icon: AlertCircle }
};

export const InterviewStatusBadge = ({ status = 'CREATED' }) => {
  const normalizedStatus = status?.toUpperCase() || 'CREATED';
  const config = STATUS_CONFIG[normalizedStatus] || STATUS_CONFIG.CREATED;
  const IconComponent = config.icon;

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '4px 10px',
        borderRadius: '16px',
        fontSize: '0.75rem',
        fontWeight: '600',
        backgroundColor: config.bg,
        color: config.color,
        border: `1px solid ${config.color}25`,
        whiteSpace: 'nowrap'
      }}
    >
      <IconComponent size={12} className={config.spin ? 'animate-spin' : ''} />
      {config.label}
    </span>
  );
};

export default InterviewStatusBadge;
