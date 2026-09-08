import React, { useState, useEffect, useRef } from 'react';
import { Video, Square, Play, CheckCircle2, ArrowRight, Clock, AlertCircle } from 'lucide-react';

export const InterviewRecording = ({ onNext, mediaRecorder, sessionHook }) => {
  const { stream, isRecording, recordedBlob, recordingDuration, startRecording, stopRecording } = mediaRecorder;
  const { questions, currentTurn, submitTurnVideo, isSubmittingTurn, submitInterview } = sessionHook;

  const [hasRecorded, setHasRecorded] = useState(false);
  const videoRef = useRef(null);

  const currentQuestion = questions[currentTurn - 1] || {
    turn_number: currentTurn,
    question_text: `Interview Question #${currentTurn}`
  };

  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  useEffect(() => {
    if (recordedBlob) {
      setHasRecorded(true);
    }
  }, [recordedBlob]);

  const handleStart = () => {
    setHasRecorded(false);
    startRecording();
  };

  const handleStop = () => {
    stopRecording();
  };

  const handleSubmitTurn = async () => {
    if (!recordedBlob) return;
    try {
      await submitTurnVideo(currentTurn, recordedBlob, recordingDuration);
      setHasRecorded(false);

      if (currentTurn >= questions.length) {
        await submitInterview();
        onNext(); // Move to completion
      }
    } catch (err) {
      console.error('Failed to submit turn:', err);
    }
  };

  const formatTime = (secs) => {
    const mins = Math.floor(secs / 60);
    const rem = secs % 60;
    return `${mins}:${rem < 10 ? '0' : ''}${rem}`;
  };

  return (
    <div className="portal-card">
      {/* Header with Turn Progress */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#ef4444', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Question {currentTurn} of {questions.length}
        </span>
        <div style={{ display: 'flex', gap: '6px' }}>
          {questions.map((q, idx) => (
            <div
              key={idx}
              style={{
                width: '28px',
                height: '6px',
                borderRadius: '3px',
                background: idx + 1 < currentTurn ? '#22c55e' : idx + 1 === currentTurn ? '#ef4444' : 'rgba(255, 255, 255, 0.2)'
              }}
            />
          ))}
        </div>
      </div>

      {/* Question Text Box */}
      <div style={{ background: 'rgba(255, 255, 255, 0.06)', padding: '1.25rem', borderRadius: '12px', marginBottom: '1.5rem', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
        <h3 style={{ fontSize: '1.15rem', lineHeight: '1.4', color: '#ffffff' }}>
          {currentQuestion.question_text}
        </h3>
      </div>

      {/* Video Recorder Box */}
      <div className="video-preview-box" style={{ marginBottom: '1.5rem' }}>
        <video ref={videoRef} autoPlay playsInline muted />
        {isRecording && (
          <div className="recording-indicator">
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#fff' }} />
            Recording ({formatTime(recordingDuration)})
          </div>
        )}
      </div>

      {/* Action Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          {!isRecording && !hasRecorded && (
            <button onClick={handleStart} className="portal-btn-primary">
              <Play size={16} /> Start Answering
            </button>
          )}

          {isRecording && (
            <button onClick={handleStop} className="portal-btn-primary" style={{ background: '#b91c1c' }}>
              <Square size={16} /> Stop Recording
            </button>
          )}

          {hasRecorded && !isRecording && (
            <button onClick={handleStart} className="portal-btn-secondary" style={{ marginRight: '10px' }}>
              Retake Answer
            </button>
          )}
        </div>

        {hasRecorded && !isRecording && (
          <button
            onClick={handleSubmitTurn}
            className="portal-btn-primary"
            disabled={isSubmittingTurn}
          >
            {isSubmittingTurn
              ? 'Uploading...'
              : currentTurn === questions.length
              ? 'Submit Final Interview'
              : 'Next Question'}
            <ArrowRight size={16} />
          </button>
        )}
      </div>
    </div>
  );
};

export default InterviewRecording;
