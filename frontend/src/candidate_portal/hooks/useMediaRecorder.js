import { useState, useRef, useCallback, useEffect } from 'react';

export const useMediaRecorder = () => {
  const [stream, setStream] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordedBlob, setRecordedBlob] = useState(null);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [hasPermissions, setHasPermissions] = useState(false);
  const [permissionError, setPermissionError] = useState(null);

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  // Request camera and microphone access
  const requestPermissions = useCallback(async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
        audio: { echoCancellation: true, noiseSuppression: true }
      });
      setStream(mediaStream);
      setHasPermissions(true);
      setPermissionError(null);
      return mediaStream;
    } catch (err) {
      console.error('Error requesting media permissions:', err);
      setPermissionError(err.message || 'Camera/Microphone access denied');
      setHasPermissions(false);
      throw err;
    }
  }, []);

  // Start recording video/audio
  const startRecording = useCallback(() => {
    if (!stream) {
      console.error('No media stream available to record');
      return;
    }

    chunksRef.current = [];
    setRecordedBlob(null);
    setRecordingDuration(0);

    const options = { mimeType: 'video/webm;codecs=vp8,opus' };
    let recorder;
    try {
      recorder = new MediaRecorder(stream, options);
    } catch (e) {
      // Fallback for Safari or browsers that prefer MP4 / default container
      recorder = new MediaRecorder(stream);
    }

    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        chunksRef.current.push(event.data);
      }
    };

    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'video/webm' });
      setRecordedBlob(blob);
      setIsRecording(false);
      clearInterval(timerRef.current);
    };

    mediaRecorderRef.current = recorder;
    recorder.start(1000); // chunk every second
    setIsRecording(true);

    timerRef.current = setInterval(() => {
      setRecordingDuration((prev) => prev + 1);
    }, 1000);
  }, [stream]);

  // Stop recording
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    clearInterval(timerRef.current);
  }, []);

  // Stop media tracks when component unmounts
  const stopStream = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      setStream(null);
      setHasPermissions(false);
    }
  }, [stream]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      stopStream();
    };
  }, [stopStream]);

  return {
    stream,
    hasPermissions,
    permissionError,
    isRecording,
    recordedBlob,
    recordingDuration,
    requestPermissions,
    startRecording,
    stopRecording,
    stopStream
  };
};

export default useMediaRecorder;
