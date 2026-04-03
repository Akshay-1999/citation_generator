import React, { useState } from 'react';
import { MessageSquare, Plus, User, Briefcase, Shield, LogOut, Settings, ChevronUp } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

const ThreadItem = ({ thread, isActive, onSwitch, onRename, onDelete }) => {
    const [showMenu, setShowMenu] = useState(false);
    const [isEditing, setIsEditing] = useState(false);
    const [editValue, setEditValue] = useState(thread.title || 'New Chat');

    const handleRenameSubmit = (e) => {
        if (e.key === 'Enter') {
            onRename(thread.thread_id, editValue);
            setIsEditing(false);
        } else if (e.key === 'Escape') {
            setEditValue(thread.title || 'New Chat');
            setIsEditing(false);
        }
    };

    return (
        <div
            className={`history-item ${isActive ? 'active' : ''}`}
            onClick={() => !isEditing && onSwitch(thread.thread_id)}
            style={{ position: 'relative' }}
        >
            <MessageSquare size={16} />
            {isEditing ? (
                <input
                    autoFocus
                    className="rename-input"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onKeyDown={handleRenameSubmit}
                    onBlur={() => {
                        onRename(thread.thread_id, editValue);
                        setIsEditing(false);
                    }}
                    onClick={(e) => e.stopPropagation()}
                />
            ) : (
                <>
                    <span className="history-title">{thread.title || 'New Chat'}</span>
                    <div className="thread-actions" onClick={(e) => e.stopPropagation()}>
                        <button
                            className="thread-action-btn"
                            onClick={() => setShowMenu(!showMenu)}
                        >
                            <Settings size={14} />
                        </button>
                        {showMenu && (
                            <div className="thread-menu-dropdown animate-scale-in">
                                <button
                                    className="thread-menu-item"
                                    onClick={() => {
                                        setIsEditing(true);
                                        setShowMenu(false);
                                    }}
                                >
                                    <span>Rename</span>
                                </button>
                                <button
                                    className="thread-menu-item delete"
                                    onClick={() => {
                                        onDelete(thread.thread_id);
                                        setShowMenu(false);
                                    }}
                                >
                                    <span>Delete</span>
                                </button>
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    );
};

const Sidebar = ({ threads, activeThreadId, onNewChat, onSwitchThread, onRenameThread, onDeleteThread, userName, userEmail, userRole, onLogout }) => {
    const location = useLocation();
    const [showUserMenu, setShowUserMenu] = useState(false);

    return (
        <aside className="sidebar glass">
            <div className="sidebar-header">
                <Link to="/" className="logo" style={{ textDecoration: 'none', color: 'inherit' }}>
                    <Briefcase className="logo-icon" />
                    <span>Recruitment Assistant</span>
                </Link>
            </div>

            <button className="new-chat-btn" onClick={onNewChat}>
                <Plus size={18} />
                <span>New Chat</span>
            </button>

            <div className="history-section">
                <div className="section-label" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>Main</span>
                </div>
                <div className="history-list" style={{ marginBottom: '2rem' }}>
                    <Link
                        to="/"
                        className={`history-item ${location.pathname === '/' ? 'active' : ''}`}
                        style={{ textDecoration: 'none' }}
                    >
                        <MessageSquare size={16} />
                        <span className="history-title">Chat Dashboard</span>
                    </Link>

                    {userRole === 'admin' && (
                        <Link
                            to="/admin"
                            className={`history-item ${location.pathname === '/admin' ? 'active' : ''}`}
                            style={{ textDecoration: 'none' }}
                        >
                            <Shield size={16} />
                            <span className="history-title">Admin Panel</span>
                        </Link>
                    )}
                </div>

                <div className="section-label">Recent Chats</div>
                <div className="history-list">
                    {threads.length === 0 ? (
                        <div className="empty-history" style={{ padding: '0.75rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            No recent chats
                        </div>
                    ) : (
                        threads.map((thread) => (
                            <ThreadItem
                                key={thread.thread_id}
                                thread={thread}
                                isActive={activeThreadId === thread.thread_id}
                                onSwitch={onSwitchThread}
                                onRename={onRenameThread}
                                onDelete={onDeleteThread}
                            />
                        ))
                    )}
                </div>
            </div>

            <div className="sidebar-footer">
                {showUserMenu && (
                    <div className="user-menu-dropdown animate-scale-in">
                        <button className="menu-item" onClick={() => alert('Settings coming soon!')}>
                            <Settings size={16} />
                            <span>Settings</span>
                        </button>
                        <div className="menu-divider"></div>
                        <button className="menu-item logout" onClick={onLogout}>
                            <LogOut size={16} />
                            <span>Log Out</span>
                        </button>
                    </div>
                )}
                <div
                    className={`user-badge ${showUserMenu ? 'active' : ''}`}
                    onClick={() => setShowUserMenu(!showUserMenu)}
                >
                    <div className="avatar">{userName?.charAt(0).toUpperCase() || 'U'}</div>
                    <div className="user-info">
                        <span className="user-email">{userName || 'User'}</span>
                        <span className="user-role">{userRole === 'admin' ? 'Administrator' : 'Recruiter'}</span>
                    </div>
                    <ChevronUp size={16} className={`menu-chevron ${showUserMenu ? 'rotated' : ''}`} />
                </div>
            </div>
        </aside>
    );
};

export default Sidebar;
