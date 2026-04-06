import React, { useState, useEffect } from 'react';
import { UserPlus, Search, Trash2, Key, Shield, User as UserIcon, Loader2, Mail, Lock } from 'lucide-react';
import { api } from '../api';

const AdminPanel = () => {
    const [users, setUsers] = useState([]);
    const [searchTerm, setSearchTerm] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [isAddingUser, setIsAddingUser] = useState(false);
    const [error, setError] = useState('');

    // New User State
    const [newUser, setNewUser] = useState({
        user_name: '',
        email: '',
        user_role: 'user',
        password: ''
    });

    useEffect(() => {
        fetchUsers();
    }, []);

    const fetchUsers = async () => {
        setIsLoading(true);
        try {
            // Since there is no "list all users" endpoint, we attempt to get the current one 
            // or we just handle the create/manage flow. 
            // For a real admin panel, we'd need a GET /user/list endpoint.
            // I will assume for now we only manage by searching specific emails as per userrouter.
            setUsers([]);
        } catch (err) {
            setError('Failed to load users');
        } finally {
            setIsLoading(false);
        }
    };

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!searchTerm) return;
        setIsLoading(true);
        try {
            const data = await api.getUser(searchTerm);
            setUsers([data]);
            setError('');
        } catch (err) {
            setError('User not found');
            setUsers([]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleCreateUser = async (e) => {
        e.preventDefault();
        setError('');
        try {
            await api.createUser(newUser);
            setIsAddingUser(false);
            setNewUser({ user_name: '', email: '', user_role: 'user', password: '' });
            alert('User created successfully!');
        } catch (err) {
            setError(err.message);
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
        const newPass = window.prompt(`Enter new password for ${email}:`);
        if (!newPass) return;
        try {
            await api.updatePassword(email, newPass);
            alert('Password updated successfully');
        } catch (err) {
            alert('Update failed: ' + err.message);
        }
    };

    return (
        <div className="admin-container animate-fade-in">
            <div className="admin-header">
                <div>
                    <h2>User Management</h2>
                    <p className="text-muted">Manage platform access and security roles</p>
                </div>
                <button className="process-btn" onClick={() => setIsAddingUser(true)}>
                    <UserPlus size={20} />
                    <span>Add New User</span>
                </button>
            </div>

            <div className="input-container" style={{ padding: '0 0 2rem 0' }}>
                <form onSubmit={handleSearch} className="input-wrapper" style={{ maxWidth: '500px' }}>
                    <Search size={20} className="text-muted" />
                    <input
                        type="text"
                        placeholder="Search user by email..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        style={{ background: 'none', border: 'none', color: 'white', flex: 1, padding: '0.5rem' }}
                    />
                    <button
                        type="submit"
                        className="process-btn"
                        style={{ padding: '0.4rem 1rem', fontSize: '0.85rem' }}
                        disabled={isLoading || !searchTerm}
                    >
                        {isLoading ? <Loader2 className="animate-spin" size={16} /> : 'Search'}
                    </button>
                </form>
            </div>

            {error && <div className="error-message" style={{ marginBottom: '1.5rem' }}>{error}</div>}

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
                                            {user.user_name?.charAt(0).toUpperCase()}
                                        </div>
                                        <div>
                                            <div style={{ fontWeight: 600 }}>{user.user_name}</div>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{user.email}</div>
                                        </div>
                                    </div>
                                </td>
                                <td>
                                    <span className={`role-badge ${user.user_role}`}>
                                        {user.user_role}
                                    </span>
                                </td>
                                <td>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                                        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success)' }}></div>
                                        Active
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
                                    {isLoading ? <Loader2 className="animate-spin" style={{ margin: '0 auto' }} /> : 'Search for a user to manage their account'}
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* Add User Modal */}
            {isAddingUser && (
                <div className="modal-overlay">
                    <div className="modal-content animate-scale-in">
                        <div className="modal-header">
                            <h3>Add New User</h3>
                            <button className="action-btn" onClick={() => setIsAddingUser(false)}>×</button>
                        </div>
                        <form onSubmit={handleCreateUser}>
                            <div className="modal-body">
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
                                                background: 'rgba(15, 23, 42, 0.6)',
                                                border: '1px solid var(--glass-border)',
                                                borderRadius: '12px',
                                                color: 'white',
                                                appearance: 'none',
                                                outline: 'none'
                                            }}
                                            value={newUser.user_role}
                                            onChange={e => setNewUser({ ...newUser, user_role: e.target.value })}
                                        >
                                            <option value="user">Standard User</option>
                                            <option value="admin">Administrator</option>
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
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="cancel-btn" onClick={() => setIsAddingUser(false)}>Cancel</button>
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
