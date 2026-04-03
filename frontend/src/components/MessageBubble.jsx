import React from 'react';
import ReactMarkdown from 'react-markdown';
import { FileText, Link, CheckCircle, AlertCircle } from 'lucide-react';
import DOMPurify from 'dompurify';

const MessageBubble = ({ role, content, citations }) => {
    const isAssistant = role === 'assistant';

    return (
        <div className={`message-bubble-wrapper ${role}`}>
            <div className={`message-bubble ${role} glass`}>
                {isAssistant ? (
                    <div className="markdown-content">
                        <ReactMarkdown>{content}</ReactMarkdown>
                    </div>
                ) : (
                    <p className="user-text">{content}</p>
                )}

                {isAssistant && citations && citations.length > 0 && (
                    <div className="citations-section">
                        <details>
                            <summary>
                                <Link size={14} />
                                <span>{citations.length} Sources</span>
                            </summary>
                            <div className="citations-list">
                                {citations.map((match, idx) => (
                                    <div key={idx} className="citation-card">
                                        <span className="citation-source">📄 {match.metadata?.file_name || 'Source'}</span>
                                        <p className="citation-text">"{match.page_content?.substring(0, 150)}..."</p>
                                    </div>
                                ))}
                            </div>
                        </details>
                    </div>
                )}
            </div>
        </div>
    );
};

export default MessageBubble;
