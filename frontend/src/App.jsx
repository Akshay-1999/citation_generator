import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import FolderModal from './components/FolderModal';
import FileSelectionModal from './components/FileSelectionModal';
import Login from './components/Login';
import AdminPanel from './components/AdminPanel';
import { api } from './api';
import { Loader2 } from 'lucide-react';
import './App.css';

function Dashboard({ userName, userEmail, userRole, threads, activeThreadId, onNewChat, onSwitchThread, onRenameThread, onDeleteThread, messages, isTyping, handleSendMessage, isFolderModalOpen, setIsFolderModalOpen, isFileSelectionModalOpen, setIsFileSelectionModalOpen, selectedFiles, handleFileSelect, handleRemoveFile, handleProcessFolder, onLogout }) {
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
        onRemoveFile={handleRemoveFile}
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
        selectedFiles={selectedFiles}
      />

      <input
        type="file"
        id="file-input"
        hidden
        onChange={async (e) => {
          const file = e.target.files[0];
          if (file) {
            try {
              await api.uploadFile(file);
              alert('File uploaded successfully!');
            } catch (err) {
              alert('Upload failed: ' + err.message);
            }
          }
        }}
      />
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
    const userMsg = { role: 'user', content: query };
    setMessages((prev) => [...prev, userMsg]);
    setIsTyping(true);

    try {
      const data = await api.sendMessage(query, messages, activeThreadId);
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

  const handleProcessFolder = async (path, jd) => {
    try {
      const res = await api.processFolder(path, jd);
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
      }
    } catch (err) {
      alert(`Error processing folder: ${err.message}`);
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
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0f172a' }}>
        <Loader2 className="animate-spin" color="#3b82f6" size={48} />
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
              handleRemoveFile={handleRemoveFile}
              handleProcessFolder={handleProcessFolder}
              onLogout={handleLogout}
            />
          ) : <Navigate to="/login" replace />
        } />

        <Route path="*" element={<Navigate to={authStatus ? "/" : "/login"} replace />} />
      </Routes>
    </Router>
  );
}

export default App;
