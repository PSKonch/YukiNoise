import { useEffect, useState } from "react";
import { usePlayback } from "./PlaybackProvider";
import type { RepeatMode } from "./types";
import "./player.css";

function time(ms: number): string {
  const seconds = Math.max(0, Math.floor(ms / 1000));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

const repeatLabels: Record<RepeatMode, string> = {
  off: "Repeat off",
  context: "Repeat queue",
  track: "Repeat track",
};

export function PlayerBar() {
  const player = usePlayback();
  const state = player.state;
  const [dragging, setDragging] = useState(false);
  const [draftPosition, setDraftPosition] = useState(0);
  useEffect(() => { if (!dragging) setDraftPosition(player.positionMs); }, [dragging, player.positionMs]);

  if (!state) {
    return <footer className="yn-player yn-player--empty"><span className="yn-player__note">Choose a track to start playback</span></footer>;
  }
  const modes: RepeatMode[] = ["off", "context", "track"];
  const nextRepeat = modes[(modes.indexOf(state.repeat_mode) + 1) % modes.length];
  const shownPosition = dragging ? draftPosition : player.positionMs;
  const listenedPercent = Math.min(100, Math.round((state.listened_ms / state.current_track.duration_ms) * 100));

  const commitSeek = () => {
    if (!dragging) return;
    setDragging(false);
    void player.seek(draftPosition);
  };

  return <footer className="yn-player">
    <div className="yn-player__track">
      <span className="yn-player__art">♫</span>
      <span><strong>{state.current_track.title}</strong><small>Track {state.current_index + 1} of {state.queue_length} · listened {listenedPercent}% {state.counted ? "· counted" : ""}</small></span>
    </div>
    <div className="yn-player__transport">
      <div className="yn-player__buttons">
        <button onClick={() => void player.previous()} aria-label="Previous" title="Previous">⏮</button>
        <button className="yn-player__play" onClick={() => void (state.is_playing ? player.pause() : player.resume())} aria-label={state.is_playing ? "Pause" : "Play"}>{state.is_playing ? "⏸" : "▶"}</button>
        <button onClick={() => void player.next()} aria-label="Next" title="Next">⏭</button>
        <button className={state.repeat_mode !== "off" ? "is-active" : ""} onClick={() => void player.setRepeat(nextRepeat)} aria-label="Repeat" title={repeatLabels[state.repeat_mode]}>↻<small>{state.repeat_mode === "track" ? "1" : ""}</small></button>
      </div>
      <div className="yn-player__timeline">
        <span>{time(shownPosition)}</span>
        <input aria-label="Position" type="range" min={0} max={state.current_track.duration_ms} value={Math.min(shownPosition, state.current_track.duration_ms)} onPointerDown={() => setDragging(true)} onChange={(event) => { setDragging(true); setDraftPosition(Number(event.target.value)); }} onPointerUp={commitSeek} onKeyUp={commitSeek} />
        <span>{time(state.current_track.duration_ms)}</span>
      </div>
    </div>
    <div className="yn-player__extras">
      <label title="Volume">🔊<input aria-label="Volume" type="range" min={0} max={1} step={0.05} value={player.volume} onChange={(event) => player.setVolume(Number(event.target.value))} /></label>
      {!player.isActiveDevice && <button onClick={() => void player.transfer()}>Play here</button>}
      <button className="yn-player__stop" onClick={() => void player.stop()} title="Stop">■</button>
    </div>
    {player.error && <div className="yn-player__error">{player.error}</div>}
  </footer>;
}
