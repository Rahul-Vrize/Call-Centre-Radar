"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

/**
 * One playhead, shared by the whole call view. The transcript, the mood
 * timeline and every evidence chip all seek through this — which is what makes
 * "click a claim, hear the three seconds that justify it" a two-click action.
 */
interface PlayerController {
  seek: (seconds: number) => void;
}

interface PlayerState {
  currentTime: number;
  /** Seek the audio to `seconds`. No-op until the waveform has loaded. */
  seekTo: (seconds: number) => void;
  /** Called by WaveformPlayer once wavesurfer is ready. */
  register: (controller: PlayerController | null) => void;
  setCurrentTime: (seconds: number) => void;
}

const PlayerCtx = createContext<PlayerState | null>(null);

export function PlayerProvider({ children }: { children: ReactNode }) {
  const controllerRef = useRef<PlayerController | null>(null);
  const [currentTime, setCurrentTime] = useState(0);

  const register = useCallback((controller: PlayerController | null) => {
    controllerRef.current = controller;
  }, []);

  const seekTo = useCallback((seconds: number) => {
    controllerRef.current?.seek(seconds);
  }, []);

  const value = useMemo(
    () => ({ currentTime, seekTo, register, setCurrentTime }),
    [currentTime, seekTo, register],
  );

  return <PlayerCtx.Provider value={value}>{children}</PlayerCtx.Provider>;
}

export function usePlayer(): PlayerState {
  const ctx = useContext(PlayerCtx);
  if (!ctx) throw new Error("usePlayer must be used inside a <PlayerProvider>");
  return ctx;
}
