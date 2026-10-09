import { type FormEvent, useEffect, useRef, useState } from "react";
import { ApiError, useApi } from "./api";
import type { Curation, Release, Track } from "./models";
import { usePlaybackOptional } from "./PlaybackProvider";
import "./curator.css";

const EXAMPLES = [
  "Холодный атмосферный breakcore для ночной прогулки",
  "Ностальгическая музыка для воспоминаний о прошлом",
  "Спокойная электронная музыка для отдыха вечером",
];

function errorMessage(cause: unknown): string {
  if (cause instanceof ApiError) {
    if (cause.status === 401) return "Сессия истекла. Войдите снова и повторите запрос.";
    if (cause.status === 429) return "Слишком много запросов. Подождите немного и попробуйте снова.";
    if (cause.status === 503) return "Куратор сейчас недоступен. Попробуйте ещё раз чуть позже.";
    if (cause.status === 502) return "Не удалось получить корректную подборку. Попробуйте повторить запрос.";
  }
  return "Не удалось получить ответ куратора. Проверьте соединение и попробуйте снова.";
}

type TrackDetails = { track: Track; artistName: string; releaseTitle: string };

export function CuratorView({ onLogin }: { onLogin(): void }) {
  const { request, tokens } = useApi();
  const player = usePlaybackOptional();
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(5);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Curation | null>(null);
  const [answeredQuery, setAnsweredQuery] = useState("");
  const [details, setDetails] = useState<Record<string, TrackDetails>>({});
  const [error, setError] = useState<string | null>(null);
  const [detailsWarning, setDetailsWarning] = useState(false);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  const currentRequest = useRef(0);
  const normalizedQuery = query.trim().replace(/\s+/g, " ");

  useEffect(() => () => {
    currentRequest.current += 1;
    controller.current?.abort();
  }, []);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!tokens) { onLogin(); return; }
    if (busy || normalizedQuery.length < 3 || normalizedQuery.length > 500) return;
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    const requestId = ++currentRequest.current;
    setBusy(true);
    setError(null);
    setDetailsWarning(false);
    setResult(null);
    setDetails({});
    const options = { signal: abort.signal };
    try {
      const next = await request<Curation>("/discovery/curations/preview", {
        ...options, method: "POST", body: JSON.stringify({ query: normalizedQuery, limit }),
      });
      if (currentRequest.current !== requestId) return;
      setResult(next);
      setAnsweredQuery(normalizedQuery);
      // Hydrate only the selected tracks; preserve the curator's order and reasons.
      const hydrated = await Promise.allSettled(next.tracks.map(async (item) => {
        const track = await request<Track>(`/tracks/${item.track_id}`, options);
        const release = await request<Release>(`/releases/${track.release_id}/with-tracks-and-author`, options);
        return [item.track_id, { track, artistName: release.author_name || "Независимый артист", releaseTitle: release.title }] as const;
      }));
      if (currentRequest.current !== requestId) return;
      setDetails(Object.fromEntries(hydrated.flatMap((item) => item.status === "fulfilled" ? [item.value] : [])));
      setDetailsWarning(hydrated.some((item) => item.status === "rejected"));
    } catch (cause) {
      if (!abort.signal.aborted && currentRequest.current === requestId) setError(errorMessage(cause));
    } finally {
      if (currentRequest.current === requestId) setBusy(false);
    }
  };

  const play = async (trackId: string) => {
    if (!player) return;
    setPlayingId(trackId);
    try {
      if (player.state?.current_track.id === trackId) {
        if (player.state.is_playing) await player.pause();
        else await player.resume();
      } else await player.playContext({ context: { type: "track", id: trackId } });
    } catch {
      setError("Не удалось запустить трек. Попробуйте ещё раз.");
    } finally { setPlayingId(null); }
  };

  return <section className="page-section curator">
    <div className="page-hero"><span className="micro">YUKINOISE / PERSONAL SELECTION</span><h1>Куратор</h1><p>Расскажите, что хотите услышать. Подберём музыку из каталога и объясним выбор.</p></div>
    <form className="curator-form" onSubmit={(event) => void submit(event)} aria-busy={busy}>
      <label htmlFor="curator-query">ВАШ ЗАПРОС</label>
      <textarea id="curator-query" value={query} onChange={(event) => setQuery(event.target.value)} rows={4} maxLength={500} disabled={busy} placeholder="Например: мрачный энергичный breakcore для вечерней прогулки" aria-describedby="curator-query-hint" />
      <div className="curator-examples" aria-label="Примеры запросов">{EXAMPLES.map((example) => <button type="button" key={example} disabled={busy} onClick={() => setQuery(example)}>{example} ↗</button>)}</div>
      <div className="curator-form-footer">
        <label htmlFor="curator-limit">ТРЕКОВ<select id="curator-limit" value={limit} disabled={busy} onChange={(event) => setLimit(Number(event.target.value))}>{[3, 5, 8, 10].map((value) => <option value={value} key={value}>{value}</option>)}</select></label>
        <small id="curator-query-hint">{normalizedQuery.length}/500 · минимум 3 символа</small>
        <button className="primary" disabled={busy || (Boolean(tokens) && normalizedQuery.length < 3)}>{busy ? "ПОДБИРАЕМ МУЗЫКУ…" : tokens ? "ПОЛУЧИТЬ ПОДБОРКУ →" : "ВОЙТИ И ПОПРОБОВАТЬ →"}</button>
      </div>
    </form>
    {!tokens && <p className="curator-note">Войдите в аккаунт, чтобы обращаться к куратору и слушать треки.</p>}
    {error && <div className="form-error" role="alert">{error}</div>}
    {busy && !result && <div className="curator-pending" role="status"><i /><span>Куратор читает запрос и выбирает треки…</span></div>}
    {result && <section className="curator-answer" aria-label="Ответ куратора" aria-live="polite">
      <span className="micro">ОТВЕТ НА ВАШ ЗАПРОС</span><p className="curator-answered-query">«{answeredQuery}»</p>
      <h2>{result.title}</h2>{result.summary && <p className="curator-summary">{result.summary}</p>}
      {!result.tracks.length ? <div className="curator-empty"><h3>Подходящих треков пока нет</h3><p>Попробуйте другое настроение или более широкий запрос.</p></div> : <ol className="curator-tracks">{result.tracks.map((item) => {
        const info = details[item.track_id];
        const active = player?.state?.current_track.id === item.track_id && player.state.is_playing;
        return <li key={item.track_id}>
          <div className="curator-track-copy"><strong>{info?.track.title || (busy ? "Загружаем название…" : "Трек недоступен")}</strong>{info && <small>{info.artistName} · {info.releaseTitle} · {Math.floor(info.track.duration_seconds / 60)}:{String(info.track.duration_seconds % 60).padStart(2, "0")}</small>}<p>{item.reason}</p>{info && <div className="curator-genres">{info.track.genres.map((genre) => <span key={genre}>{genre}</span>)}</div>}</div>
          <button type="button" className="ghost curator-play" disabled={!info || !player || playingId !== null} onClick={() => void play(item.track_id)} aria-label={`${active ? "Приостановить" : "Слушать"} ${info?.track.title || "трек"}`}>{active ? "Ⅱ ПАУЗА" : "▶ СЛУШАТЬ"}</button>
        </li>;
      })}</ol>}
      {detailsWarning && <p className="curator-note" role="status">Часть треков больше недоступна. Объяснения куратора сохранены; попробуйте получить новую подборку.</p>}
    </section>}
  </section>;
}
