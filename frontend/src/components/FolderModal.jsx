import React, { useState } from 'react';
import { X, Folder, FileText, Loader2 } from 'lucide-react';

const FolderModal = ({ isOpen, onClose, onProcess }) => {
    const [folderPath, setFolderPath] = useState('');
    const [jd, setJd] = useState('');
    const [isProcessing, setIsProcessing] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!folderPath || !jd) return;

        setIsProcessing(true);
        try {
            await onProcess(folderPath, jd);
            onClose();
        } catch (err) {
            console.error(err);
        } finally {
            setIsProcessing(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay glass" onClick={onClose}>
            <div className="modal-content glass" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h3>
                        <Folder size={20} />
                        Phase Folder Processing
                    </h3>
                    <button className="close-btn" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="modal-body">
                    <div className="input-group">
                        <label>Local Folder Path</label>
                        <div className="input-with-icon">
                            <Folder className="input-icon" size={16} />
                            <input
                                type="text"
                                value={folderPath}
                                onChange={(e) => setFolderPath(e.target.value)}
                                placeholder="Enter path to resume folder..."
                                required
                            />
                            <button 
                                type="button" 
                                className="browse-btn"
                                onClick={() => document.getElementById('folder-picker-hidden').click()}
                            >
                                Browse
                            </button>
                        </div>
                        <p className="input-tip">
                            Tip: For local processing, you can also paste the full absolute path from your File Explorer.
                        </p>
                        <input
                            type="file"
                            id="folder-picker-hidden"
                            webkitdirectory="true"
                            directory="true"
                            hidden
                            onChange={(e) => {
                                if (e.target.files.length > 0) {
                                    // Extract the base folder name from the first file's path
                                    const firstFile = e.target.files[0];
                                    const pathParts = firstFile.webkitRelativePath.split('/');
                                    if (pathParts.length > 0) {
                                        setFolderPath(pathParts[0]);
                                    }
                                }
                            }}
                        />
                    </div>

                    <div className="input-group">
                        <label>Job Description</label>
                        <div className="textarea-with-icon">
                            <FileText className="input-icon" size={16} />
                            <textarea
                                value={jd}
                                onChange={(e) => setJd(e.target.value)}
                                placeholder="Paste the JC details here for matching..."
                                required
                            />
                        </div>
                    </div>

                    <div className="modal-footer">
                        <button className="cancel-btn" type="button" onClick={onClose}>Cancel</button>
                        <button
                            className="process-btn"
                            type="submit"
                            disabled={isProcessing || !folderPath || !jd}
                        >
                            {isProcessing ? (
                                <>
                                    <Loader2 className="animate-spin" size={16} />
                                    <span>Processing...</span>
                                </>
                            ) : (
                                'Start Screening'
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default FolderModal;
