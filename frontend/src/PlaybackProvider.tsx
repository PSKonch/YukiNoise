import {
  createContext,
  type PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { PlayContextOptions, PlaybackState, QueueState, RepeatMode } from "./types";

type TokenProvider = () => string | Promise<string>;

interface PlayerApi {
  state: PlaybackState | null;
  queue: QueueState | null;
  positionMs: number;
  deviceId: string;
  isActiveDevice: boolean;
  error: string | null;
  volume: number;
  playContext(options: PlayContextOptions): Promise<void>;
  resume(): Promise<void>;
  pause(): Promise<void>;
  seek(positionMs: number): Promise<void>;
  next(): Promise<void>;
  previous(): Promise<void>;
  setRepeat(mode: RepeatMode): Promise<void>;
  transfer(): Promise<void>;
  stop(): Promise<void>;
  refreshQueue(): Promise<void>;
  setVolume(volume: number): void;
}

const PlaybackContext = createContext<PlayerApi | null>(null);

function browserStorage(): Storage | null {
  try { return typeof window === "undefined" ? null : window.localStorage; }
  catch { return null; }
}

function persistentDeviceId(): string {
  const key = "yukinoise.playback.device-id";
  const storage = browserStorage();
  let id = storage?.getItem(key) ?? null;
  if (!id) {
    id = crypto.randomUUID();
    storage?.setItem(key, id);
  }
  return id;
}

export interface PlaybackProviderProps extends PropsWithChildren {
  apiBaseUrl: string;
  getAccessToken: TokenProvider;
  deviceId?: string;
}

export function PlaybackProvider({
  apiBaseUrl,
  getAccessToken,
  deviceId: explicitDeviceId,
  children,
}: PlaybackProviderProps) {
  const deviceId = useMemo(() => explicitDeviceId ?? persistentDeviceId(), [explicitDeviceId]);
  const [state, setState] = useState<PlaybackState | null>(null);
  const [queue, setQueue] = useState<QueueState | null>(null);
  const [positionMs, setPositionMs] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [volume, setVolumeState] = useState(() => {
    const stored = Number(browserStorage()?.getItem("yukinoise.playback.volume") ?? "0.8");
    return Number.isFinite(stored) ? Math.max(0, Math.min(stored, 1)) : 0.8;
  });
  const audio = useRef<HTMLAudioElement | null>(null);
  const sequence = useRef(0);
  const attempt = useRef<string | null>(null);
  const heartbeatFailures = useRef(0);

  if (!audio.current) audio.current = new Audio();

  const request = useCallback(async <T,>(path: string, init: RequestInit = {}): Promise<T> => {
    const token = await getAccessToken();
    const response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...init.headers },
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => null) as { detail?: string } | null;
      throw new Error(payload?.detail ?? `Player request failed: ${response.status}`);
    }
    if (response.status === 204) return undefined as T;
    return response.json() as Promise<T>;
  }, [apiBaseUrl, getAccessToken]);

  const applyState = useCallback((next: PlaybackState | null) => {
    setState(next);
    if (!next) return;
    setPositionMs(next.position_ms);
    if (attempt.current !== next.attempt_id) {
      attempt.current = next.attempt_id;
      sequence.current = next.heartbeat_sequence;
    } else {
      sequence.current = Math.max(sequence.current, next.heartbeat_sequence);
    }
    const element = audio.current!;
    const source = `${apiBaseUrl}${next.current_track.stream_url}`;
    if (element.src !== new URL(source, window.location.href).href) {
      element.src = source;
      element.currentTime = next.position_ms / 1000;
    } else if (Math.abs(element.currentTime * 1000 - next.position_ms) > 1_000) {
      element.currentTime = next.position_ms / 1000;
    }
    if (next.active_device_id !== deviceId || !next.is_playing) element.pause();
    else void element.play().catch(() => undefined);
  }, [apiBaseUrl, deviceId]);

  const refresh = useCallback(async () => {
    applyState(await request<PlaybackState | null>("/me/player"));
  }, [applyState, request]);

  const refreshQueue = useCallback(async () => {
    setQueue(await request<QueueState>("/me/player/queue"));
  }, [request]);

  const command = useCallback(async (path: string, method: string, body: object) => {
    try {
      setError(null);
      applyState(await request<PlaybackState>(path, { method, body: JSON.stringify(body) }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Playback command failed");
      throw cause;
    }
  }, [applyState, request]);

  const reportProgress = useCallback(async () => {
    const current = state;
    if (!current || !current.is_playing || current.active_device_id !== deviceId) return;
    try {
      const next = await request<PlaybackState>("/me/player/progress", {
        method: "POST",
        body: JSON.stringify({
          device_id: deviceId,
          session_id: current.session_id,
          attempt_id: current.attempt_id,
          sequence: ++sequence.current,
          position_ms: Math.round(audio.current!.currentTime * 1000),
        }),
      });
      heartbeatFailures.current = 0;
      setState(next);
    } catch {
      heartbeatFailures.current += 1;
      if (heartbeatFailures.current >= 3) audio.current!.pause();
    }
  }, [deviceId, request, state]);

  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => { audio.current!.volume = Math.max(0, Math.min(volume, 1)); }, [volume]);
  useEffect(() => {
    const timer = window.setInterval(() => {
      setPositionMs(Math.round(audio.current!.currentTime * 1000));
    }, 250);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    const timer = window.setInterval(() => void reportProgress(), 5_000);
    return () => clearInterval(timer);
  }, [reportProgress]);

  useEffect(() => {
    let socket: WebSocket | undefined;
    let retry: number | undefined;
    let closed = false;
    const connect = async () => {
      const token = await getAccessToken();
      const url = new URL(`${apiBaseUrl}/me/player/events`, window.location.href);
      url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
      socket = new WebSocket(url);
      socket.onopen = () => socket?.send(JSON.stringify({ type: "authenticate", access_token: token, device_id: deviceId }));
      socket.onmessage = () => void refresh();
      socket.onclose = () => { if (!closed) retry = window.setTimeout(connect, 2_000); };
    };
    void connect();
    return () => { closed = true; if (retry) clearTimeout(retry); socket?.close(); };
  }, [apiBaseUrl, deviceId, getAccessToken, refresh]);

  useEffect(() => {
    const element = audio.current!;
    const ended = () => void command("/me/player/next", "POST", { device_id: deviceId, ended: true });
    element.addEventListener("ended", ended);
    return () => element.removeEventListener("ended", ended);
  }, [command, deviceId]);

  const value = useMemo<PlayerApi>(() => ({
    state, queue, positionMs, deviceId, error, volume,
    isActiveDevice: state?.active_device_id === deviceId,
    playContext: async ({ context, offsetTrackId, positionMs: start = 0 }) => command("/me/player/play", "PUT", { device_id: deviceId, context, offset_track_id: offsetTrackId, position_ms: start }),
    resume: async () => command("/me/player/play", "PUT", { device_id: deviceId }),
    pause: async () => { await reportProgress(); await command("/me/player/pause", "PUT", { device_id: deviceId }); },
    seek: async (value) => { setPositionMs(value); await command("/me/player/seek", "PUT", { device_id: deviceId, position_ms: value }); },
    next: async () => { await reportProgress(); await command("/me/player/next", "POST", { device_id: deviceId, ended: false }); },
    previous: async () => { await reportProgress(); await command("/me/player/previous", "POST", { device_id: deviceId }); },
    setRepeat: async (mode) => command("/me/player/repeat", "PUT", { device_id: deviceId, mode }),
    transfer: async () => command("/me/player/transfer", "PUT", { device_id: deviceId }),
    stop: async () => {
      await request<void>("/me/player", { method: "DELETE", body: JSON.stringify({ device_id: deviceId }) });
      audio.current!.pause();
      setState(null);
      setQueue(null);
    },
    refreshQueue,
    setVolume: (value) => {
      const normalized = Math.max(0, Math.min(value, 1));
      audio.current!.volume = normalized;
      setVolumeState(normalized);
      browserStorage()?.setItem("yukinoise.playback.volume", String(normalized));
    },
  }), [command, deviceId, error, positionMs, queue, refreshQueue, reportProgress, request, state, volume]);

  return <PlaybackContext.Provider value={value}>{children}</PlaybackContext.Provider>;
}

export function usePlayback(): PlayerApi {
  const value = useContext(PlaybackContext);
  if (!value) throw new Error("usePlayback must be used inside PlaybackProvider");
  return value;
}

export function usePlaybackOptional(): PlayerApi | null {
  return useContext(PlaybackContext);
}
