import { useEffect } from "react";
import { usePlayback } from "./PlaybackProvider";

export function QueuePanel() {
  const { state, queue, refreshQueue } = usePlayback();
  useEffect(() => {
    if (state) void refreshQueue().catch(() => undefined);
  }, [refreshQueue, state?.session_id, state?.current_index]);
  return <aside className="queue-panel">
    <div className="section-heading"><div><span className="eyebrow">Up next</span><h2>Queue</h2></div><span className="count">{queue?.tracks.length ?? 0}</span></div>
    {!queue && <p className="muted">Start a release, playlist or track.</p>}
    {queue && <ol className="queue-list">{queue.tracks.map((track, index) => <li key={track.id} className={index === queue.current_index ? "is-current" : ""} aria-current={index === queue.current_index}><span>{index + 1}</span><div><strong>{track.title}</strong><small>{Math.floor(track.duration_ms / 60_000)}:{String(Math.floor(track.duration_ms / 1000) % 60).padStart(2, "0")}</small></div>{index === queue.current_index && <i>playing</i>}</li>)}</ol>}
  </aside>;
}
