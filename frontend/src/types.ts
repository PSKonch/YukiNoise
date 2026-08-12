export type ContextType = "track" | "release" | "playlist";
export type RepeatMode = "off" | "track" | "context";

export interface PlaybackContextRef { type: ContextType; id: string }
export interface PlaybackTrack {
  id: string;
  title: string;
  duration_ms: number;
  stream_url: string;
}
export interface PlaybackState {
  session_id: string;
  revision: number;
  active_device_id: string;
  context: PlaybackContextRef;
  current_track: PlaybackTrack;
  current_index: number;
  queue_length: number;
  attempt_id: string;
  heartbeat_sequence: number;
  position_ms: number;
  is_playing: boolean;
  repeat_mode: RepeatMode;
  listened_ms: number;
  counted: boolean;
}
export interface QueueState { current_index: number; tracks: PlaybackTrack[] }
export interface PlayContextOptions {
  context: PlaybackContextRef;
  offsetTrackId?: string;
  positionMs?: number;
}
