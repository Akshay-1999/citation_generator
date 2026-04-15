import React, { useState } from 'react';
import { X, Folder, FileText, Loader2, FileUp } from 'lucide-react';

const FolderModal = ({ isOpen, onClose, onProcess }) => {
    const [selectedFiles, setSelectedFiles] = useState([]);
    const [jd, setJd] = useState('');
    const [isProcessing, setIsProcessing] = useState(false);

    const handleFolderSelect = (e) => {
        const files = Array.from(e.target.files).filter(f => 
            f.name.toLowerCase().endsWith('.pdf')
        );
        setSelectedFiles(files);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (selectedFiles.length === 0 || !jd) return;

        setIsProcessing(true);
        try {
            await onProcess(selectedFiles, jd);
            setSelectedFiles([]);
            setJd('');
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
        <div className="modal-overlay glass" onClick={handleClose}>
            <div className="modal-content glass" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h3>
                        <Folder size={20} />
                        Bulk Resume Screening
                    </h3>
                    <button className="close-btn" onClick={handleClose} disabled={isProcessing}>
                        <X size={20} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="modal-body">
                    {/* Folder / File Picker */}
                    <div className="input-group">
                        <label>Select Resume Folder</label>
                        <div
                            style={{
                                border: '2px dashed rgba(255,255,255,0.15)',
                                borderRadius: '10px',
                                padding: '24px 16px',
                                textAlign: 'center',
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                                background: selectedFiles.length > 0 
                                    ? 'rgba(59,130,246,0.08)' 
                                    : 'rgba(255,255,255,0.02)',
                            }}
                            onClick={() => document.getElementById('folder-picker').click()}
                            onDragOver={(e) => e.preventDefault()}
                            onDrop={(e) => {
                                e.preventDefault();
                                const files = Array.from(e.dataTransfer.files).filter(f => 
                                    f.name.toLowerCase().endsWith('.pdf')
                                );
                                setSelectedFiles(files);
                            }}
                        >
                            {selectedFiles.length === 0 ? (
                                <>
                                    <FileUp size={32} style={{ color: '#64748b', marginBottom: '8px' }} />
                                    <p style={{ color: '#94a3b8', margin: '4px 0 0', fontSize: '14px' }}>
                                        Click to select a folder or drag & drop PDF files
                                    </p>
                                    <p style={{ color: '#64748b', margin: '4px 0 0', fontSize: '12px' }}>
                                        Only PDF files will be processed
                                    </p>
                                </>
                            ) : (
                                <>
                                    <FileUp size={32} style={{ color: '#3b82f6', marginBottom: '8px' }} />
                                    <p style={{ color: '#60a5fa', margin: '4px 0 0', fontSize: '14px', fontWeight: 600 }}>
                                        {selectedFiles.length} PDF file{selectedFiles.length !== 1 ? 's' : ''} selected
                                    </p>
                                    <p style={{ color: '#64748b', margin: '4px 0 0', fontSize: '12px' }}>
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

                    {/* Show selected file names */}
                    {selectedFiles.length > 0 && (
                        <div style={{
                            maxHeight: '120px',
                            overflowY: 'auto',
                            background: 'rgba(0,0,0,0.2)',
                            borderRadius: '8px',
                            padding: '8px 12px',
                            fontSize: '12px',
                            color: '#94a3b8',
                            marginBottom: '8px'
                        }}>
                            {selectedFiles.map((f, i) => (
                                <div key={i} style={{ 
                                    padding: '3px 0', 
                                    display: 'flex', 
                                    alignItems: 'center', 
                                    gap: '6px' 
                                }}>
                                    <FileText size={12} style={{ flexShrink: 0 }} />
                                    {f.name}
                                </div>
                            ))}
                        </div>
                    )}

                    <div className="input-group">
                        <label>Job Description</label>
                        <div className="textarea-with-icon">
                            <FileText className="input-icon" size={16} />
                            <textarea
                                value={jd}
                                onChange={(e) => setJd(e.target.value)}
                                placeholder="Paste the JD details here for matching..."
                                required
                            />
                        </div>
                    </div>

                    <div className="modal-footer">
                        <button className="cancel-btn" type="button" onClick={handleClose} disabled={isProcessing}>
                            Cancel
                        </button>
                        <button
                            className="process-btn"
                            type="submit"
                            disabled={isProcessing || selectedFiles.length === 0 || !jd}
                        >
                            {isProcessing ? (
                                <>
                                    <Loader2 className="animate-spin" size={16} />
                                    <span>Processing {selectedFiles.length} files...</span>
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
