import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Briefcase, Mail, Lock, Loader2, Brain, Target, FileText, Sparkles, Cpu, Award, TrendingUp, UserCheck, PieChart, Users, CheckCircle, Search } from 'lucide-react';
import { BASE_URL } from '../api';

const mosaicTiles = [
  { bg: 'rgba(196,18,48,0.95)', text: 'AI Screening', icon: Brain, size: 'tall', color: '#ffffff' },
  { bg: '#ffffff', text: 'Smart Matching', icon: Target, size: 'normal', color: '#1a1a2e' },
  { bg: '#C41230', text: '', icon: FileText, size: 'normal', color: '#ffffff' },
  { bg: 'rgba(31,41,55,0.9)', text: 'Resume Analysis', icon: Cpu, size: 'tall', color: '#ffffff' },
  { bg: 'rgba(196,18,48,0.7)', text: 'Candidate Insights', icon: Sparkles, size: 'normal', color: '#ffffff' },
  { bg: '#ffffff', text: 'Talent IQ', icon: Award, size: 'normal', color: '#C41230' },
  { bg: '#C41230', text: 'Simplified Hiring', icon: UserCheck, size: 'tall', color: '#ffffff' },
  { bg: '#1f2937', text: '', icon: Search, size: 'normal', color: '#ffffff' },
  { bg: 'rgba(196,18,48,0.4)', text: 'Data Analytics', icon: TrendingUp, size: 'normal', color: '#ffffff' },
  { bg: '#ffffff', text: 'ProfileIQ', icon: CheckCircle, size: 'normal', color: '#C41230' },
  { bg: '#C41230', text: '', icon: Users, size: 'tall', color: '#ffffff' },
  { bg: '#1f2937', text: 'Automated Reports', icon: PieChart, size: 'normal', color: '#ffffff' },
];

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

            {/* FULL-SCREEN BACKGROUND MOSAIC */}
            <div className="login-mosaic">
                <div className="mosaic-grid">
                    {mosaicTiles.map((tile, i) => {
                        const Icon = tile.icon;
                        return (
                            <div
                                key={i}
                                className={`mosaic-tile tile-${tile.size}`}
                                style={{ 
                                    background: tile.bg, 
                                    animationDelay: `${i * 0.08}s` 
                                }}
                            >
                                <Icon className="tile-icon" size={24} style={{ color: tile.color }} />
                                {tile.text && <span className="tile-label" style={{ color: tile.color }}>{tile.text}</span>}
                            </div>
                        );
                    })}
                </div>
                
                {/* Visual overlay for dark mask and copy readability */}
                <div className="mosaic-overlay-bg"></div>
            </div>

            {/* RESPONSIVE FLEX CONTENT LAYER */}
            <div className="login-content-layer">
                {/* LEFT BRANDING COPY */}
                <div className="login-left-copy">
                    <h2>Screen Smarter,<br/><span>Hire Better.</span></h2>
                    <p>AI-powered candidate analysis at your fingertips</p>
                </div>

                {/* FLOATING CARD CONTAINER */}
                <div className="login-floating-panel">
                    <div className="login-card">
                        <div className="login-header">
                            <div className="estuate-logo">ESTUATE</div>
                            <h1 className="login-subheader">ProfileIQ</h1>
                            <p>Sign in to continue to your dashboard</p>
                        </div>

                        <form onSubmit={handleLogin} className="login-form">
                            {error && <div className="error-message animate-shake">{error}</div>}

                            <div className="input-group slide-in-1">
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

                            <div className="input-group slide-in-2">
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

                            <button type="submit" className="login-btn slide-in-3" disabled={isSubmitting}>
                                {isSubmitting ? <Loader2 className="animate-spin" size={20} /> : 'Sign In'}
                            </button>
                        </form>

                        <div className="login-footer slide-in-4">
                            <p>&copy; 2026 ProfileIQ. All rights reserved.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Login;
