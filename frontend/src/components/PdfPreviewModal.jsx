import React, { useState } from 'react';
import { X, Download, FileText, ThumbsDown, Loader2 } from 'lucide-react';
import { api, BASE_URL } from '../api';

const PdfPreviewModal = ({ isOpen, onClose, resume, onDownload }) => {
  const [isRejecting, setIsRejecting] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [submittingReject, setSubmittingReject] = useState(false);

  if (!isOpen) return null;

  const handleRejectSubmit = async () => {
    if (!feedback.trim()) return;
    setSubmittingReject(true);
    try {
      if (resume?.isMock) {
        // Simulate network delay
        await new Promise(resolve => setTimeout(resolve, 800));
        alert(`[Preview Mode] Resume rejected!\nFeedback: "${feedback}"\n\n(In production, this feedback is saved to the core.converted_resumes database table, status is updated, and the file is permanently deleted from the folder).`);
      } else {
        await api.rejectResume(resume.originalFile, feedback);
        alert('Resume conversion rejected. Feedback saved and file deleted.');
      }
      setIsRejecting(false);
      setFeedback('');
      onClose(); // Close the PDF preview modal
    } catch (err) {
      alert('Failed to submit rejection: ' + err.message);
    } finally {
      setSubmittingReject(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose} style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.6)', zIndex: 9999, display: 'flex',
      alignItems: 'center', justifyContent: 'center', backdropFilter: 'blur(3px)'
    }}>
      <div className="modal-content animate-scale-in" onClick={e => e.stopPropagation()} style={{
        background: 'white', borderRadius: '12px', width: '90%', maxWidth: '1000px',
        height: '85vh', display: 'flex', flexDirection: 'column', overflow: 'hidden',
        boxShadow: '0 20px 40px rgba(0,0,0,0.2)'
      }}>
        {/* Header section */}
        <div style={{ 
          padding: '1rem 1.5rem', borderBottom: '1px solid #eee', 
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: '#f8f9fa'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ background: '#C41230', color: 'white', padding: '0.5rem', borderRadius: '8px' }}>
              <FileText size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#1a1a1a', fontWeight: 600 }}>{resume?.candidateName}</h3>
              <span style={{ fontSize: '0.8rem', color: '#666' }}>Formatted via {resume?.templateName}</span>
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            {/* Reject Button */}
            <button 
              onClick={() => setIsRejecting(true)}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem',
                background: '#e0e0e0', color: '#333', border: 'none', borderRadius: '6px',
                cursor: 'pointer', fontWeight: 600, fontSize: '14px', transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#d2d2d2';
                e.currentTarget.style.color = '#C41230';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#e0e0e0';
                e.currentTarget.style.color = '#333';
              }}
            >
              <ThumbsDown size={16} /> Reject
            </button>

            {/* Download Button */}
            <button 
              onClick={() => onDownload(resume)}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem',
                background: '#C41230', color: 'white', border: 'none', borderRadius: '6px',
                cursor: 'pointer', fontWeight: 600, fontSize: '14px', boxShadow: '0 2px 4px rgba(196,18,48,0.3)'
              }}
            >
              <Download size={16} /> Download PDF
            </button>

            {/* Close Button */}
            <button 
              onClick={onClose}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                width: '36px', height: '36px', border: '1px solid #ddd', borderRadius: '6px',
                background: 'white', color: '#666', cursor: 'pointer'
              }}
            >
              <X size={18} />
            </button>
          </div>
        </div>
        
        {/* PDF Viewer and Overlay feedback box */}
        <div style={{ flex: 1, background: '#e5e7eb', position: 'relative', overflowY: 'auto' }}>
          {resume && resume.isMock ? (
            /* Premium Mock HTML Resume Preview */
            <div style={{
              position: 'absolute', top: '2rem', bottom: '2rem', left: '50%', transform: 'translateX(-50%)',
              width: '80%', maxWidth: '800px', background: 'white', boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
              padding: '3rem', overflowY: 'auto', minHeight: '600px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '2px solid #C41230', paddingBottom: '1rem', marginBottom: '2rem' }}>
                <div>
                  <h1 style={{ fontSize: '24px', margin: '0 0 0.5rem 0', color: '#333', fontWeight: 700 }}>{resume?.candidateName || 'John Doe'}</h1>
                  <p style={{ margin: 0, color: '#666', fontSize: '14px' }}>Software Engineer | React & Python</p>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ 
                    background: '#FFEBEF', color: '#C41230', padding: '0.25rem 0.75rem', 
                    borderRadius: '20px', fontSize: '11px', fontWeight: 600, border: '1px solid #FFD1DA' 
                  }}>
                    PREVIEW MODE
                  </span>
                </div>
              </div>
              
              <h3 style={{ borderBottom: '1px solid #eee', paddingBottom: '0.5rem', color: '#333', fontWeight: 600 }}>Profile Summary</h3>
              <p style={{ color: '#555', lineHeight: 1.6, fontSize: '14px', marginBottom: '2rem' }}>
                Experienced software engineer with a strong background in developing scalable web applications. 
                Proficient in full-stack development using modern technologies. Proven track record of delivering 
                high-quality solutions within tight deadlines.
              </p>
              
              <h3 style={{ borderBottom: '1px solid #eee', paddingBottom: '0.5rem', color: '#333', fontWeight: 600 }}>Technical Skills</h3>
              <ul style={{ color: '#555', lineHeight: 1.6, fontSize: '14px', marginBottom: '2rem', columns: 2 }}>
                <li>Frontend: React, Vue, HTML, CSS</li>
                <li>Backend: Node.js, Python, Java</li>
                <li>Database: PostgreSQL, MongoDB</li>
                <li>DevOps: Docker, AWS, CI/CD</li>
              </ul>

              <h3 style={{ borderBottom: '1px solid #eee', paddingBottom: '0.5rem', color: '#333', fontWeight: 600 }}>Professional Experience</h3>
              <div style={{ marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600, color: '#333', fontSize: '14px' }}>
                  <span>Senior Software Engineer - Tech Solutions Inc.</span>
                  <span>2022 - Present</span>
                </div>
                <p style={{ margin: '0.25rem 0', color: '#666', fontSize: '13px', fontStyle: 'italic' }}>Led frontend development team and improved application load times by 40%.</p>
              </div>
              
              <div style={{ textAlign: 'center', marginTop: '4rem', color: '#aaa', fontSize: '12px' }}>
                <p>-- This is a preview of the converted Estuate Format (Mock Data) --</p>
              </div>
            </div>
          ) : resume && resume.convertedFile ? (
            <iframe
              src={`${BASE_URL}/conversion/api/preview/${resume.convertedFile}`}
              title="PDF Preview"
              style={{ width: '100%', height: '100%', border: 'none', background: 'white' }}
            />
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#666' }}>
              No PDF preview available.
            </div>
          )}

          {/* Rejection Feedback Modal/Popup */}
          {isRejecting && (
            <div style={{
              position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
              background: 'rgba(0,0,0,0.7)', zIndex: 1000, display: 'flex',
              alignItems: 'center', justifyContent: 'center', backdropFilter: 'blur(3px)'
            }}>
              <div style={{
                background: 'white', padding: '2rem', borderRadius: '12px',
                width: '90%', maxWidth: '450px', display: 'flex', flexDirection: 'column',
                gap: '1rem', boxShadow: '0 10px 25px rgba(0,0,0,0.3)', border: '1px solid #eee'
              }}>
                <h3 style={{ margin: 0, color: '#1a1a1a', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.2rem', fontWeight: 600 }}>
                  <ThumbsDown size={20} color="#C41230" /> Reject Converted Resume
                </h3>
                <p style={{ margin: 0, fontSize: '0.9rem', color: '#666', lineHeight: '1.4' }}>
                  Please provide feedback on why this resume is being rejected. This feedback will be saved in the database, and the generated file will be permanently deleted from the folder.
                </p>
                <textarea
                  placeholder="Provide details about the issue (e.g. alignment incorrect, layout issues, missing sections, formatting error...)"
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  disabled={submittingReject}
                  style={{
                    width: '100%', height: '120px', borderRadius: '8px', padding: '0.75rem',
                    border: '1px solid #ccc', fontSize: '0.9rem', outline: 'none', resize: 'none',
                    fontFamily: 'inherit'
                  }}
                />
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
                  <button
                    onClick={() => {
                      setIsRejecting(false);
                      setFeedback('');
                    }}
                    disabled={submittingReject}
                    style={{
                      padding: '0.5rem 1rem', background: '#f0f0f0', border: 'none',
                      borderRadius: '6px', cursor: 'pointer', fontWeight: 600, fontSize: '14px',
                      color: '#333'
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleRejectSubmit}
                    disabled={submittingReject || !feedback.trim()}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem',
                      background: '#C41230', color: 'white', border: 'none', borderRadius: '6px',
                      cursor: 'pointer', fontWeight: 600, fontSize: '14px', opacity: (submittingReject || !feedback.trim()) ? 0.6 : 1
                    }}
                  >
                    {submittingReject ? (
                      <>
                        <Loader2 className="animate-spin" size={16} /> Submitting...
                      </>
                    ) : 'Submit Rejection'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PdfPreviewModal;
