/**
 * Q&Ace — useWebRTC hook.
 *
 * Manages:
 *  - Microphone capture (audio track → WebRTC)
 *  - Webcam capture (video for face mesh, optional)
 *  - SDP offer/answer exchange with backend (POST /webrtc/offer)
 *  - RTCPeerConnection lifecycle
 *  - Creates 'qace-events' DataChannel for bidirectional messaging
 *  - Creates 'au-telemetry' DataChannel for binary AU data (Phase 2)
 *  - Exposes addVideoTrack() for face crop stream
 *
 * The hook exposes connection state, a start/stop API, and the data channels
 * for useDataChannel to subscribe to.
 */

import { useCallback, useRef, useState } from "react";

export type ConnectionState = "idle" | "connecting" | "connected" | "error";

function getApiUrl(): string {
  if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_QACE_API_URL) {
    return process.env.NEXT_PUBLIC_QACE_API_URL;
  }
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    return `http://${host}:8000`;
  }
  return "http://127.0.0.1:8000";
}

export function useWebRTC() {
  const [state, setState] = useState<ConnectionState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [dataChannel, setDataChannel] = useState<RTCDataChannel | null>(null);
  const [auChannel, setAuChannel] = useState<RTCDataChannel | null>(null);
  const [webcamStream, setWebcamStream] = useState<MediaStream | null>(null);
  const [remoteAudioStream, setRemoteAudioStream] = useState<MediaStream | null>(null);
  const [remoteVideoStream, setRemoteVideoStream] = useState<MediaStream | null>(null);
  const [isMicEnabled, setIsMicEnabled] = useState(true);
  const [isCamEnabled, setIsCamEnabled] = useState(true);
  const [micGated, setMicGated] = useState(false);

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const webcamRef = useRef<MediaStream | null>(null);
  const addedVideoTrackIdsRef = useRef<Set<string>>(new Set());

  // ── Add face crop video track (called after connection) ──
  const addVideoTrack = useCallback((stream: MediaStream) => {
    const pc = pcRef.current;
    if (!pc) return;
    for (const track of stream.getVideoTracks()) {
      if (addedVideoTrackIdsRef.current.has(track.id)) {
        continue;
      }
      pc.addTrack(track, stream);
      addedVideoTrackIdsRef.current.add(track.id);
    }
  }, []);

  const applyMicGate = useCallback(
    (gated: boolean) => {
      setMicGated(gated);
      const stream = streamRef.current;
      if (!stream) return;
      // If system is ungating, only enable if user hasn't manually muted
      const shouldEnable = !gated && isMicEnabled;
      stream.getAudioTracks().forEach((track) => {
        track.enabled = shouldEnable;
      });
    },
    [isMicEnabled]
  );

  const toggleMic = useCallback(() => {
    const stream = streamRef.current;
    if (!stream) return;
    const next = !isMicEnabled;
    // Only touch the track if mic is not system-gated
    if (!micGated) {
      stream.getAudioTracks().forEach((track) => {
        track.enabled = next;
      });
    }
    setIsMicEnabled(next);
  }, [isMicEnabled, micGated]);

  const toggleCam = useCallback(() => {
    const stream = webcamRef.current;
    if (!stream) return;
    const next = !isCamEnabled;
    stream.getVideoTracks().forEach((track) => {
      track.enabled = next;
    });
    setIsCamEnabled(next);
  }, [isCamEnabled]);

  // ── Start session ──
  const start = useCallback(async (durationMinutes: number = 20, stressLevel: string = "none", cvSessionId: string = "") => {
    setState("connecting");
    setError(null);

    try {
      // 1. Capture microphone + webcam
      const audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 48000,
        },
        video: false,
      });
      streamRef.current = audioStream;
      setIsMicEnabled(audioStream.getAudioTracks().some((track) => track.enabled));

      // Also capture webcam for face mesh (separate stream)
      try {
        const videoStream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 640 },
            height: { ideal: 480 },
            frameRate: { ideal: 15 },
            facingMode: "user",
          },
          audio: false,
        });
        webcamRef.current = videoStream;
        setWebcamStream(videoStream);
        setIsCamEnabled(videoStream.getVideoTracks().some((track) => track.enabled));
      } catch {
        console.warn("Webcam not available — face analysis disabled");
        setIsCamEnabled(false);
      }

      // 2. Create RTCPeerConnection
      const pc = new RTCPeerConnection({
        iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
      });
      pcRef.current = pc;

      // 3. Add audio track
      for (const track of audioStream.getAudioTracks()) {
        pc.addTrack(track, audioStream);
      }

      // 3b. Advertise receive capability for server-returned TTS audio and avatar video.
      // Without these transceivers, the offer may omit recv media sections and aiortc
      // cannot legally attach outbound tracks while generating the answer.
      pc.addTransceiver("audio", { direction: "recvonly" });
      pc.addTransceiver("video", { direction: "recvonly" });

      // 4. Create DataChannel BEFORE offer (so it's in the SDP)
      const dc = pc.createDataChannel("qace-events", {
        ordered: true,
      });
      setDataChannel(dc);
      dc.onopen = () => setDataChannel(dc);
      dc.onclose = () => setDataChannel(null);

      // 4b. Create AU telemetry channel (unreliable, per ADR-010)
      const auDc = pc.createDataChannel("au-telemetry", {
        ordered: false,
        maxRetransmits: 0,
      });
      auDc.binaryType = "arraybuffer";
      setAuChannel(auDc);
      auDc.onopen = () => setAuChannel(auDc);
      auDc.onclose = () => setAuChannel(null);

      // 5. Monitor connection state
      pc.onconnectionstatechange = () => {
        const s = pc.connectionState;
        if (s === "connected") {
          setState("connected");
          setMicGated(false); // Reset gate on successful connection/reconnect
        }
        if (s === "failed" || s === "closed") {
          setState("idle");
          cleanup();
        }
      };

      // 5b. Handle incoming tracks from server (TTS audio + avatar video)
      pc.ontrack = (ev) => {
        const track = ev.track;
        const stream = ev.streams[0] || new MediaStream([track]);
        if (track.kind === "audio") {
          setRemoteAudioStream(stream);
        } else if (track.kind === "video") {
          setRemoteVideoStream(stream);
        }
      };

      // 6. Create offer
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      // 7. Send to backend
      const apiUrl = getApiUrl();
      const resp = await fetch(`${apiUrl}/webrtc/offer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sdp: pc.localDescription!.sdp,
          type: pc.localDescription!.type,
          duration_minutes: durationMinutes,
          stress_level: stressLevel,
          cv_session_id: cvSessionId,
        }),
      });

      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`Backend returned ${resp.status}: ${text}`);
      }

      const answer = await resp.json();
      setSessionId(answer.session_id);

      await pc.setRemoteDescription(
        new RTCSessionDescription({ sdp: answer.sdp, type: answer.type })
      );

      setState("connected");
    } catch (err: any) {
      console.error("WebRTC start error:", err);
      setError(err?.message ?? "Connection failed");
      setState("error");
      cleanup();
    }
  }, []);

  // ── Stop session ──
  const stop = useCallback(() => {
    cleanup();
    setState("idle");
    setSessionId(null);
    setError(null);
  }, []);

  // ── Cleanup ──
  function cleanup() {
    if (pcRef.current) {
      pcRef.current.close();
      pcRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (webcamRef.current) {
      webcamRef.current.getTracks().forEach((t) => t.stop());
      webcamRef.current = null;
    }
    addedVideoTrackIdsRef.current.clear();
    setDataChannel(null);
    setAuChannel(null);
    setWebcamStream(null);
    setRemoteAudioStream(null);
    setRemoteVideoStream(null);
    setIsMicEnabled(true);
    setIsCamEnabled(true);
    setMicGated(false);
  }

  return {
    state,
    error,
    sessionId,
    dataChannel,
    auChannel,
    webcamStream,
    remoteAudioStream,
    remoteVideoStream,
    isMicEnabled,
    isCamEnabled,
    micGated,
    toggleMic,
    toggleCam,
    applyMicGate,
    start,
    stop,
    addVideoTrack,
  };
}
