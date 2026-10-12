export const BASE_URL = import.meta.env.VITE_API_URL || '';

const handleResponse = async (res, defaultError = 'Request failed') => {
    if (res.ok) return res.json();
    let errorMessage = defaultError;
    try {
        const data = await res.json();
        errorMessage = data.detail || defaultError;
    } catch (e) {
        // Fallback if response is not JSON
    }
    throw new Error(errorMessage);
};

export const api = {
    // Auth & Session
    fetchUserName: async () => {
        const res = await fetch(`${BASE_URL}/user/user_name`, { credentials: 'include' });
        return handleResponse(res, 'Unauthorized');
    },

    fetchSession: async () => {
        const res = await fetch(`${BASE_URL}/user/session`, { credentials: 'include' });
        return handleResponse(res, 'Failed to fetch session');
    },

    logout: async () => {
        const res = await fetch(`${BASE_URL}/auth/logout`, { method: 'POST', credentials: 'include' });
        return handleResponse(res, 'Logout failed');
    },

    // Threads & Chat
    fetchThreads: async () => {
        const res = await fetch(`${BASE_URL}/chat/threads`, { credentials: 'include' });
        return handleResponse(res, 'Failed to fetch threads');
    },

    fetchHistory: async (threadId) => {
        const res = await fetch(`${BASE_URL}/chat/history/${threadId}`, { credentials: 'include' });
        return handleResponse(res, 'Failed to fetch history');
    },

    sendMessage: async (query, history, threadId, fileNames = [], fileContext = []) => {
        const res = await fetch(`${BASE_URL}/chat/query`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query,
                history,
                thread_id: threadId,
                file_names: fileNames,
                file_context: fileContext
            }),
        });
        return handleResponse(res, 'Failed to send message');
    },

    // Files & Folder Processing
    uploadFile: async (file) => {
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch(`${BASE_URL}/file/upload`, {
            method: 'POST',
            credentials: 'include',
            body: formData,
        });
        return handleResponse(res, 'Upload failed');
    },

    listFiles: async () => {
        const res = await fetch(`${BASE_URL}/file/list_files`, { credentials: 'include' });
        return handleResponse(res, 'Failed to fetch files');
    },

    deleteFile: async (fileId) => {
        const res = await fetch(`${BASE_URL}/file/delete_file/${fileId}`, {
            method: 'PUT',
            credentials: 'include',
        });
        return handleResponse(res, 'Failed to delete file');
    },

    deleteReport: async (batchId) => {
        const res = await fetch(`${BASE_URL}/folder/delete_report/${batchId}`, {
            method: 'PUT',
            credentials: 'include',
        });
        return handleResponse(res, 'Failed to delete report');
    },

    processFolder: async (files, jd, jdFile, jobId = null, batchName = null, extraMetadata = {}) => {
        const formData = new FormData();
        formData.append('job_description', jd || '');
        if (jdFile) {
            formData.append('jd_file', jdFile);
        }
        if (jobId) {
            formData.append('job_id', jobId);
        }
        if (batchName) {
            formData.append('batch_name', batchName);
        }

        // Client Name
        const clientName = extraMetadata.client_name || extraMetadata.client || '';
        formData.append('client_name', clientName);

        // Total years of experience
        const exp = extraMetadata.experience !== undefined && extraMetadata.experience !== null
            ? extraMetadata.experience
            : (extraMetadata.total_experience !== undefined ? extraMetadata.total_experience : (extraMetadata.min_experience !== undefined ? extraMetadata.min_experience : 0));
        formData.append('experience', String(exp));
        formData.append('total_experience', String(exp));
        formData.append('total_year_of_experience', String(exp));

        // Report Name
        const reportName = extraMetadata.report_name || batchName || (clientName ? `${clientName}_Report` : 'Screening_Report');
        formData.append('report_name', reportName);

        // Position / Title
        if (extraMetadata.position || extraMetadata.title) {
            formData.append('position', extraMetadata.position || extraMetadata.title);
        }

        for (const file of files) {
            formData.append('files', file);
        }
        const res = await fetch(`${BASE_URL}/folder/process_folder`, {
            method: 'POST',
            credentials: 'include',
            body: formData,
        });
        return handleResponse(res, 'Processing failed');
    },

    // Admin / User Management
    createUser: async (userData) => {
        const res = await fetch(`${BASE_URL}/user/create_user`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData),
        });
        return handleResponse(res, 'Failed to create user');
    },

    deleteUser: async (email) => {
        const res = await fetch(`${BASE_URL}/user/delete_user/${encodeURIComponent(email)}`, {
            method: 'DELETE',
            credentials: 'include',
        });
        return handleResponse(res, 'Failed to delete user');
    },

    getUser: async (email) => {
        const res = await fetch(`${BASE_URL}/user/get_user/${encodeURIComponent(email)}`, { credentials: 'include' });
        return handleResponse(res, 'User not found');
    },

    updatePassword: async (email, newPassword) => {
        const res = await fetch(`${BASE_URL}/user/update_password/${email}?new_password=${encodeURIComponent(newPassword)}`, {
            method: 'PUT',
            credentials: 'include',
        });
        return handleResponse(res, 'Failed to update password');
    },

    updateRole: async (email, role) => {
        const res = await fetch(`${BASE_URL}/user/update_role/${encodeURIComponent(email)}?role=${role}`, {
            method: 'PUT',
            credentials: 'include',
        });
        return handleResponse(res, 'Failed to update role');
    },

    updateActiveStatus: async (email, isActive) => {
        const res = await fetch(`${BASE_URL}/user/update_active_status/${encodeURIComponent(email)}?is_active=${isActive}`, {
            method: 'PUT',
            credentials: 'include',
        });
        return handleResponse(res, 'Failed to update status');
    },

    fetchActiveUsers: async () => {
        const res = await fetch(`${BASE_URL}/user/get_active_users`, { credentials: 'include' });
        return handleResponse(res, 'Failed to fetch active users');
    },

    deleteThread: async (threadId) => {
        const res = await fetch(`${BASE_URL}/chat/delete/${threadId}`, {
            method: 'DELETE',
            credentials: 'include',
        });
        return handleResponse(res, 'Failed to delete thread');
    },

    renameThread: async (threadId, threadTitle) => {
        const res = await fetch(`${BASE_URL}/chat/rename/${threadId}`, {
            method: 'PUT',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ thread_title: threadTitle }),
        });
        return handleResponse(res, 'Failed to rename thread');
    },

    // Report History
    fetchReports: async () => {
        const res = await fetch(`${BASE_URL}/folder/list_reports`, { credentials: 'include' });
        return handleResponse(res, 'Failed to fetch reports');
    },

    fetchReportResults: async (batchId) => {
        const res = await fetch(`${BASE_URL}/folder/get_report_results/${batchId}`, { credentials: 'include' });
        return handleResponse(res, 'Failed to fetch report results');
    },

    convertResume: async (originalFile, candidateName) => {
        const res = await fetch(`${BASE_URL}/conversion/api/convert`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ original_file: originalFile, candidate_name: candidateName }),
        });
        return handleResponse(res, 'Failed to convert resume');
    },

    rejectResume: async (originalFile, feedback) => {
        const res = await fetch(`${BASE_URL}/conversion/api/reject`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ original_file: originalFile, feedback }),
        });
        return handleResponse(res, 'Failed to submit rejection feedback');
    },

    updateAndRegenerate: async (uuid, content) => {
        const res = await fetch(`${BASE_URL}/conversion/api/update_and_regenerate`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ uuid, content }),
        });
        return handleResponse(res, 'Failed to update and regenerate resume');
    },

    // Regular user / Recruiter: Active jobs for folder processing dropdown (Strictly from DB)
    fetchJobs: async () => {
        try {
            localStorage.removeItem('recai_jobs');
        } catch (e) {}

        try {
            let res = await fetch(`${BASE_URL}/job/all_jobs`, { credentials: 'include' });
            if (!res.ok) {
                res = await fetch(`${BASE_URL}/job/active_jobs`, { credentials: 'include' });
            }
            if (res.ok) {
                const data = await res.json();
                return Array.isArray(data) ? data : [];
            }
        } catch (e) {
            console.error('Error fetching jobs for user dropdown:', e);
        }
        return [];
    },

    // Admin Panel: Reads all jobs (active & inactive) strictly from DB
    fetchAdminJobs: async () => {
        try {
            localStorage.removeItem('recai_jobs');
        } catch (e) {}

        try {
            const res = await fetch(`${BASE_URL}/job/admin_jobs`, { credentials: 'include' });
            if (res.ok) {
                const data = await res.json();
                return Array.isArray(data) ? data : [];
            }
        } catch (e) {
            console.error('Error fetching admin jobs:', e);
        }
        return [];
    },

    readAttachedFile: async (fileOrUrl) => {
        if (fileOrUrl instanceof File) {
            const formData = new FormData();
            formData.append('file', fileOrUrl);
            const res = await fetch(`${BASE_URL}/job/read_attached_file?job_description_url=${encodeURIComponent(fileOrUrl.name)}`, {
                method: 'POST',
                credentials: 'include',
                body: formData,
            });
            return handleResponse(res, 'Failed to read attached file');
        } else {
            const res = await fetch(`${BASE_URL}/job/read_attached_file?job_description_url=${encodeURIComponent(fileOrUrl)}`, {
                method: 'GET',
                credentials: 'include',
            });
            return handleResponse(res, 'Failed to read attached file');
        }
    },

    createJob: async (jobData) => {
        try {
            localStorage.removeItem('recai_jobs');
        } catch (e) {}

        const now = new Date().toISOString();
        const payload = {
            user_id: jobData.user_id || 'admin',
            job_name: jobData.title || jobData.job_name || jobData.job_code || 'Job Position',
            job_description: jobData.jd_text || jobData.job_description || '',
            job_status: typeof jobData.status === 'string' ? jobData.status : 'OPEN',
            job_created_at: jobData.created_at || now,
            job_updated_at: jobData.updated_at || now,
            // Additional contextual fields
            position: jobData.title || jobData.position || '',
            client_name: jobData.client_name || '',
            experience: String(jobData.min_experience || jobData.experience || 0),
            jd_text: jobData.jd_text || jobData.job_description || '',
            job_code: jobData.job_code || ''
        };

        const res = await fetch(`${BASE_URL}/job/create_job`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        const data = await handleResponse(res, 'Failed to create job');
        try {
            window.dispatchEvent(new CustomEvent('reports-updated', { detail: data }));
        } catch (e) {}
        return data;
    },

    deleteJob: async (jobId) => {
        try {
            localStorage.removeItem('recai_jobs');
        } catch (e) {}

        let res = await fetch(`${BASE_URL}/job/${encodeURIComponent(jobId)}`, {
            method: 'DELETE',
            credentials: 'include',
        });
        if (!res.ok) {
            res = await fetch(`${BASE_URL}/jobs/${encodeURIComponent(jobId)}`, {
                method: 'DELETE',
                credentials: 'include',
            });
        }
        const data = await handleResponse(res, 'Failed to delete job');
        try {
            window.dispatchEvent(new CustomEvent('reports-updated', { detail: { deletedJobId: jobId } }));
        } catch (e) {}
        return data;
    },

    updateJobStatus: async (jobId, status) => {
        try {
            localStorage.removeItem('recai_jobs');
        } catch (e) {}

        let res = await fetch(`${BASE_URL}/job/${encodeURIComponent(jobId)}/status?status=${encodeURIComponent(status)}`, {
            method: 'PUT',
            credentials: 'include',
        });
        if (!res.ok) {
            res = await fetch(`${BASE_URL}/jobs/${encodeURIComponent(jobId)}/status?status=${encodeURIComponent(status)}`, {
                method: 'PUT',
                credentials: 'include',
            });
        }
        const data = await handleResponse(res, 'Failed to update job status');
        try {
            window.dispatchEvent(new CustomEvent('reports-updated', { detail: { jobId, status } }));
        } catch (e) {}
        return data;
    }
};

