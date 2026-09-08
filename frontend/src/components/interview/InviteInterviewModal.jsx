import React, { useState } from 'react';
import { Calendar, X, User, Mail, Phone, Briefcase, Building2, Clock, Send } from 'lucide-react';

export const InviteInterviewModal = ({ isOpen, onClose, candidate, batchId, onSend }) => {
  const resolvedJobId = candidate?.batch_id || batchId || '';
  const [formData, setFormData] = useState({
    job_id: resolvedJobId,
    name: candidate?.name || '',
    email: candidate?.email || '',
    phone: candidate?.phone || candidate?.phone_number || '',
    position: candidate?.position || '',
    client: candidate?.client || '',
    experience: candidate?.experience || ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      if (onSend) {
        await onSend(candidate, formData);
      }
      onClose();
    } catch (err) {
      console.error('Failed to send invite:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h3>
            <Calendar size={18} className="title-icon" style={{ marginRight: '8px' }} />
            Schedule AI Video Interview
          </h3>
          <button onClick={onClose} className="icon-btn close-btn" title="Close" type="button">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="input-group">
              <label>Job ID / Batch ID (Auto-assigned)</label>
              <div className="input-with-icon">
                <Briefcase size={16} className="input-icon" />
                <input
                  type="text"
                  name="job_id"
                  value={formData.job_id || 'N/A'}
                  readOnly
                  disabled
                  style={{
                    backgroundColor: '#f1f5f9',
                    color: '#475569',
                    cursor: 'not-allowed',
                    fontFamily: 'monospace',
                    fontWeight: 600,
                    border: '1px solid #cbd5e1'
                  }}
                />
              </div>
            </div>

            <div className="input-group">
              <label>Candidate Name</label>
              <div className="input-with-icon">
                <User size={16} className="input-icon" />
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  required
                  placeholder="Enter candidate name"
                />
              </div>
            </div>

            <div className="input-group">
              <label>Candidate Email</label>
              <div className="input-with-icon">
                <Mail size={16} className="input-icon" />
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  placeholder="candidate@example.com"
                />
              </div>
            </div>

            <div className="input-group">
              <label>Candidate Mobile Number</label>
              <div className="input-with-icon">
                <Phone size={16} className="input-icon" />
                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  placeholder="e.g. +91 9876543210 / +1 (555) 000-0000"
                />
              </div>
            </div>

            <div className="input-group">
              <label>Position / Role</label>
              <div className="input-with-icon">
                <Briefcase size={16} className="input-icon" />
                <input
                  type="text"
                  name="position"
                  value={formData.position}
                  onChange={handleChange}
                  required
                  placeholder="e.g. Senior Software Engineer"
                />
              </div>
            </div>

            <div className="input-group">
              <label>Client</label>
              <div className="input-with-icon">
                <Building2 size={16} className="input-icon" />
                <input
                  type="text"
                  name="client"
                  value={formData.client}
                  onChange={handleChange}
                  required
                  placeholder="e.g. Estuate Inc"
                />
              </div>
            </div>

            <div className="input-group">
              <label>Years of Experience</label>
              <div className="input-with-icon">
                <Clock size={16} className="input-icon" />
                <input
                  type="number"
                  name="experience"
                  value={formData.experience}
                  onChange={handleChange}
                  required
                  min="0"
                  step="0.5"
                  placeholder="e.g. 5"
                />
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" onClick={onClose} className="cancel-btn">
              Cancel
            </button>
            <button type="submit" className="process-btn" disabled={isSubmitting}>
              {isSubmitting ? 'Sending...' : 'Send Invite'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default InviteInterviewModal;
