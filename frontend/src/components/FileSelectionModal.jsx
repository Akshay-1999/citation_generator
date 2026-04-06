import React, { useState, useEffect } from 'react';
import { X, Search, FileText, Trash2, Check, Loader2 } from 'lucide-react';
import { api } from '../api';

const FileSelectionModal = ({ isOpen, onClose, onSelect, selectedFiles }) => {
    const [files, setFiles] = useState([]);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [deletingId, setDeletingId] = useState(null);

    const fetchFiles = async () => {
        setLoading(true);
        try {
            const data = await api.listFiles();
            setFiles(data);
        } catch (err) {
            console.error('Failed to fetch files:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (isOpen) {
            fetchFiles();
        }
    }, [isOpen]);

    const handleDelete = async (e, fileId) => {
        e.stopPropagation();
        if (!window.confirm('Are you sure you want to permanently delete this file?')) return;
        
        setDeletingId(fileId);
        try {
            await api.deleteFile(fileId);
            setFiles(files.filter(f => f.file_id !== fileId));
        } catch (err) {
            alert('Failed to delete file: ' + err.message);
        } finally {
            setDeletingId(null);
        }
    };

    const filteredFiles = files.filter(file => 
        file.filename.toLowerCase().includes(searchQuery.toLowerCase())
    );

    if (!isOpen) return null;

    return (
        <div className="modal-overlay">
            <div className="modal-content file-selection-modal glass">
                <div className="modal-header">
                    <h3>File Context</h3>
                    <button className="close-btn" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                <div className="search-bar">
                    <Search size={18} className="search-icon" />
                    <input 
                        type="text" 
                        placeholder="Search files..." 
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>

                <div className="file-list-container">
                    {loading ? (
                        <div className="loading-state">
                            <Loader2 className="animate-spin" size={24} />
                            <p>Loading files...</p>
                        </div>
                    ) : filteredFiles.length === 0 ? (
                        <div className="empty-state">
                            <p>{searchQuery ? 'No files match your search.' : 'No files uploaded yet.'}</p>
                        </div>
                    ) : (
                        <div className="file-grid">
                            {filteredFiles.map((file) => {
                                const isSelected = selectedFiles.some(f => f.file_id === file.file_id);
                                return (
                                    <div 
                                        key={file.file_id} 
                                        className={`file-card ${isSelected ? 'selected' : ''}`}
                                        onClick={() => onSelect(file)}
                                    >
                                        <div className="file-icon">
                                            <FileText size={24} />
                                        </div>
                                        <div className="file-info">
                                            <span className="file-name" title={file.filename}>{file.filename}</span>
                                            <span className="file-meta">{file.size_mb.toFixed(2)} MB • {file.extension}</span>
                                        </div>
                                        <div className="file-actions">
                                            <button 
                                                className="action-btn delete-btn" 
                                                onClick={(e) => handleDelete(e, file.file_id)}
                                                disabled={deletingId === file.file_id}
                                            >
                                                {deletingId === file.file_id ? (
                                                    <Loader2 className="animate-spin" size={16} />
                                                ) : (
                                                    <Trash2 size={16} />
                                                )}
                                            </button>
                                            <div className="selection-indicator">
                                                {isSelected && <Check size={16} />}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>

                <div className="modal-footer">
                    <button className="primary-btn" onClick={onClose}>Done</button>
                </div>
            </div>
        </div>
    );
};

export default FileSelectionModal;
