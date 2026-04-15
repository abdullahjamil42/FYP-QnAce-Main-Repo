"use client";

import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";

interface InterviewerAvatarProps {
  containerClassName?: string;
  avatarState?: string | null;
  onLoad?: () => void;
  onError?: (err: any) => void;
}

export interface InterviewerAvatarRef {
  speak: (stream: MediaStream) => void;
  stopSpeaking: () => void;
}

const InterviewerAvatar = forwardRef<InterviewerAvatarRef, InterviewerAvatarProps>(
  ({ containerClassName, avatarState, onLoad, onError }, ref) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const headRef = useRef<any>(null);
    const [isLoaded, setIsLoaded] = useState(false);
    const [hasError, setHasError] = useState(false);
    const hasErrorRef = useRef(false);
    const audioCtxRef = useRef<AudioContext | null>(null);
    const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
    const processorRef = useRef<ScriptProcessorNode | null>(null);
    const silentGainRef = useRef<GainNode | null>(null);

    // Expose methods to parent
    useImperativeHandle(ref, () => ({
      speak: (stream: MediaStream) => {
        if (!headRef.current || !stream || hasErrorRef.current) return;

        // Ensure audio context is running
        if (!audioCtxRef.current) {
          audioCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({
            sampleRate: 48000
          });
        }
        
        if (audioCtxRef.current.state === "suspended") {
          audioCtxRef.current.resume();
        }

        // Clean up previous capture if any
        if (processorRef.current) {
          processorRef.current.onaudioprocess = null;
          processorRef.current.disconnect();
          processorRef.current = null;
        }
        if (sourceRef.current) {
          sourceRef.current.disconnect();
          sourceRef.current = null;
        }
        if (silentGainRef.current) {
          silentGainRef.current.disconnect();
          silentGainRef.current = null;
        }

        const source = audioCtxRef.current.createMediaStreamSource(stream);
        const processor = audioCtxRef.current.createScriptProcessor(4096, 1, 1);
        const silentGain = audioCtxRef.current.createGain();
        silentGain.gain.value = 0;

        source.connect(processor);
        processor.connect(silentGain);
        silentGain.connect(audioCtxRef.current.destination);

        processor.onaudioprocess = (e) => {
          const input = e.inputBuffer.getChannelData(0);
          // Convert float32 [-1, 1] to int16 PCM for TalkingHead
          const pcm = new Int16Array(input.length);
          for (let i = 0; i < input.length; i++) {
            // TalkingHead expects signed 16-bit PCM. 
            // Scaling 1.0 to 32767 and -1.0 to -32768.
            pcm[i] = Math.max(-32768, Math.min(32767, input[i] * 32768));
          }
          
          // Feed to TalkingHead via speakAudio
          // Note: Passing as an array [pcm.buffer] triggers pcmToAudioBuffer internal conversion
          try {
            if (headRef.current && headRef.current.avatar) {
              headRef.current.speakAudio({
                audio: [pcm.buffer],
                words: [],
                wtimes: [],
                wdurations: []
              }, { lipsyncLang: "en", isRaw: true });
            }
          } catch (e) {
            // Silently ignore if avatar mesh is not ready
          }
        };

        sourceRef.current = source;
        processorRef.current = processor;
        silentGainRef.current = silentGain;
      },
      stopSpeaking: () => {
        if (headRef.current) {
          headRef.current.stopSpeaking();
        }
        if (processorRef.current) {
          processorRef.current.onaudioprocess = null;
          processorRef.current.disconnect();
          processorRef.current = null;
        }
        if (sourceRef.current) {
          sourceRef.current.disconnect();
          sourceRef.current = null;
        }
        if (silentGainRef.current) {
          silentGainRef.current.disconnect();
          silentGainRef.current = null;
        }
      },
    }));

    useEffect(() => {
      let isMounted = true;

      const init = async () => {
        try {
          // Dynamic import from importmap with webpackIgnore to avoid Next.js bundling issues
          // @ts-ignore
          const module = await import(/* webpackIgnore: true */ "talkinghead");
          const TalkingHead = module.TalkingHead;

          if (!isMounted || !containerRef.current) return;

          const head = new TalkingHead(containerRef.current, {
            lipsyncModules: ["en"],
            cameraView: "head",
            cameraRotateEnable: false,
            cameraPanEnable: false,
            cameraZoomEnable: false,
            avatarMood: "neutral",
            mixerGainSpeech: 0,
            pcmSampleRate: 48000
          });

          headRef.current = head;

          // Correct API method is showAvatar (v1.7)
          // It takes an avatar object with 'url' property
          // @ts-ignore
          await head.showAvatar({ url: "/avatars/interviewer.glb" });

          if (isMounted) {
            setIsLoaded(true);
            onLoad?.();
            console.log("TalkingHead 3D Avatar loaded and ready");
          }
        } catch (err) {
          console.error("TalkingHead initialization failed:", err);
          if (isMounted) {
            setHasError(true);
            hasErrorRef.current = true;
            onError?.(err);
          }
        }
      };

      init();

      return () => {
        isMounted = false;
        if (headRef.current) {
          // Cleanup
          try { headRef.current.stop(); } catch(e) {}
        }
        if (processorRef.current) {
          processorRef.current.onaudioprocess = null;
          processorRef.current.disconnect();
          processorRef.current = null;
        }
        if (sourceRef.current) {
          sourceRef.current.disconnect();
          sourceRef.current = null;
        }
        if (silentGainRef.current) {
          silentGainRef.current.disconnect();
          silentGainRef.current = null;
        }
        if (audioCtxRef.current) {
          void audioCtxRef.current.close();
          audioCtxRef.current = null;
        }
      };
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
      if (!headRef.current || !isLoaded || !avatarState) return;
      
      try {
        switch (avatarState) {
          case "AVATAR_COLD":
            headRef.current.setAvatarMood("angry");
            break;
          case "AVATAR_INTERRUPT":
            headRef.current.playAnim("disagree");
            break;
          case "AVATAR_SKEPTICAL":
            headRef.current.playAnim("think");
            break;
        }
      } catch (err) {
        console.warn("Avatar state transition failed:", err);
      }
    }, [avatarState, isLoaded]);

    return (
      <div 
        ref={containerRef} 
        className={`${containerClassName} relative overflow-hidden bg-black/40`}
        style={{ width: '100%', height: '100%' }}
      >
        {hasError ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/60 z-50 backdrop-blur-md">
            <svg className="h-16 w-16 text-indigo-400/80 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-[var(--muted)] text-[10px] uppercase tracking-wide text-center px-4 font-semibold">Avatar Display Idle<br/><span className="font-medium opacity-60">Voice Engine Connected</span></span>
          </div>
        ) : !isLoaded ? (
          <div className="absolute inset-0 flex items-center justify-center bg-zinc-950 z-50">
            <div className="flex flex-col items-center gap-4">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--accent-base)] border-t-transparent" />
              <span className="text-[var(--muted)] text-xs font-medium animate-pulse">Initializing 3D Pipeline...</span>
            </div>
          </div>
        ) : null}
      </div>
    );
  }
);

InterviewerAvatar.displayName = "InterviewerAvatar";

export default InterviewerAvatar;
