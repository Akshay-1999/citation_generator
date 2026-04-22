import React, { useState } from 'react';
import { X, Folder, FileText, Loader2, FileUp, Paperclip } from 'lucide-react';

const FolderModal = ({ isOpen, onClose, onProcess }) => {
    const [selectedFiles, setSelectedFiles] = useState([]);
    const [jd, setJd] = useState('');
    const [jdFile, setJdFile] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);

    const handleFolderSelect = (e) => {
        const files = Array.from(e.target.files).filter(f => 
            f.name.toLowerCase().endsWith('.pdf')
        );
        setSelectedFiles(files);
    };

    const handleJdFileChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            setJdFile(file);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (selectedFiles.length === 0 || (!jd && !jdFile)) return;

        setIsProcessing(true);
        try {
            await onProcess(selectedFiles, jd, jdFile);
            setSelectedFiles([]);
            setJd('');
            setJdFile(null);
            onClose();
        } catch (err) {
            console.error(err);
        } finally {
            setIsProcessing(false);
        }
    };

    const handleClose = () => {
        if (!isProcessing) {
            setSelectedFiles([]);
            onClose();
        }
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={handleClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h3>
                        <Folder size={18} />
                        Bulk Resume Screening
                    </h3>
                    <button className="close-btn" onClick={handleClose} disabled={isProcessing}>
                        <X size={18} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="modal-body">
                    <div className="input-group">
                        <label>Select Resume Folder</label>
                        <div
                            style={{
                                border: '2px dashed #d1d5db',
                                borderRadius: '10px',
                                padding: '24px 16px',
                                textAlign: 'center',
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                                background: selectedFiles.length > 0 
                                    ? 'rgba(196, 18, 48, 0.03)' 
                                    : '#f9fafb',
                            }}
                            onClick={() => document.getElementById('folder-picker').click()}
                        >
                            {selectedFiles.length === 0 ? (
                                <>
                                    <FileUp size={28} style={{ color: '#8a94a6', marginBottom: '6px' }} />
                                    <p style={{ color: '#4a5568', margin: '4px 0 0', fontSize: '0.88rem' }}>
                                        Click to select a folder with resume PDFs
                                    </p>
                                    <p style={{ color: '#8a94a6', margin: '4px 0 0', fontSize: '0.75rem' }}>
                                        Only PDF files will be processed
                                    </p>
                                </>
                            ) : (
                                <>
                                    <FileUp size={28} style={{ color: '#C41230', marginBottom: '6px' }} />
                                    <p style={{ color: '#C41230', margin: '4px 0 0', fontSize: '0.88rem', fontWeight: 600 }}>
                                        {selectedFiles.length} PDF file{selectedFiles.length !== 1 ? 's' : ''} selected
                                    </p>
                                    <p style={{ color: '#8a94a6', margin: '4px 0 0', fontSize: '0.75rem' }}>
                                        Click to change selection
                                    </p>
                                </>
                            )}
                        </div>

                        <input
                            type="file"
                            id="folder-picker"
                            webkitdirectory="true"
                            directory="true"
                            multiple
                            hidden
                            onChange={handleFolderSelect}
                        />
                    </div>

                    {selectedFiles.length > 0 && (
                        <div style={{
                            maxHeight: '100px',
                            overflowY: 'auto',
                            background: '#f7f8fa',
                            borderRadius: '8px',
                            padding: '8px 12px',
                            fontSize: '0.75rem',
                            color: '#4a5568',
                            border: '1px solid #e2e5ea'
                        }}>
                            {selectedFiles.map((f, i) => (
                                <div key={i} style={{ 
                                    padding: '3px 0', 
                                    display: 'flex', 
                                    alignItems: 'center', 
                                    gap: '6px' 
                                }}>
                                    <FileText size={12} style={{ flexShrink: 0, color: '#C41230' }} />
                                    {f.name}
                                </div>
                            ))}
                        </div>
                    )}

                    <div className="input-group">
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                            <label style={{ margin: 0 }}>Job Description</label>
                            <button
                                type="button"
                                className="browse-btn"
                                onClick={() => document.getElementById('jd-file-picker').click()}
                                style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
                            >
                                <Paperclip size={14} />
                                {jdFile ? 'Change JD File' : 'Attach JD File'}
                            </button>
                        </div>
                        
                        <input
                            type="file"
                            id="jd-file-picker"
                            hidden
                            onChange={handleJdFileChange}
                            accept=".pdf,.doc,.docx,.txt"
                        />

                        {jdFile && (
                            <div style={{ 
                                display: 'flex', 
                                alignItems: 'center', 
                                gap: '8px', 
                                margin: '0 0 10px 0',
                                padding: '8px 12px',
                                background: 'rgba(196, 18, 48, 0.04)',
                                border: '1px solid rgba(196, 18, 48, 0.15)',
                                borderRadius: '8px',
                                fontSize: '0.82rem',
                                color: '#C41230'
                            }}>
                                <FileText size={14} />
                                <span style={{ flex: 1, fontWeight: 500 }}>{jdFile.name}</span>
                                <button 
                                    type="button" 
                                    onClick={() => setJdFile(null)}
                                    style={{ color: '#8a94a6', '&:hover': { color: '#dc2626' } }}
                                >
                                    <X size={14} />
                                </button>
                            </div>
                        )}

                        <div className="textarea-with-icon">
                            <FileText className="input-icon" size={16} />
                            <textarea
                                value={jd}
                                onChange={(e) => setJd(e.target.value)}
                                placeholder="Paste the JD details here for matching..."
                                required={!jdFile}
                                disabled={!!jdFile}
                                style={{ opacity: jdFile ? 0.6 : 1 }}
                            />
                        </div>
                        {jdFile && (
                            <p style={{ fontSize: '0.75rem', color: '#8a94a6', marginTop: '4px', fontStyle: 'italic' }}>
                                Using attached JD file instead of text area.
                            </p>
                        )}
                    </div>

                    <div className="modal-footer">
                        <button className="cancel-btn" type="button" onClick={handleClose} disabled={isProcessing}>
                            Cancel
                        </button>
                        <button
                            className="process-btn"
                            type="submit"
                            disabled={isProcessing || selectedFiles.length === 0 || (!jd && !jdFile)}
                        >
                            {isProcessing ? (
                                <>
                                    <Loader2 className="animate-spin" size={16} />
                                    <span>Processing...</span>
                                </>
                            ) : (
                                `Screen ${selectedFiles.length || ''} Resume${selectedFiles.length !== 1 ? 's' : ''}`
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default FolderModal;
