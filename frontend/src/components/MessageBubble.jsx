import React from 'react';
import ReactMarkdown from 'react-markdown';
import { FileText, Link, CheckCircle, AlertCircle } from 'lucide-react';
import DOMPurify from 'dompurify';

const MessageBubble = ({ role, content, citations, attachments = [] }) => {
    const isAssistant = role === 'assistant';

    // Handle both new attachments array and legacy file-name patterns
    const getCleanContent = () => {
        if (!content) return '';
        // If it's a user message, remove the legacy file-name strings
        if (!isAssistant) {
            return content.split('\n').filter(line => !line.includes('file-name :')).join('\n');
        }
        return content;
    };

    return (
        <div className={`message-bubble-wrapper ${role}`}>
            <div className={`message-bubble ${role} glass`}>
                {isAssistant ? (
                    <div className="markdown-content">
                        <ReactMarkdown>{getCleanContent()}</ReactMarkdown>
                    </div>
                ) : (
                    <p className="user-text">{getCleanContent()}</p>
                )}

                {attachments && attachments.length > 0 && (
                    <div className="message-attachments">
                        {attachments.map((file, idx) => (
                            <div key={idx} className="message-attachment-badge">
                                <FileText size={12} />
                                <span>{file.filename}</span>
                            </div>
                        ))}
                    </div>
                ) || (
                    // Fallback for legacy messages: extract file names if they exist in content
                    !isAssistant && content && content.includes('file-name :') && (
                        <div className="message-attachments">
                            {content.split('\n')
                                .filter(line => line.includes('file-name :'))
                                .map((line, idx) => {
                                    const fileName = line.replace('file-name :', '').trim();
                                    return (
                                        <div key={idx} className="message-attachment-badge">
                                            <FileText size={12} />
                                            <span>{fileName}</span>
                                        </div>
                                    );
                                })
                            }
                        </div>
                    )
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
