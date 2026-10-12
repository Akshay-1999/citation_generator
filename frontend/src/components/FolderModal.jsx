import React, { useState, useEffect } from 'react';
import { 
    X, Folder, FileText, Loader2, FileUp, Briefcase, 
    Building2, Clock, CheckCircle2, ChevronDown, ChevronUp, AlertCircle, Layers
} from 'lucide-react';
import { api } from '../api';

const FolderModal = ({ isOpen, onClose, onProcess }) => {
    const [selectedFiles, setSelectedFiles] = useState([]);
    const [jobs, setJobs] = useState([]);
    const [selectedJobId, setSelectedJobId] = useState('');
    const [batchName, setBatchName] = useState('');
    const [isLoadingJobs, setIsLoadingJobs] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [showJdPreview, setShowJdPreview] = useState(false);

    // Fetch active jobs whenever the modal opens
    useEffect(() => {
        try {
            localStorage.removeItem('recai_jobs');
        } catch (e) {}

        if (isOpen) {
            loadJobs();
            // Set default suggested batch name
            const today = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            setBatchName(`Batch - ${today}`);
        }
    }, [isOpen]);

    const loadJobs = async () => {
        setIsLoadingJobs(true);
        try {
            const data = await api.fetchJobs();
            const activeJobs = (data || []).filter(j => j.status !== 'CLOSED');
            setJobs(activeJobs);
            // Default select the first active job if not already chosen, or reset if no longer valid
            if (activeJobs.length > 0) {
                if (!selectedJobId || !activeJobs.some(j => (j.job_id || j.id || j.job_code) === selectedJobId)) {
                    setSelectedJobId(activeJobs[0].job_id || activeJobs[0].id || activeJobs[0].job_code);
                }
            } else {
                setSelectedJobId('');
            }
        } catch (err) {
            console.error('Failed to load jobs:', err);
        } finally {
            setIsLoadingJobs(false);
        }
    };

    const handleFolderSelect = (e) => {
        const files = Array.from(e.target.files).filter(f => 
            ['.pdf', '.doc', '.docx'].some(ext => f.name.toLowerCase().endsWith(ext)) &&
            !f.name.startsWith('~$')  // exclude Word lock/temp files
        );
        setSelectedFiles(files);
    };

    // Find the currently selected job object
    const selectedJob = jobs.find(j => (j.job_id === selectedJobId || j.job_code === selectedJobId || j.id === selectedJobId));

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (selectedFiles.length === 0 || !selectedJob) return;

        setIsProcessing(true);
        try {
            const clientName = selectedJob.client_name || '';
            const exp = selectedJob.experience !== undefined && selectedJob.experience !== null
                ? selectedJob.experience
                : (selectedJob.min_experience !== undefined && selectedJob.min_experience !== null ? selectedJob.min_experience : 0);
            const dateStr = new Date().toISOString().split('T')[0];
            const cleanClient = (clientName || 'Client').replace(/\s+/g, '_');
            const cleanPos = (selectedJob.position || selectedJob.title || 'Position').replace(/\s+/g, '_');
            const defaultReportName = `${cleanClient}_${cleanPos}_${exp}_${dateStr}`;
            const reportName = selectedJob.report_name || batchName || defaultReportName;

            const extraMetadata = {
                client_name: clientName,
                experience: exp,
                total_experience: exp,
                total_year_of_experience: exp,
                report_name: reportName,
                position: selectedJob.position || selectedJob.title || '',
                job_id: selectedJob.job_id || selectedJob.id || selectedJob.job_code || ''
            };

            // We pass the resumes along with the official JD text and Job ID metadata
            await onProcess(
                selectedFiles, 
                selectedJob.jd_text, 
                null, 
                selectedJob.job_id || selectedJob.id || selectedJob.job_code,
                batchName,
                extraMetadata
            );
            setSelectedFiles([]);
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
            setShowJdPreview(false);
            onClose();
        }
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={handleClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '580px' }}>
                <div className="modal-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Folder size={20} color="var(--brand-primary)" />
                        <h3>Bulk Resume Screening</h3>
                    </div>
                    <button className="close-btn" onClick={handleClose} disabled={isProcessing}>
                        <X size={18} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="modal-body" style={{ position: 'relative' }}>
                    {isProcessing && (
                        <div className="buffering-overlay">
                            <Loader2 className="animate-spin" size={40} color="#C41230" />
                            <div className="processing-text">Screening Resumes...</div>
                            <p style={{ fontSize: '0.8rem', color: '#8a94a6' }}>
                                Matching candidates against: {selectedJob?.title || selectedJob?.position || 'Selected Job'}
                            </p>
                        </div>
                    )}

                    {/* Step 1: Select Approved Job Position */}
                    <div className="input-group">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                            <label style={{ margin: 0, fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <Briefcase size={16} color="var(--brand-primary)" />
                                Select Job Position *
                            </label>
                            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                                Pre-approved by Admin
                            </span>
                        </div>

                        {isLoadingJobs ? (
                            <div style={{ padding: '0.75rem', background: '#f7f8fa', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                                <Loader2 size={16} className="animate-spin" />
                                <span>Loading active jobs...</span>
                            </div>
                        ) : jobs.length === 0 ? (
                            <div style={{
                                padding: '12px 14px',
                                background: '#fffbeb',
                                border: '1px solid #fde68a',
                                borderRadius: '8px',
                                fontSize: '0.82rem',
                                color: '#b45309',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px'
                            }}>
                                <AlertCircle size={18} />
                                <div>
                                    <strong>No active jobs found.</strong> An Administrator must create a Job in the Admin Panel before screening.
                                </div>
                            </div>
                        ) : (
                            <select
                                value={selectedJobId}
                                onChange={(e) => setSelectedJobId(e.target.value)}
                                style={{
                                    width: '100%',
                                    padding: '0.75rem 1rem',
                                    borderRadius: '8px',
                                    border: '1px solid var(--glass-border)',
                                    background: '#ffffff',
                                    fontSize: '0.88rem',
                                    fontWeight: 500,
                                    outline: 'none',
                                    cursor: 'pointer'
                                }}
                                required
                            >
                                <option value="" disabled>-- Choose an Approved Job Position --</option>
                                {jobs.map((job) => (
                                    <option key={job.job_id || job.id || job.title} value={job.job_id || job.id}>
                                        {job.title || job.position || job.job_name} — {job.client_name || 'Client'} ({job.min_experience !== undefined ? job.min_experience : (job.experience || 0)}+ yrs)
                                    </option>
                                ))}
                            </select>
                        )}

                        {/* Selected Job Preview Card */}
                        {selectedJob && (
                            <div style={{
                                marginTop: '10px',
                                padding: '12px 14px',
                                background: 'rgba(196, 18, 48, 0.03)',
                                border: '1px solid rgba(196, 18, 48, 0.15)',
                                borderRadius: '10px'
                            }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                    <div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                            <Briefcase size={16} color="var(--brand-primary)" />
                                            <span style={{ fontWeight: 600, fontSize: '0.92rem', color: 'var(--text-primary)' }}>
                                                {selectedJob.title || selectedJob.position || selectedJob.job_name}
                                            </span>
                                        </div>
                                        <div style={{ display: 'flex', gap: '14px', marginTop: '6px', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                                            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                                <Building2 size={13} color="var(--brand-primary)" />
                                                {selectedJob.client_name}
                                            </span>
                                            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                                <Clock size={13} color="var(--brand-primary)" />
                                                {selectedJob.min_experience ? `${selectedJob.min_experience}+ Years Exp` : 'Any Exp'}
                                            </span>
                                        </div>
                                    </div>

                                    <button
                                        type="button"
                                        onClick={() => setShowJdPreview(!showJdPreview)}
                                        style={{
                                            background: 'none',
                                            border: 'none',
                                            color: 'var(--brand-primary)',
                                            fontSize: '0.75rem',
                                            fontWeight: 600,
                                            cursor: 'pointer',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '2px'
                                        }}
                                    >
                                        {showJdPreview ? 'Hide JD' : 'Preview JD'}
                                        {showJdPreview ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                    </button>
                                </div>

                                {showJdPreview && (
                                    <div style={{
                                        marginTop: '10px',
                                        padding: '10px',
                                        background: '#ffffff',
                                        border: '1px solid var(--glass-border)',
                                        borderRadius: '6px',
                                        fontSize: '0.78rem',
                                        maxHeight: '120px',
                                        overflowY: 'auto',
                                        whiteSpace: 'pre-wrap',
                                        lineHeight: 1.4,
                                        color: 'var(--text-secondary)'
                                    }}>
                                        {selectedJob.jd_text}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Step 2: Upload Resumes Folder */}
                    <div className="input-group">
                        <label style={{ fontWeight: 600 }}>Select Resumes Folder *</label>
                        <div
                            style={{
                                border: '2px dashed #d1d5db',
                                borderRadius: '10px',
                                padding: '22px 16px',
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
                                        Click to select folder with candidate resumes
                                    </p>
                                    <p style={{ color: '#8a94a6', margin: '4px 0 0', fontSize: '0.75rem' }}>
                                        Supports PDF, DOC, and DOCX files
                                    </p>
                                </>
                            ) : (
                                <>
                                    <FileUp size={28} style={{ color: '#C41230', marginBottom: '6px' }} />
                                    <p style={{ color: '#C41230', margin: '4px 0 0', fontSize: '0.88rem', fontWeight: 600 }}>
                                        {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
                                    </p>
                                    <p style={{ color: '#8a94a6', margin: '4px 0 0', fontSize: '0.75rem' }}>
                                        Click to change folder selection
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
                            maxHeight: '90px',
                            overflowY: 'auto',
                            background: '#f7f8fa',
                            borderRadius: '8px',
                            padding: '8px 12px',
                            fontSize: '0.75rem',
                            color: '#4a5568',
                            border: '1px solid #e2e5ea',
                            marginBottom: '1rem'
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

                    {/* Step 3: Optional Batch Label */}
                    <div className="input-group" style={{ marginBottom: '0.5rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                            <label style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                Batch Label / Source (Optional)
                            </label>
                        </div>
                        <div className="input-with-icon">
                            <Layers className="input-icon" size={16} />
                            <input
                                type="text"
                                value={batchName}
                                onChange={(e) => setBatchName(e.target.value)}
                                placeholder="e.g. Batch 1 - LinkedIn / Vendor"
                                style={{
                                    width: '100%',
                                    padding: '0.55rem 0.75rem 0.55rem 2.2rem',
                                    borderRadius: '8px',
                                    border: '1px solid var(--glass-border)',
                                    fontSize: '0.82rem'
                                }}
                            />
                        </div>
                    </div>

                    <div className="modal-footer" style={{ marginTop: '1.25rem' }}>
                        <button className="cancel-btn" type="button" onClick={handleClose} disabled={isProcessing}>
                            Cancel
                        </button>
                        <button
                            className="process-btn"
                            type="submit"
                            disabled={isProcessing || selectedFiles.length === 0 || !selectedJob}
                            style={{
                                opacity: (selectedFiles.length === 0 || !selectedJob) ? 0.6 : 1
                            }}
                        >
                            {isProcessing ? (
                                <>
                                    <Loader2 className="animate-spin" size={16} />
                                    <span>Processing...</span>
                                </>
                            ) : (
                                `Screen ${selectedFiles.length || ''} Resume${selectedFiles.length !== 1 ? 's' : ''} for ${selectedJob ? (selectedJob.job_code || selectedJob.job_id) : 'Selected Job'}`
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default FolderModal;
