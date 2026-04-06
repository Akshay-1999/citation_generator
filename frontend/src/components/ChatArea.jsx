import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, Folder, Loader2, Database, FileText, Trash2, X } from 'lucide-react';
import MessageBubble from './MessageBubble';

const ChatArea = ({ messages, isTyping, onSendMessage, onAttachFile, onOpenFolderModal, onOpenFileSelection, selectedFiles = [], onRemoveFile }) => {
    const [input, setInput] = useState('');
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isTyping]);

    const handleSend = () => {
        if (input.trim()) {
            onSendMessage(input);
            setInput('');
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="chat-area">
            <div className="messages-container">
                {messages.length === 0 ? (
                    <div className="welcome-screen">
                        <div className="welcome-icon">📝</div>
                        <h2>Recruitment Assistant</h2>
                        <p>Start a new chat to begin screening candidates or answering recruitment queries.</p>
                    </div>
                ) : (
                    messages.map((msg, idx) => (
                        <MessageBubble
                            key={idx}
                            role={msg.role}
                            content={msg.content}
                            citations={msg.citations}
                            attachments={msg.attachments}
                        />
                    ))
                )}
                {isTyping && (
                    <div className="message-bubble-wrapper assistant">
                        <div className="message-bubble assistant glass typing">
                            <Loader2 className="animate-spin" size={18} />
                            <span>Thinking...</span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <div className="input-container glass">
                {selectedFiles.length > 0 && (
                    <div className="attachments-bar">
                        {selectedFiles.map((file) => (
                            <div key={file.file_id} className="attachment-item glass">
                                <FileText size={14} />
                                <span className="attachment-name">{file.filename}</span>
                                <button 
                                    className="remove-attachment-btn" 
                                    onClick={() => onRemoveFile(file.file_id)}
                                    title="Delete File"
                                >
                                    <Trash2 size={12} />
                                </button>
                            </div>
                        ))}
                    </div>
                )}
                <div className="input-wrapper">
                    <button className="icon-btn" onClick={onAttachFile} title="Upload File">
                        <Paperclip size={20} />
                    </button>
                    <button className="icon-btn" onClick={onOpenFolderModal} title="Process Folder">
                        <Folder size={20} />
                    </button>
                    <button className="icon-btn" onClick={onOpenFileSelection} title="File Context">
                        <Database size={20} />
                    </button>
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Message Recruitment Assistant..."
                        rows={1}
                        style={{ height: 'auto' }}
                    />
                    <button
                        className={`send-btn ${input.trim() ? 'active' : ''}`}
                        onClick={handleSend}
                        disabled={!input.trim()}
                    >
                        <Send size={18} />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ChatArea;
