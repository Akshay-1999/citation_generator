import React, { useState, useEffect } from 'react';
import { 
    UserPlus, Search, Trash2, Key, Shield, User as UserIcon, 
    Loader2, Mail, Lock, Briefcase, Plus, FileText, Building2, 
    Calendar, Eye, CheckCircle2, X, Clock, FileSpreadsheet
} from 'lucide-react';
import { api } from '../api';

const AdminPanel = ({ onRefreshReports }) => {
    // Tab Navigation: 'jobs' | 'users'
    const [activeTab, setActiveTab] = useState('jobs');

    // ─── Users State ──────────────────────────────────────────────────────────
    const [users, setUsers] = useState([]);
    const [searchTerm, setSearchTerm] = useState('');
    const [isLoadingUsers, setIsLoadingUsers] = useState(false);
    const [isAddingUser, setIsAddingUser] = useState(false);
    const [userError, setUserError] = useState('');

    const [newUser, setNewUser] = useState({
        user_name: '',
        email: '',
        user_role: 'user',
        password: ''
    });

    // ─── Jobs State ───────────────────────────────────────────────────────────
    const [jobs, setJobs] = useState([]);
    const [jobSearchTerm, setJobSearchTerm] = useState('');
    const [isLoadingJobs, setIsLoadingJobs] = useState(true);
    const [isAddingJob, setIsAddingJob] = useState(false);
    const [viewingJdJob, setViewingJdJob] = useState(null);
    const [isReadingJdFile, setIsReadingJdFile] = useState(false);
    const [jobError, setJobError] = useState('');

    const [newJob, setNewJob] = useState({
        title: '',
        client_name: '',
        min_experience: 3,
        jd_text: '',
        status: 'OPEN'
    });

    useEffect(() => {
        try {
            localStorage.removeItem('recai_jobs');
        } catch (e) {}
        loadJobs();
        loadActiveUsers();
    }, []);

    // ─── Job Requisition Handlers ─────────────────────────────────────────────
    const loadJobs = async () => {
        setIsLoadingJobs(true);
        try {
            const data = await api.fetchAdminJobs();
            setJobs(data || []);
        } catch (err) {
            console.error('Failed to load admin jobs:', err);
            setJobError('Failed to load jobs.');
        } finally {
            setIsLoadingJobs(false);
        }
    };

    const handleImportJdFile = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setIsReadingJdFile(true);
        setJobError('');

        try {
            // Call backend route @jobrouter.api_route("/read_attached_file") to extract text
            const response = await api.readAttachedFile(file);
            if (response && response.file_content) {
                setNewJob(prev => ({ ...prev, jd_text: response.file_content }));
            } else if (file.name.endsWith('.txt') || file.name.endsWith('.md')) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    setNewJob(prev => ({ ...prev, jd_text: event.target.result }));
                };
                reader.readAsText(file);
            }
        } catch (err) {
            console.error('Error reading attached JD file via backend:', err);
            if (file.name.endsWith('.txt') || file.name.endsWith('.md')) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    setNewJob(prev => ({ ...prev, jd_text: event.target.result }));
                };
                reader.readAsText(file);
            } else {
                setJobError(`Failed to read file: ${err.message}`);
            }
        } finally {
            setIsReadingJdFile(false);
            e.target.value = '';
        }
    };

    const handleCreateJob = async (e) => {
        e.preventDefault();
        setJobError('');

        if (!newJob.title.trim()) {
            setJobError('Job title is required.');
            return;
        }
        if (!newJob.client_name.trim()) {
            setJobError('Client name is required.');
            return;
        }
        if (!newJob.jd_text.trim()) {
            setJobError('Job description text is required.');
            return;
        }

        try {
            const res = await api.createJob(newJob);
            await loadJobs();
            if (onRefreshReports) {
                await onRefreshReports();
            }
            setIsAddingJob(false);
            const createdReportName = res?.report_name || (typeof res === 'string' ? res : '');
            setNewJob({
                title: '',
                client_name: '',
                min_experience: 3,
                jd_text: '',
                status: 'OPEN'
            });
            alert(`Job Requisition created successfully!\n${createdReportName ? `Generated Report: ${createdReportName}\n\n` : ''}Recruiters can now select this Job for bulk screening.`);
        } catch (err) {
            setJobError(err.message || 'Failed to create job.');
        }
    };

    const handleDeleteJob = async (jobId) => {
        if (!window.confirm("Are you sure you want to delete this Job position?")) return;
        try {
            await api.deleteJob(jobId);
            setJobs(prev => prev.filter(j => j.job_id !== jobId && j.id !== jobId));
            if (onRefreshReports) {
                await onRefreshReports();
            }
        } catch (err) {
            alert('Failed to delete job: ' + err.message);
        }
    };

    const handleToggleJobStatus = async (jobId, currentStatus) => {
        const isCurrentlyOpen = currentStatus === 'OPEN' || currentStatus === true || String(currentStatus).toLowerCase() === 'active';
        const nextStatus = isCurrentlyOpen ? 'CLOSED' : 'OPEN';
        try {
            await api.updateJobStatus(jobId, nextStatus);
            setJobs(prev => prev.map(j => (j.job_id === jobId || j.id === jobId) ? { ...j, status: nextStatus } : j));
            if (onRefreshReports) {
                await onRefreshReports();
            }
        } catch (err) {
            alert('Failed to update status: ' + err.message);
        }
    };

    const filteredJobs = jobs.filter(job => {
        if (!jobSearchTerm.trim()) return true;
        const term = jobSearchTerm.toLowerCase();
        return (
            (job.title || '').toLowerCase().includes(term) ||
            (job.position || '').toLowerCase().includes(term) ||
            (job.job_name || '').toLowerCase().includes(term) ||
            (job.client_name || '').toLowerCase().includes(term) ||
            (job.job_code || '').toLowerCase().includes(term)
        );
    });

    // ─── User Management Handlers ─────────────────────────────────────────────
    const validatePasswordComplexity = (password) => {
        const minLength = 12;
        const hasUpperCase = /[A-Z]/.test(password);
        const hasNumber = /[0-9]/.test(password);
        const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
        
        if (password.length < minLength) return "Password must be at least 12 characters long.";
        if (!hasUpperCase) return "Password must contain at least one uppercase letter.";
        if (!hasNumber) return "Password must contain at least one number.";
        if (!hasSpecialChar) return "Password must contain at least one special character.";
        
        return null;
    };

    const loadActiveUsers = async () => {
        setIsLoadingUsers(true);
        try {
            const data = await api.fetchActiveUsers();
            setUsers(data || []);
        } catch (err) {
            console.error('Failed to load active users:', err);
        } finally {
            setIsLoadingUsers(false);
        }
    };

    const handleSearchUser = async (e) => {
        e.preventDefault();
        if (!searchTerm) return;
        setIsLoadingUsers(true);
        try {
            const data = await api.getUser(searchTerm);
            setUsers([data]);
            setUserError('');
        } catch (err) {
            setUserError('User not found');
            setUsers([]);
        } finally {
            setIsLoadingUsers(false);
        }
    };

    const handleCreateUser = async (e) => {
        e.preventDefault();
        setUserError('');
        
        const passwordError = validatePasswordComplexity(newUser.password);
        if (passwordError) {
            setUserError(passwordError);
            return;
        }

        try {
            await api.createUser(newUser);
            setIsAddingUser(false);
            setNewUser({ user_name: '', email: '', user_role: 'user', password: '' });
            await loadActiveUsers();
            alert('User created successfully!');
        } catch (err) {
            setUserError(err.message);
        }
    };

    const handleDeleteUser = async (email) => {
        if (!window.confirm(`Are you sure you want to delete ${email}?`)) return;
        try {
            await api.deleteUser(email);
            setUsers(users.filter(u => u.email !== email));
            alert('User deleted successfully');
        } catch (err) {
            alert('Deletion failed: ' + err.message);
        }
    };

    const handleResetPassword = async (email) => {
        const newPass = window.prompt(`Enter new password for ${email}:\n(Min 12 chars, 1 uppercase, 1 number, 1 special char)`);
        if (!newPass) return;

        const passwordError = validatePasswordComplexity(newPass);
        if (passwordError) {
            alert(passwordError);
            return;
        }

        try {
            await api.updatePassword(email, newPass);
            alert('Password updated successfully');
        } catch (err) {
            alert('Update failed: ' + err.message);
        }
    };

    const handleUpdateRole = async (email, newRole) => {
        try {
            await api.updateRole(email, newRole);
            setUsers(prev => prev.map(u => u.email === email ? { ...u, user_role: newRole } : u));
            alert('Role updated successfully');
        } catch (err) {
            alert('Role update failed: ' + err.message);
        }
    };

    const handleUpdateStatus = async (email, newStatus) => {
        const isActive = newStatus === 'active';
        try {
            await api.updateActiveStatus(email, isActive);
            setUsers(prev => prev.map(u => u.email === email ? { ...u, is_active: isActive } : u));
            alert('Status updated successfully');
        } catch (err) {
            alert('Status update failed: ' + err.message);
        }
    };

    return (
        <div className="admin-container animate-fade-in">
            {/* Top Navigation Tabs */}
            <div className="admin-tab-nav" style={{ display: 'flex', gap: '10px', marginBottom: '1.5rem', borderBottom: '1px solid var(--glass-border)', paddingBottom: '0.75rem' }}>
                <button
                    className={`admin-tab-btn ${activeTab === 'jobs' ? 'active' : ''}`}
                    onClick={() => setActiveTab('jobs')}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '8px 18px',
                        borderRadius: '8px',
                        border: 'none',
                        background: activeTab === 'jobs' ? 'var(--brand-primary)' : 'transparent',
                        color: activeTab === 'jobs' ? '#ffffff' : 'var(--text-secondary)',
                        fontWeight: 600,
                        fontSize: '0.9rem',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease'
                    }}
                >
                    <Briefcase size={18} />
                    <span>Job Requisitions</span>
                    <span style={{ 
                        fontSize: '0.75rem', 
                        padding: '2px 6px', 
                        borderRadius: '10px', 
                        background: activeTab === 'jobs' ? 'rgba(255,255,255,0.2)' : 'var(--bg-accent)',
                        color: activeTab === 'jobs' ? '#ffffff' : 'var(--text-muted)'
                    }}>
                        {jobs.length}
                    </span>
                </button>

                <button
                    className={`admin-tab-btn ${activeTab === 'users' ? 'active' : ''}`}
                    onClick={() => setActiveTab('users')}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '8px 18px',
                        borderRadius: '8px',
                        border: 'none',
                        background: activeTab === 'users' ? 'var(--brand-primary)' : 'transparent',
                        color: activeTab === 'users' ? '#ffffff' : 'var(--text-secondary)',
                        fontWeight: 600,
                        fontSize: '0.9rem',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease'
                    }}
                >
                    <Shield size={18} />
                    <span>User Management</span>
                </button>
            </div>

            {/* ════════════════════════════════════════════════════════════════════
               TAB 1: JOB REQUISITIONS (JOB IDS)
               ════════════════════════════════════════════════════════════════════ */}
            {activeTab === 'jobs' && (
                <div>
                    <div className="admin-header">
                        <div>
                            <h2>Job Requisition Management</h2>
                            <p className="text-muted">Create official job positions and descriptions so recruiters can map multiple candidate batches to the same position</p>
                        </div>
                        <button className="process-btn" onClick={() => {
                            setIsAddingJob(true);
                            setJobError('');
                        }}>
                            <Plus size={20} />
                            <span>Create Job</span>
                        </button>
                    </div>

                    <div className="admin-actions-bar" style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', background: '#fff', padding: '1rem', borderRadius: '16px', border: '1px solid var(--glass-border)', boxShadow: '0 4px 20px rgba(0, 0, 0, 0.03)' }}>
                        <div className="input-with-icon" style={{ flex: 1 }}>
                            <Search size={18} className="input-icon" />
                            <input
                                type="text"
                                placeholder="Search by position, role, or client..."
                                value={jobSearchTerm}
                                onChange={(e) => setJobSearchTerm(e.target.value)}
                                style={{ width: '100%', padding: '0.6rem 1rem 0.6rem 2.5rem', borderRadius: '8px', border: '1px solid var(--glass-border)', outline: 'none' }}
                            />
                        </div>
                        {jobSearchTerm && (
                            <button
                                type="button"
                                className="action-btn-secondary"
                                onClick={() => setJobSearchTerm('')}
                                style={{ padding: '0.6rem 1rem', fontSize: '0.85rem', border: '1px solid var(--glass-border)', background: 'white', borderRadius: '8px', cursor: 'pointer' }}
                            >
                                Clear
                            </button>
                        )}
                    </div>

                    {jobError && <div className="error-message" style={{ marginBottom: '1.5rem' }}>{jobError}</div>}

                    <div className="user-table-container glass">
                        <table className="admin-table">
                            <thead>
                                <tr>
                                    <th>Role / Position</th>
                                    <th>Client / Company</th>
                                    <th>Min Experience</th>
                                    <th>Status</th>
                                    <th>Created At</th>
                                    <th style={{ textAlign: 'right' }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredJobs.length > 0 ? filteredJobs.map((job) => (
                                    <tr key={job.job_id || job.id || job.title} className="animate-fade-in">
                                        <td>
                                            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                                                {job.title || job.position || job.job_name}
                                            </div>
                                            {job.report_name && (
                                                <div style={{ 
                                                    fontSize: '0.74rem', 
                                                    color: 'var(--brand-primary)', 
                                                    fontFamily: 'monospace', 
                                                    marginTop: '3px',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '4px'
                                                }}>
                                                    <FileSpreadsheet size={12} />
                                                    <span title={job.report_name}>{job.report_name}</span>
                                                </div>
                                            )}
                                        </td>
                                        <td>
                                            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                <Building2 size={14} color="var(--brand-primary)" />
                                                <span>{job.client_name || 'N/A'}</span>
                                            </div>
                                        </td>
                                        <td>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.85rem' }}>
                                                <Clock size={14} color="var(--text-muted)" />
                                                <span>{job.min_experience !== undefined ? `${job.min_experience}+ Years` : 'Not specified'}</span>
                                            </div>
                                        </td>
                                        <td>
                                            <button
                                                onClick={() => handleToggleJobStatus(job.job_id || job.id, job.status || 'OPEN')}
                                                style={{
                                                    border: 'none',
                                                    background: job.status === 'CLOSED' ? 'rgba(148, 163, 184, 0.15)' : 'rgba(22, 163, 74, 0.1)',
                                                    color: job.status === 'CLOSED' ? '#64748b' : 'var(--success)',
                                                    padding: '4px 10px',
                                                    borderRadius: '99px',
                                                    fontSize: '0.75rem',
                                                    fontWeight: 600,
                                                    cursor: 'pointer'
                                                }}
                                                title="Click to toggle status"
                                            >
                                                {job.status === 'CLOSED' ? 'Closed' : 'Active (Open)'}
                                            </button>
                                        </td>
                                        <td>
                                            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                                <Calendar size={13} />
                                                {job.created_at ? new Date(job.created_at).toLocaleDateString() : 'Recent'}
                                            </div>
                                        </td>
                                        <td style={{ textAlign: 'right' }}>
                                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                                                <button
                                                    className="action-btn"
                                                    title="View Full Job Description"
                                                    onClick={() => setViewingJdJob(job)}
                                                    style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '6px 10px', fontSize: '0.78rem' }}
                                                >
                                                    <Eye size={15} />
                                                    <span>View JD</span>
                                                </button>
                                                <button
                                                    className="action-btn delete"
                                                    title="Delete Job Requisition"
                                                    onClick={() => handleDeleteJob(job.job_id || job.id)}
                                                >
                                                    <Trash2 size={16} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                )) : (
                                    <tr>
                                        <td colSpan="6" style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-muted)' }}>
                                            {isLoadingJobs ? (
                                                <Loader2 className="animate-spin" style={{ margin: '0 auto' }} />
                                            ) : (
                                                <div>
                                                    <Briefcase size={36} style={{ color: 'var(--text-muted)', margin: '0 auto 10px' }} />
                                                    <p style={{ fontWeight: 500, fontSize: '0.95rem' }}>No Job Requisitions found</p>
                                                    <p style={{ fontSize: '0.8rem', marginTop: '4px' }}>
                                                        Click "+ Create Job" above to define an approved job requisition for your recruiters.
                                                    </p>
                                                </div>
                                            )}
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* ════════════════════════════════════════════════════════════════════
               TAB 2: USER MANAGEMENT
               ════════════════════════════════════════════════════════════════════ */}
            {activeTab === 'users' && (
                <div>
                    <div className="admin-header">
                        <div>
                            <h2>User Management</h2>
                            <p className="text-muted">Manage platform access, recruiter credentials, and security roles</p>
                        </div>
                        <button className="process-btn" onClick={() => {
                            setIsAddingUser(true);
                            setUserError('');
                        }}>
                            <UserPlus size={20} />
                            <span>Add New User</span>
                        </button>
                    </div>

                    <div className="admin-actions-bar" style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', background: '#fff', padding: '1rem', borderRadius: '16px', border: '1px solid var(--glass-border)', boxShadow: '0 4px 20px rgba(0, 0, 0, 0.03)' }}>
                        <form onSubmit={handleSearchUser} style={{ display: 'flex', flex: 1, gap: '1rem' }}>
                            <div className="input-with-icon" style={{ flex: 1 }}>
                                <Search size={18} className="input-icon" />
                                <input
                                    type="text"
                                    placeholder="Search user by email..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    style={{ width: '100%', padding: '0.6rem 1rem 0.6rem 2.5rem', borderRadius: '8px', border: '1px solid var(--glass-border)', outline: 'none' }}
                                />
                            </div>
                            <button
                                type="submit"
                                className="process-btn"
                                style={{ padding: '0.6rem 1.25rem', fontSize: '0.85rem' }}
                                disabled={isLoadingUsers || !searchTerm}
                            >
                                {isLoadingUsers ? <Loader2 className="animate-spin" size={16} /> : 'Search'}
                            </button>
                            <button
                                type="button"
                                className="action-btn-secondary"
                                onClick={loadActiveUsers}
                                disabled={isLoadingUsers}
                                style={{ padding: '0.6rem 1.25rem', fontSize: '0.85rem', whiteSpace: 'nowrap', border: '1px solid var(--glass-border)', background: 'white', borderRadius: '8px', cursor: 'pointer' }}
                            >
                                {isLoadingUsers ? <Loader2 className="animate-spin" size={16} /> : 'Get Active Users'}
                            </button>
                        </form>
                    </div>

                    {userError && <div className="error-message" style={{ marginBottom: '1.5rem' }}>{userError}</div>}

                    <div className="user-table-container glass">
                        <table className="admin-table">
                            <thead>
                                <tr>
                                    <th>User</th>
                                    <th>Role</th>
                                    <th>Status</th>
                                    <th style={{ textAlign: 'right' }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {users.length > 0 ? users.map((user) => (
                                    <tr key={user.email} className="animate-fade-in">
                                        <td>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                                <div className="avatar" style={{ width: '32px', height: '32px', fontSize: '0.8rem' }}>
                                                    {user.user_name?.charAt(0).toUpperCase() || 'U'}
                                                </div>
                                                <div>
                                                    <div style={{ fontWeight: 600 }}>{user.user_name}</div>
                                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{user.email}</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td>
                                            <select 
                                                className={`role-badge ${user.user_role}`}
                                                value={user.user_role}
                                                onChange={(e) => handleUpdateRole(user.email, e.target.value)}
                                                style={{
                                                    border: 'none',
                                                    outline: 'none',
                                                    cursor: 'pointer',
                                                    fontWeight: 600,
                                                    padding: '4px 8px',
                                                    borderRadius: '99px'
                                                }}
                                            >
                                                <option value="user">recruiter (user)</option>
                                                <option value="admin">admin</option>
                                            </select>
                                        </td>
                                        <td>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                                                <div style={{ 
                                                    width: '8px', 
                                                    height: '8px', 
                                                    borderRadius: '50%', 
                                                    background: user.is_active ? 'var(--success)' : 'var(--error)' 
                                                }}></div>
                                                <select
                                                    value={user.is_active ? 'active' : 'inactive'}
                                                    onChange={(e) => handleUpdateStatus(user.email, e.target.value)}
                                                    style={{
                                                        background: 'none',
                                                        border: 'none',
                                                        outline: 'none',
                                                        cursor: 'pointer',
                                                        fontWeight: 500,
                                                        color: user.is_active ? 'var(--success)' : 'var(--error)',
                                                        padding: '2px 4px'
                                                    }}
                                                >
                                                    <option value="active">Active</option>
                                                    <option value="inactive">Inactive</option>
                                                </select>
                                            </div>
                                        </td>
                                        <td style={{ textAlign: 'right' }}>
                                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                                                <button className="action-btn" title="Reset Password" onClick={() => handleResetPassword(user.email)}>
                                                    <Key size={18} />
                                                </button>
                                                <button className="action-btn delete" title="Delete User" onClick={() => handleDeleteUser(user.email)}>
                                                    <Trash2 size={18} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                )) : (
                                    <tr>
                                        <td colSpan="4" style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-muted)' }}>
                                            {isLoadingUsers ? <Loader2 className="animate-spin" style={{ margin: '0 auto' }} /> : 'Search for a user or click "Get Active Users" to manage accounts'}
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* ════════════════════════════════════════════════════════════════════
               MODAL: CREATE JOB REQUISITION (ADMIN ONLY)
               ════════════════════════════════════════════════════════════════════ */}
            {isAddingJob && (
                <div className="modal-overlay" onClick={() => setIsAddingJob(false)}>
                    <div className="modal-content animate-scale-in" onClick={e => e.stopPropagation()} style={{ maxWidth: '620px' }}>
                        <div className="modal-header">
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <Briefcase size={20} color="var(--brand-primary)" />
                                <h3>Create New Job</h3>
                            </div>
                            <button className="action-btn" onClick={() => setIsAddingJob(false)}>
                                <X size={18} />
                            </button>
                        </div>
                        <form onSubmit={handleCreateJob}>
                            <div className="modal-body" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
                                {jobError && <div className="error-message" style={{ marginBottom: '1rem', padding: '0.75rem' }}>{jobError}</div>}
                                
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                                    <div className="input-group">
                                        <label>Job Title / Position *</label>
                                        <input
                                            type="text"
                                            required
                                            value={newJob.title}
                                            onChange={e => setNewJob({ ...newJob, title: e.target.value })}
                                            placeholder="e.g. Senior Fullstack Python Developer"
                                        />
                                    </div>

                                    <div className="input-group">
                                        <label>Client / Company Name *</label>
                                        <div className="input-with-icon">
                                            <Building2 className="input-icon" size={18} />
                                            <input
                                                type="text"
                                                required
                                                value={newJob.client_name}
                                                onChange={e => setNewJob({ ...newJob, client_name: e.target.value })}
                                                placeholder="e.g. Estuate Technologies"
                                            />
                                        </div>
                                    </div>
                                </div>

                                <div className="input-group" style={{ marginBottom: '1rem' }}>
                                    <label>Min Experience (Years)</label>
                                    <input
                                        type="number"
                                        min="0"
                                        max="30"
                                        value={newJob.min_experience}
                                        onChange={e => setNewJob({ ...newJob, min_experience: parseInt(e.target.value) || 0 })}
                                        placeholder="e.g. 3"
                                    />
                                </div>

                                <div className="input-group">
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                                        <label style={{ margin: 0 }}>Official Job Description (JD) *</label>
                                        <button
                                            type="button"
                                            disabled={isReadingJdFile}
                                            onClick={() => document.getElementById('admin-jd-file').click()}
                                            style={{
                                                background: 'none',
                                                border: 'none',
                                                color: isReadingJdFile ? 'var(--text-muted)' : 'var(--brand-primary)',
                                                fontSize: '0.78rem',
                                                fontWeight: 600,
                                                cursor: isReadingJdFile ? 'not-allowed' : 'pointer',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '4px'
                                            }}
                                        >
                                            {isReadingJdFile ? <Loader2 size={13} className="animate-spin" /> : <FileText size={13} />}
                                            {isReadingJdFile ? 'Extracting JD text...' : 'Import from Text File'}
                                        </button>
                                        <input
                                            type="file"
                                            id="admin-jd-file"
                                            accept=".txt,.md,.pdf,.doc,.docx"
                                            hidden
                                            onChange={handleImportJdFile}
                                        />
                                    </div>
                                    <textarea
                                        required
                                        rows={7}
                                        value={newJob.jd_text}
                                        onChange={e => setNewJob({ ...newJob, jd_text: e.target.value })}
                                        placeholder="Paste the complete Job Description here... Recruiter batches will be screened against this description."
                                        style={{
                                            width: '100%',
                                            padding: '0.75rem',
                                            borderRadius: '8px',
                                            border: '1px solid var(--glass-border)',
                                            fontSize: '0.85rem',
                                            lineHeight: 1.4,
                                            resize: 'vertical'
                                        }}
                                    />
                                    <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                                        This JD is configured once by the Admin. Recruiters will only need to select this Job ID.
                                    </p>
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="cancel-btn" onClick={() => setIsAddingJob(false)}>
                                    Cancel
                                </button>
                                <button type="submit" className="process-btn">
                                    Create Job
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* ════════════════════════════════════════════════════════════════════
               MODAL: VIEW FULL JOB DESCRIPTION
               ════════════════════════════════════════════════════════════════════ */}
            {viewingJdJob && (
                <div className="modal-overlay" onClick={() => setViewingJdJob(null)}>
                    <div className="modal-content animate-scale-in" onClick={e => e.stopPropagation()} style={{ maxWidth: '650px' }}>
                        <div className="modal-header">
                            <div>
                                <h3 style={{ marginTop: '2px' }}>{viewingJdJob.title || viewingJdJob.position || viewingJdJob.job_name}</h3>
                                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                    Client: {viewingJdJob.client_name} &bull; Min Experience: {viewingJdJob.min_experience !== undefined ? viewingJdJob.min_experience : (viewingJdJob.experience || 0)}+ Years
                                </p>
                            </div>
                            <button className="action-btn" onClick={() => setViewingJdJob(null)}>
                                <X size={18} />
                            </button>
                        </div>
                        <div className="modal-body" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
                            <div style={{
                                background: '#f7f8fa',
                                padding: '16px',
                                borderRadius: '8px',
                                border: '1px solid var(--glass-border)',
                                fontSize: '0.85rem',
                                whiteSpace: 'pre-wrap',
                                lineHeight: 1.6,
                                color: 'var(--text-secondary)'
                            }}>
                                {viewingJdJob.jd_text || 'No description provided.'}
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button type="button" className="process-btn" onClick={() => setViewingJdJob(null)}>
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* ════════════════════════════════════════════════════════════════════
               MODAL: ADD NEW USER
               ════════════════════════════════════════════════════════════════════ */}
            {isAddingUser && (
                <div className="modal-overlay" onClick={() => setIsAddingUser(false)}>
                    <div className="modal-content animate-scale-in" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>Add New User</h3>
                            <button className="action-btn" onClick={() => {
                                setIsAddingUser(false);
                                setUserError('');
                            }}><X size={18} /></button>
                        </div>
                        <form onSubmit={handleCreateUser}>
                            <div className="modal-body">
                                {userError && <div className="error-message" style={{ marginBottom: '1rem', padding: '0.75rem' }}>{userError}</div>}
                                <div className="input-group">
                                    <label>Full Name</label>
                                    <div className="input-with-icon">
                                        <UserIcon className="input-icon" size={18} />
                                        <input
                                            type="text"
                                            required
                                            value={newUser.user_name}
                                            onChange={e => setNewUser({ ...newUser, user_name: e.target.value })}
                                            placeholder="John Doe"
                                        />
                                    </div>
                                </div>
                                <div className="input-group">
                                    <label>Email Address</label>
                                    <div className="input-with-icon">
                                        <Mail className="input-icon" size={18} />
                                        <input
                                            type="email"
                                            required
                                            value={newUser.email}
                                            onChange={e => setNewUser({ ...newUser, email: e.target.value })}
                                            placeholder="john@example.com"
                                        />
                                    </div>
                                </div>
                                <div className="input-group">
                                    <label>Role</label>
                                    <div className="input-with-icon">
                                        <Shield className="input-icon" size={18} />
                                        <select
                                            style={{
                                                width: '100%',
                                                padding: '0.875rem 1rem 0.875rem 3rem',
                                                background: '#f7f8fa',
                                                border: '1px solid #e2e5ea',
                                                borderRadius: '8px',
                                                color: '#1a1a2e',
                                                appearance: 'none',
                                                outline: 'none'
                                            }}
                                            value={newUser.user_role}
                                            onChange={e => setNewUser({ ...newUser, user_role: e.target.value })}
                                        >
                                            <option value="user">Recruiter (Standard User)</option>
                                            <option value="admin">Administrator (Can create Job IDs)</option>
                                        </select>
                                    </div>
                                </div>
                                <div className="input-group">
                                    <label>Initial Password</label>
                                    <div className="input-with-icon">
                                        <Lock className="input-icon" size={18} />
                                        <input
                                            type="password"
                                            required
                                            value={newUser.password}
                                            onChange={e => setNewUser({ ...newUser, password: e.target.value })}
                                            placeholder="••••••••"
                                        />
                                    </div>
                                    <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                                        Min 12 characters, including uppercase, number, and special character.
                                    </p>
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="cancel-btn" onClick={() => {
                                    setIsAddingUser(false);
                                    setUserError('');
                                }}>Cancel</button>
                                <button type="submit" className="process-btn">Create User</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AdminPanel;
