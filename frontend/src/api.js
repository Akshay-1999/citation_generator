const BASE_URL = '';

export const api = {
    // Auth & Session
    fetchUserName: async () => {
        const res = await fetch(`${BASE_URL}/user/user_name`);
        if (!res.ok) throw new Error('Unauthorized');
        return res.json();
    },

    fetchSession: async () => {
        const res = await fetch(`${BASE_URL}/user/session`);
        if (!res.ok) throw new Error('Failed to fetch session');
        return res.json();
    },

    logout: async () => {
        const res = await fetch(`${BASE_URL}/auth/logout`, { method: 'POST' });
        if (!res.ok) throw new Error('Logout failed');
        return res.json();
    },

    // Threads & Chat
    fetchThreads: async () => {
        const res = await fetch(`${BASE_URL}/chat/threads`);
        if (!res.ok) throw new Error('Failed to fetch threads');
        return res.json();
    },

    fetchHistory: async (threadId) => {
        const res = await fetch(`${BASE_URL}/chat/history/${threadId}`);
        if (!res.ok) throw new Error('Failed to fetch history');
        return res.json();
    },

    sendMessage: async (query, history, threadId, fileNames = [], fileContext = []) => {
        const res = await fetch(`${BASE_URL}/chat/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                query, 
                history, 
                thread_id: threadId, 
                file_names: fileNames,
                file_context: fileContext 
            }),
        });
        if (!res.ok) throw new Error('Failed to send message');
        return res.json();
    },

    // Files & Folder Processing
    uploadFile: async (file) => {
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch(`${BASE_URL}/file/upload`, {
            method: 'POST',
            body: formData,
        });
        if (!res.ok) throw new Error('Upload failed');
        return res.json();
    },

    listFiles: async () => {
        const res = await fetch(`${BASE_URL}/file/list_files`);
        if (!res.ok) throw new Error('Failed to fetch files');
        return res.json();
    },

    deleteFile: async (fileId) => {
        const res = await fetch(`${BASE_URL}/file/delete_file/${fileId}`, {
            method: 'DELETE',
        });
        if (!res.ok) throw new Error('Failed to delete file');
        return res.json();
    },

    processFolder: async (path, jd) => {
        const res = await fetch(`${BASE_URL}/folder/process_folder`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ folder_path: path, job_description: jd }),
        });
        if (!res.ok) throw new Error('Processing failed');
        return res; // Return response for blob handling
    },

    // Admin / User Management
    createUser: async (userData) => {
        const res = await fetch(`${BASE_URL}/user/create_user`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Failed to create user' }));
            throw new Error(err.detail || 'Failed to create user');
        }
        return res.json();
    },

    deleteUser: async (email) => {
        const res = await fetch(`${BASE_URL}/user/delete_user/${encodeURIComponent(email)}`, {
            method: 'DELETE',
        });
        if (!res.ok) throw new Error('Failed to delete user');
        return res.json();
    },

    getUser: async (email) => {
        const res = await fetch(`${BASE_URL}/user/get_user/${encodeURIComponent(email)}`);
        if (!res.ok) throw new Error('User not found');
        return res.json();
    },

    updatePassword: async (email, newPassword) => {
        const res = await fetch(`${BASE_URL}/user/update_password/${email}?new_password=${encodeURIComponent(newPassword)}`, {
            method: 'PUT',
        });
        if (!res.ok) throw new Error('Failed to update password');
        return res.json();
    },

    deleteThread: async (threadId) => {
        const res = await fetch(`${BASE_URL}/chat/delete/${threadId}`, {
            method: 'DELETE',
        });
        if (!res.ok) throw new Error('Failed to delete thread');
        return res.json();
    },

    renameThread: async (threadId, threadTitle) => {
        const res = await fetch(`${BASE_URL}/chat/rename/${threadId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ thread_title: threadTitle }),
        });
        if (!res.ok) throw new Error('Failed to rename thread');
        return res.json();
    }
};
