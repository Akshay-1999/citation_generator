import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Briefcase, Mail, Lock, Loader2 } from 'lucide-react';
import { BASE_URL } from '../api';

const Login = ({ onLoginSuccess }) => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const handleLogin = async (e) => {
        e.preventDefault();
        setIsSubmitting(true);
        setError('');

        try {
            const res = await fetch(`${BASE_URL}/auth/login`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
            });

            if (!res.ok) {
                const data = await res.json().catch(() => ({ detail: 'Login failed' }));
                const errorMsg = typeof data.detail === 'string'
                    ? data.detail
                    : JSON.stringify(data.detail) || 'Login failed';
                throw new Error(errorMsg);
            }

            if (onLoginSuccess) await onLoginSuccess();
            navigate('/');
        } catch (err) {
            setError(err.message);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="login-container">
            <div className="login-card glass">
                <div className="login-header">
                    <Briefcase size={32} className="logo-icon" />
                    <h1>Recruitment Assistant</h1>
                    <p>Sign in to continue to your dashboard</p>
                </div>

                <form onSubmit={handleLogin} className="login-form">
                    {error && <div className="error-message">{error}</div>}

                    <div className="input-group">
                        <label>Email Address</label>
                        <div className="input-with-icon">
                            <Mail className="input-icon" size={18} />
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="receptionist@estuate.com"
                                required
                            />
                        </div>
                    </div>

                    <div className="input-group">
                        <label>Password</label>
                        <div className="input-with-icon">
                            <Lock className="input-icon" size={18} />
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                            />
                        </div>
                    </div>

                    <button type="submit" className="login-btn" disabled={isSubmitting}>
                        {isSubmitting ? <Loader2 className="animate-spin" size={20} /> : 'Sign In'}
                    </button>
                </form>

                <div className="login-footer">
                    <p>&copy; 2026 Recruitment Assistant. All rights reserved.</p>
                </div>
            </div>
        </div>
    );
};

export default Login;
