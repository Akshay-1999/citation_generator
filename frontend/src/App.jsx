import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import FolderModal from './components/FolderModal';
import FileSelectionModal from './components/FileSelectionModal';
import Login from './components/Login';
import AdminPanel from './components/AdminPanel';
import { api } from './api';
import { Loader2, CheckCircle2 } from 'lucide-react';
import './App.css';

function Dashboard({ userName, userEmail, userRole, threads, activeThreadId, onNewChat, onSwitchThread, onRenameThread, onDeleteThread, messages, isTyping, handleSendMessage, isFolderModalOpen, setIsFolderModalOpen, isFileSelectionModalOpen, setIsFileSelectionModalOpen, selectedFiles, handleFileSelect, handleUnselectFile, handleRemoveFile, handleProcessFolder, onLogout, uploadProgress, setUploadProgress }) {
  return (
    <div className="app-container">
      <Sidebar
        threads={threads}
        activeThreadId={activeThreadId}
        onNewChat={onNewChat}
        onSwitchThread={onSwitchThread}
        onRenameThread={onRenameThread}
        onDeleteThread={onDeleteThread}
        userName={userName}
        userEmail={userEmail}
        userRole={userRole}
        onLogout={onLogout}
      />

      <ChatArea
        messages={messages}
        isTyping={isTyping}
        onSendMessage={handleSendMessage}
        onAttachFile={() => document.getElementById('file-input')?.click()}
        onOpenFolderModal={() => setIsFolderModalOpen(true)}
        onOpenFileSelection={() => setIsFileSelectionModalOpen(true)}
        selectedFiles={selectedFiles}
        onRemoveFile={handleUnselectFile}
      />

      <FolderModal
        isOpen={isFolderModalOpen}
        onClose={() => setIsFolderModalOpen(false)}
        onProcess={handleProcessFolder}
      />

      <FileSelectionModal
        isOpen={isFileSelectionModalOpen}
        onClose={() => setIsFileSelectionModalOpen(false)}
        onSelect={handleFileSelect}
        onDelete={handleRemoveFile}
        selectedFiles={selectedFiles}
      />

      <input
        type="file"
        id="file-input"
        hidden
        onChange={async (e) => {
          const file = e.target.files[0];
          if (file) {
            setUploadProgress({ active: true, message: `Uploading ${file.name}...`, status: 'uploading' });
            try {
              const result = await api.uploadFile(file);
              if (result && result.file_id) {
                handleFileSelect({
                  file_id: result.file_id,
                  filename: result.filename || file.name
                });
                setUploadProgress({ active: true, message: 'Upload Complete', status: 'success' });
                await new Promise(r => setTimeout(r, 2000));
              }
            } catch (err) {
              alert('Upload failed: ' + err.message);
            } finally {
              setUploadProgress({ active: false, message: '', status: 'uploading' });
              e.target.value = '';
            }
          }
        }}
      />
      {uploadProgress.active && (
        <div className={`upload-overlay ${uploadProgress.status}`}>
          <div className="icon-container">
            {uploadProgress.status === 'success' ? (
              <CheckCircle2 size={24} />
            ) : (
              <Loader2 className="animate-spin" size={20} />
            )}
          </div>
          <div className="text-container">
            <h2>{uploadProgress.message}</h2>
            {uploadProgress.status === 'uploading' && (
              <p className="status-text">Processing documents...</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function AdminLayout({ userName, userEmail, userRole, onLogout, children }) {
  if (userRole !== 'admin') return <Navigate to="/" replace />;

  return (
    <div className="app-container">
      <Sidebar
        threads={[]}
        activeThreadId={null}
        onNewChat={() => { }}
        onSwitchThread={() => { }}
        userName={userName}
        userEmail={userEmail}
        userRole={userRole}
        onLogout={onLogout}
      />
      {children}
    </div>
  );
}

function App() {
  const [authStatus, setAuthStatus] = useState(null); // null, true, false
  const [user, setUser] = useState({ username: '', email: '', role: '' });

  // Dashboard State (Moved up to share with Sidebar)
  const [threads, setThreads] = useState([]);
  const [activeThreadId, setActiveThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [isFolderModalOpen, setIsFolderModalOpen] = useState(false);
  const [isFileSelectionModalOpen, setIsFileSelectionModalOpen] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadProgress, setUploadProgress] = useState({ active: false, message: '', status: 'uploading' });

  // Load persisted files when user is authenticated
  useEffect(() => {
    if (user.email) {
      const savedFiles = localStorage.getItem(`selectedFiles_${user.email}`);
      if (savedFiles) {
        try {
          setSelectedFiles(JSON.parse(savedFiles));
        } catch (e) {
          console.error('Failed to parse saved files:', e);
        }
      }
    } else {
      setSelectedFiles([]);
    }
  }, [user.email]);

  // Persistent save to localStorage whenever selectedFiles or user.email changes
  useEffect(() => {
    if (user.email) {
      localStorage.setItem(`selectedFiles_${user.email}`, JSON.stringify(selectedFiles));
    }
  }, [selectedFiles, user.email]);

  const checkAuth = async () => {
    try {
      const session = await api.fetchSession();
      setUser({
        username: session.username || session.email.split('@')[0],
        email: session.email,
        role: session.role
      });
      setAuthStatus(true);

      // Pre-load threads if authenticated
      const threadList = await api.fetchThreads();
      setThreads(threadList);
    } catch (err) {
      setAuthStatus(false);
      setUser({ username: '', email: '', role: '' });
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const handleLogout = async () => {
    try {
      await api.logout();
      setAuthStatus(false);
      setUser({ username: '', email: '', role: '' });
      // Clear dashboard state
      setThreads([]);
      setActiveThreadId(null);
      setMessages([]);
      setSelectedFiles([]);
    } catch (err) {
      console.error('Logout failed:', err);
      setAuthStatus(false);
      setUser({ username: '', email: '', role: '' });
      setThreads([]);
      setActiveThreadId(null);
      setMessages([]);
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setActiveThreadId(null);
  };

  const handleSwitchThread = async (threadId) => {
    setIsTyping(true);
    setActiveThreadId(threadId);
    try {
      const history = await api.fetchHistory(threadId);
      setMessages(history);
    } catch (err) {
      console.error('Failed to switch thread:', err);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSendMessage = async (query) => {
    // We no longer append text to the content; instead, we store it separately for UI
    const userMsg = { 
      role: 'user', 
      content: query,
      attachments: [...selectedFiles] 
    };
    
    setMessages((prev) => [...prev, userMsg]);
    setIsTyping(true);

    try {
      const fileNames = selectedFiles.map(f => f.filename);
      // Pass the original query and the context separately
      const data = await api.sendMessage(query, messages, activeThreadId, fileNames, selectedFiles);
      const botOutput = data.response?.output || data.response || 'No response';
      const newThreadId = data.thread_id || data.response?.thread_id;

      if (newThreadId && !activeThreadId) {
        setActiveThreadId(newThreadId);
        setThreads(await api.fetchThreads());
      }
      setMessages((prev) => [...prev, { role: 'assistant', content: botOutput, citations: data.citations }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: `⚠️ Error: ${err.message}` }]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleProcessFolder = async (files, jd, jdFile) => {
    setUploadProgress({ active: true, message: `Uploading ${files.length} resumes...`, status: 'uploading' });
    try {
      const res = await api.processFolder(files, jd, jdFile);

      if (res.headers.get('content-type')?.includes('spreadsheetml')) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'screening_results.xlsx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        setUploadProgress({ active: true, message: 'Screening Complete', status: 'success' });
        await new Promise(r => setTimeout(r, 2500));
      } else {
        const data = await res.json();
        setUploadProgress({ active: true, message: data.message || 'Processing Complete', status: 'success' });
        await new Promise(r => setTimeout(r, 2500));
      }
    } catch (err) {
      alert(`Error processing: ${err.message}`);
    } finally {
      setUploadProgress({ active: false, message: '', status: 'uploading' });
    }
  };

  const handleDeleteThread = async (threadId) => {
    if (!window.confirm('Are you sure you want to delete this chat?')) return;
    try {
      await api.deleteThread(threadId);
      setThreads((prev) => prev.filter((t) => t.thread_id !== threadId));
      if (activeThreadId === threadId) {
        handleNewChat();
      }
    } catch (err) {
      alert('Failed to delete thread: ' + err.message);
    }
  };

  const handleRenameThread = async (threadId, newTitle) => {
    if (!newTitle.trim()) return;
    try {
      await api.renameThread(threadId, newTitle);
      setThreads((prev) =>
        prev.map((t) => (t.thread_id === threadId ? { ...t, title: newTitle } : t))
      );
    } catch (err) {
      alert('Failed to rename thread: ' + err.message);
    }
  };

  const handleFileSelect = (file) => {
    setSelectedFiles(prev => {
      const isAlreadySelected = prev.some(f => f.file_id === file.file_id);
      if (isAlreadySelected) {
        return prev.filter(f => f.file_id !== file.file_id);
      } else {
        return [...prev, file];
      }
    });
  };

  const handleUnselectFile = (fileId) => {
    setSelectedFiles(prev => prev.filter(f => f.file_id !== fileId));
  };

  const handleRemoveFile = async (fileId) => {
    if (window.confirm('Are you sure you want to permanently delete this file?')) {
      try {
        await api.deleteFile(fileId);
        setSelectedFiles(prev => prev.filter(f => f.file_id !== fileId));
      } catch (err) {
        alert('Failed to delete file: ' + err.message);
      }
    }
  };

  if (authStatus === null) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f7f8fa' }}>
        <Loader2 className="animate-spin" color="#C41230" size={48} />
      </div>
    );
  }

  return (
    <Router>
      <Routes>
        <Route path="/login" element={authStatus ? <Navigate to="/" replace /> : <Login onLoginSuccess={checkAuth} />} />

        <Route path="/admin" element={
          <AdminLayout userName={user.username} userEmail={user.email} userRole={user.role} onLogout={handleLogout}>
            <AdminPanel />
          </AdminLayout>
        } />

        <Route path="/" element={
          authStatus ? (
            <Dashboard
              userName={user.username}
              userEmail={user.email}
              userRole={user.role}
              threads={threads}
              activeThreadId={activeThreadId}
              onNewChat={handleNewChat}
              onSwitchThread={handleSwitchThread}
              onRenameThread={handleRenameThread}
              onDeleteThread={handleDeleteThread}
              messages={messages}
              isTyping={isTyping}
              handleSendMessage={handleSendMessage}
              isFolderModalOpen={isFolderModalOpen}
              setIsFolderModalOpen={setIsFolderModalOpen}
              isFileSelectionModalOpen={isFileSelectionModalOpen}
              setIsFileSelectionModalOpen={setIsFileSelectionModalOpen}
              selectedFiles={selectedFiles}
              handleFileSelect={handleFileSelect}
              handleUnselectFile={handleUnselectFile}
              handleRemoveFile={handleRemoveFile}
              handleProcessFolder={handleProcessFolder}
              onLogout={handleLogout}
              uploadProgress={uploadProgress}
              setUploadProgress={setUploadProgress}
            />
          ) : <Navigate to="/login" replace />
        } />

        <Route path="*" element={<Navigate to={authStatus ? "/" : "/login"} replace />} />
      </Routes>
    </Router>
  );
}

export default App;
