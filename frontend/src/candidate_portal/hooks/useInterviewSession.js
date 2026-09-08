import { useState, useEffect, useCallback } from 'react';

export const useInterviewSession = (token) => {
  const [session, setSession] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [currentTurn, setCurrentTurn] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isSubmittingTurn, setIsSubmittingTurn] = useState(false);

  // Validate Token & Load Session Information
  const validateSession = useCallback(async () => {
    if (!token) {
      setError('No interview token provided in URL');
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      // In full implementation, call: const res = await fetch(`/api/interview/candidate/${token}/validate`);
      // Mock / fallback response for structure
      const mockSession = {
        session_id: 'sess-12345',
        candidate_name: 'Candidate',
        job_position: 'Senior Software Engineer',
        status: 'STARTED',
        total_questions: 5
      };

      const mockQuestions = [
        { turn_number: 1, question_text: 'Can you introduce yourself and describe your technical background?' },
        { turn_number: 2, question_text: 'How do you design scalable backend architectures with PostgreSQL?' },
        { turn_number: 3, question_text: 'Describe a time you solved a difficult performance bottleneck.' },
        { turn_number: 4, question_text: 'How do you manage asynchronous worker queues and retry failures?' },
        { turn_number: 5, question_text: 'Why are you interested in this role and what are your career goals?' }
      ];

      setSession(mockSession);
      setQuestions(mockQuestions);
      setError(null);
    } catch (err) {
      console.error('Session validation error:', err);
      setError(err.message || 'Failed to validate interview token');
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    validateSession();
  }, [validateSession]);

  // Submit Turn Video Chunk
  const submitTurnVideo = async (turnNumber, videoBlob, duration) => {
    setIsSubmittingTurn(true);
    try {
      const formData = new FormData();
      formData.append('turn_number', turnNumber);
      formData.append('video_file', videoBlob, `turn_${turnNumber}.webm`);
      formData.append('duration', duration);

      // In full implementation:
      // await fetch(`/api/interview/candidate/${token}/turn`, { method: 'POST', body: formData });
      
      console.log(`Uploaded turn ${turnNumber} (${duration}s, size: ${videoBlob.size} bytes)`);
      if (currentTurn < questions.length) {
        setCurrentTurn((prev) => prev + 1);
      }
      return true;
    } catch (err) {
      console.error(`Error uploading turn ${turnNumber}:`, err);
      throw err;
    } finally {
      setIsSubmittingTurn(false);
    }
  };

  // Upload Identity Documents
  const uploadDocuments = async (idFile, selfieBlob) => {
    const formData = new FormData();
    formData.append('document_file', idFile);
    formData.append('selfie_file', selfieBlob, 'selfie.jpg');

    // In full implementation:
    // await fetch(`/api/interview/candidate/${token}/documents`, { method: 'POST', body: formData });
    console.log('Identity documents uploaded successfully');
    return true;
  };

  // Final Complete Submission
  const submitInterview = async () => {
    // In full implementation:
    // await fetch(`/api/interview/candidate/${token}/submit`, { method: 'POST' });
    console.log('Interview submitted for AI evaluation pipeline');
    return true;
  };

  return {
    session,
    questions,
    currentTurn,
    setCurrentTurn,
    isLoading,
    error,
    isSubmittingTurn,
    submitTurnVideo,
    uploadDocuments,
    submitInterview,
    refetchSession: validateSession
  };
};

export default useInterviewSession;
