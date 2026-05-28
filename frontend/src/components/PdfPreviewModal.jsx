import React, { useState, useEffect } from 'react';
import { X, Download, FileText, ThumbsDown, Loader2, Edit, Save, File } from 'lucide-react';
import { api, BASE_URL } from '../api';

const PdfPreviewModal = ({ isOpen, onClose, resume, onUpdate }) => {
  const [isRejecting, setIsRejecting] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [submittingReject, setSubmittingReject] = useState(false);
  
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(null);
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [showDownloadMenu, setShowDownloadMenu] = useState(false);

  // Force re-fetch of iframe to break browser cache when regenerated
  const [iframeKey, setIframeKey] = useState(0);

  useEffect(() => {
    if (resume?.content) {
      setEditContent(JSON.parse(JSON.stringify(resume.content))); // Deep copy
    }
  }, [resume]);

  if (!isOpen) return null;

  const handleRejectSubmit = async () => {
    if (!feedback.trim()) return;
    setSubmittingReject(true);
    try {
      if (resume?.isMock) {
        await new Promise(resolve => setTimeout(resolve, 800));
        alert(`[Preview Mode] Resume rejected!\nFeedback: "${feedback}"`);
        setIsRejecting(false);
        setFeedback('');
        onClose();
      } else {
        const rawData = await api.rejectResume(resume.originalFile, feedback);
        
        // Map backend snake_case fields to frontend camelCase expectations
        const newResumeData = {
          ...resume, // keep original details like candidateName
          originalFile: resume.originalFile,
          convertedFile: rawData.converted_file,
          uuid: rawData.uuid,
          pdfDownloadUrl: rawData.pdf_download_url,
          docxDownloadUrl: rawData.docx_download_url,
          previewUrl: rawData.preview_url,
          content: rawData.content
        };
        
        // Use onUpdate to pass the new URLs and content back up to parent
        if (onUpdate) {
          onUpdate(newResumeData);
        }
        
        setIsRejecting(false);
        setFeedback('');
        setIframeKey(prev => prev + 1); // Refresh iframe
        alert('Resume reprocessed successfully based on feedback!');
      }
    } catch (err) {
      alert('Failed to submit rejection: ' + err.message);
    } finally {
      setSubmittingReject(false);
    }
  };

  const handleSaveEdit = async () => {
    setIsSavingEdit(true);
    try {
      await api.updateAndRegenerate(resume.uuid, editContent);
      
      if (onUpdate) {
        onUpdate({ ...resume, content: editContent });
      }
      
      setIsEditing(false);
      setIframeKey(prev => prev + 1); // Refresh iframe
      alert('Resume updated and regenerated successfully!');
    } catch (err) {
      alert('Failed to update resume: ' + err.message);
    } finally {
      setIsSavingEdit(false);
    }
  };

  const downloadFile = (formatUrl) => {
    if (formatUrl) {
      const fullUrl = `${BASE_URL}${formatUrl}`;
      const link = document.createElement('a');
      link.href = fullUrl;
      link.setAttribute('download', '');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } else {
      alert('Download link not available.');
    }
    setShowDownloadMenu(false);
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
            
            {/* Edit / Save Button */}
            {!isEditing ? (
              <button 
                onClick={() => setIsEditing(true)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem',
                  background: '#f0f0f0', color: '#333', border: '1px solid #ccc', borderRadius: '6px',
                  cursor: 'pointer', fontWeight: 600, fontSize: '14px', transition: 'all 0.2s ease'
                }}
              >
                <Edit size={16} /> Edit Data
              </button>
            ) : (
              <button 
                onClick={handleSaveEdit}
                disabled={isSavingEdit}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem',
                  background: '#28a745', color: 'white', border: 'none', borderRadius: '6px',
                  cursor: 'pointer', fontWeight: 600, fontSize: '14px', opacity: isSavingEdit ? 0.6 : 1
                }}
              >
                {isSavingEdit ? <Loader2 className="animate-spin" size={16}/> : <Save size={16} />} Save Changes
              </button>
            )}

            {/* Reject Button */}
            <button 
              onClick={() => setIsRejecting(true)}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem',
                background: '#e0e0e0', color: '#333', border: 'none', borderRadius: '6px',
                cursor: 'pointer', fontWeight: 600, fontSize: '14px', transition: 'all 0.2s ease'
              }}
            >
              <ThumbsDown size={16} /> Reject
            </button>

            {/* Download Button with Dropdown */}
            <div style={{ position: 'relative' }}>
              <button 
                onClick={() => setShowDownloadMenu(!showDownloadMenu)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem',
                  background: '#C41230', color: 'white', border: 'none', borderRadius: '6px',
                  cursor: 'pointer', fontWeight: 600, fontSize: '14px', boxShadow: '0 2px 4px rgba(196,18,48,0.3)'
                }}
              >
                <Download size={16} /> Download
              </button>
              
              {showDownloadMenu && (
                <div style={{
                  position: 'absolute', top: '110%', right: 0, background: 'white',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)', borderRadius: '6px', border: '1px solid #eee',
                  zIndex: 10, minWidth: '150px', overflow: 'hidden'
                }}>
                  <div 
                    onClick={() => downloadFile(resume?.pdfDownloadUrl)}
                    style={{ padding: '0.75rem 1rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '14px', borderBottom: '1px solid #f0f0f0' }}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#f9f9f9'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
                  >
                    <FileText size={16} color="#C41230"/> PDF Format
                  </div>
                  <div 
                    onClick={() => downloadFile(resume?.docxDownloadUrl)}
                    style={{ padding: '0.75rem 1rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '14px' }}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#f9f9f9'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
                  >
                    <File size={16} color="#2b579a"/> DOCX Format
                  </div>
                </div>
              )}
            </div>

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
        
        {/* Editor or PDF Viewer */}
        <div style={{ flex: 1, background: '#e5e7eb', position: 'relative', overflowY: 'auto' }}>
          
          {isEditing && editContent ? (
            <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto', background: 'white', minHeight: '100%' }}>
              <h2 style={{marginTop: 0}}>Edit Resume Content</h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label style={{fontWeight: 'bold'}}>Candidate Name</label>
                  <input type="text" value={editContent.candidate_name || ''} 
                    onChange={e => setEditContent({...editContent, candidate_name: e.target.value})}
                    style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc', borderRadius: '4px' }} />
                </div>
                <div>
                  <label style={{fontWeight: 'bold'}}>Designation</label>
                  <input type="text" value={editContent.candidate_designation_based_on_jd || ''} 
                    onChange={e => setEditContent({...editContent, candidate_designation_based_on_jd: e.target.value})}
                    style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc', borderRadius: '4px' }} />
                </div>
                <div>
                  <label style={{fontWeight: 'bold'}}>Profile Summary</label>
                  <textarea value={editContent.profile_summary || ''} 
                    onChange={e => setEditContent({...editContent, profile_summary: e.target.value})}
                    style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc', borderRadius: '4px', minHeight: '100px', fontFamily: 'inherit' }} />
                </div>
              </div>
            </div>
          ) : resume && resume.previewUrl ? (
            <iframe
              key={iframeKey}
              src={`${BASE_URL}${resume.previewUrl}?t=${iframeKey}`}
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
              {/* Omitted rejection modal code for brevity, same as before */}
              <div style={{
                background: 'white', padding: '2rem', borderRadius: '12px',
                width: '90%', maxWidth: '450px', display: 'flex', flexDirection: 'column',
                gap: '1rem', boxShadow: '0 10px 25px rgba(0,0,0,0.3)', border: '1px solid #eee'
              }}>
                <h3 style={{ margin: 0, color: '#1a1a1a', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.2rem', fontWeight: 600 }}>
                  <ThumbsDown size={20} color="#C41230" /> Reject Converted Resume
                </h3>
                <textarea
                  placeholder="Provide feedback..."
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  style={{ width: '100%', height: '120px', borderRadius: '8px', padding: '0.75rem', border: '1px solid #ccc' }}
                />
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
                  <button onClick={() => { setIsRejecting(false); setFeedback(''); }} disabled={submittingReject} style={{ padding: '0.6rem 1.2rem', borderRadius: '6px', border: '1px solid #ccc', background: 'transparent', cursor: submittingReject ? 'not-allowed' : 'pointer', fontWeight: 500 }}>Cancel</button>
                  <button onClick={handleRejectSubmit} disabled={submittingReject} style={{ padding: '0.6rem 1.2rem', borderRadius: '6px', border: 'none', background: '#C41230', color: 'white', cursor: submittingReject ? 'not-allowed' : 'pointer', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {submittingReject ? <><Loader2 size={16} className="spinner-icon" /> Reprocessing...</> : 'Submit Rejection'}
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
