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
            method: 'DELETE',
            credentials: 'include',
        });
        return handleResponse(res, 'Failed to delete file');
    },

    processFolder: async (files, jd, jdFile) => {
        const formData = new FormData();
        formData.append('job_description', jd);
        if (jdFile) {
            formData.append('jd_file', jdFile);
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
    }
};
