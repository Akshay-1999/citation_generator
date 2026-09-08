import React, { useState } from 'react';
import './candidate_portal.css';
import useMediaRecorder from './hooks/useMediaRecorder';
import useInterviewSession from './hooks/useInterviewSession';

import WelcomeAndCheck from './steps/1_WelcomeAndCheck';
import IdVerification from './steps/2_IdVerification';
import InterviewRecording from './steps/3_InterviewRecording';
import CompletionScreen from './steps/4_CompletionScreen';

export const CandidateInterviewApp = () => {
  // Extract token from URL search query (e.g. ?token=...)
  const searchParams = new URLSearchParams(window.location.search);
  const token = searchParams.get('token') || 'demo_token';

  const [currentStep, setCurrentStep] = useState(1); // 1: Welcome/Check, 2: Verification, 3: Recording, 4: Done

  const mediaRecorder = useMediaRecorder();
  const sessionHook = useInterviewSession(token);

  const { session, isLoading, error } = sessionHook;

  if (isLoading) {
    return (
      <div className="candidate-portal-root" style={{ alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: '#94a3b8' }}>Validating interview session...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="candidate-portal-root" style={{ alignItems: 'center', justifyContent: 'center' }}>
        <div className="portal-card" style={{ textAlign: 'center', maxWidth: '480px' }}>
          <h3 style={{ color: '#ef4444', marginBottom: '10px' }}>Access Expired or Invalid</h3>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="candidate-portal-root">
      {/* Header */}
      <header className="portal-header">
        <div className="portal-logo">
          Rec<span>AI</span> Video Interview
        </div>
        <div className="portal-step-indicator">
          Step {currentStep} of 4 • {currentStep === 1 ? 'Readiness Check' : currentStep === 2 ? 'Identity Verification' : currentStep === 3 ? 'Live Recording' : 'Completed'}
        </div>
      </header>

      {/* Main Content Container */}
      <main className="portal-container">
        {currentStep === 1 && (
          <WelcomeAndCheck
            session={session}
            mediaRecorder={mediaRecorder}
            onNext={() => setCurrentStep(2)}
          />
        )}

        {currentStep === 2 && (
          <IdVerification
            sessionHook={sessionHook}
            mediaRecorder={mediaRecorder}
            onBack={() => setCurrentStep(1)}
            onNext={() => setCurrentStep(3)}
          />
        )}

        {currentStep === 3 && (
          <InterviewRecording
            sessionHook={sessionHook}
            mediaRecorder={mediaRecorder}
            onNext={() => setCurrentStep(4)}
          />
        )}

        {currentStep === 4 && (
          <CompletionScreen session={session} />
        )}
      </main>
    </div>
  );
};

export default CandidateInterviewApp;
