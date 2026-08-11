import {
  type FormEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import { ApiError, ApiProvider, API_BASE, readTokens, responseError, TOKEN_KEY, useApi } from "./api";
import type {
  Artist,
  Commentary,
  LikeTargetType,
  Playlist,
  PlaylistTrack,
  Post,
  Release,
  TokenPair,
  Track,
  User,
  ViewName,
} from "./models";
import { PlaybackProvider, usePlaybackOptional } from "./PlaybackProvider";
import { PlayerBar } from "./PlayerBar";
import { QueuePanel } from "./QueuePanel";
import type { ContextType } from "./types";
import "./app.css";

const LIMIT = "limit=100&offset=0";

function formatDate(value?: string | null): string {
  if (!value) return "без даты";
  return new Intl.DateTimeFormat("ru", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value));
}

function formatDuration(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds) % 60).padStart(2, "0")}`;
}

function initials(value?: string | null): string {
  const parts = (value || "YN").trim().split(/\s+/);
  return parts.slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

function coverClass(id: string): string {
  return `tone-${[...id].reduce((sum, char) => sum + char.charCodeAt(0), 0) % 6}`;
}

function Modal({ children, onClose, wide = false }: { children: ReactNode; onClose(): void; wide?: boolean }) {
  useEffect(() => {
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [onClose]);
  return <div className="modal-backdrop" onMouseDown={onClose}>
    <section className={`modal ${wide ? "modal--wide" : ""}`} onMouseDown={(event) => event.stopPropagation()}>
      <button className="modal-close" onClick={onClose} aria-label="Закрыть">×</button>
      {children}
    </section>
  </div>;
}

function NoiseMark({ large = false }: { large?: boolean }) {
  return <div className={`noise-mark ${large ? "noise-mark--large" : ""}`} aria-label="YukiNoise">
    <span>雪</span><strong>YUKI<br />NOISE</strong>
  </div>;
}

function Empty({ title, copy }: { title: string; copy: string }) {
  return <div className="empty"><span>∿</span><h3>{title}</h3><p>{copy}</p></div>;
}

function Loading({ label = "приём сигнала" }: { label?: string }) {
  return <div className="loading"><i /><span>{label}...</span></div>;
}

function SectionTitle({ code, title, aside }: { code: string; title: string; aside?: ReactNode }) {
  return <div className="section-title"><div><span>{code}</span><h2>{title}</h2></div>{aside}</div>;
}

function PlayTrackButton({ track, contextType = "track", contextId, label = false }: {
  track: Track;
  contextType?: ContextType;
  contextId?: string;
  label?: boolean;
}) {
  const player = usePlaybackOptional();
  const active = player?.state?.current_track.id === track.id;
  const play = () => {
    if (!player) return;
    if (active && player.state?.is_playing) void player.pause();
    else if (active) void player.resume();
    else void player.playContext({
      context: { type: contextType, id: contextId ?? track.id },
      offsetTrackId: contextType === "track" ? undefined : track.id,
    });
  };
  return <button className={label ? "play-pill" : "round-play"} onClick={play} disabled={!player} title={player ? "Воспроизвести" : "Войдите, чтобы слушать"}>
    {active && player?.state?.is_playing ? "Ⅱ" : "▶"}{label && <span>{active ? "пауза" : "слушать"}</span>}
  </button>;
}

interface EngagementProps {
  artist: Artist | null;
  onNeedIdentity(): void;
  notify(message: string): void;
}

function TrackList({ tracks, contextType = "track", contextId, onSelect, engagement }: {
  tracks: Track[];
  contextType?: ContextType;
  contextId?: string;
  onSelect?(track: Track): void;
  engagement?: EngagementProps;
}) {
  return <div className="track-list">
    {tracks.map((track, index) => <div className="track-line" key={track.id} onClick={() => onSelect?.(track)}>
      <PlayTrackButton track={track} contextType={contextType} contextId={contextId} />
      <span className="track-index">{String(track.track_number_in_release || index + 1).padStart(2, "0")}</span>
      <div><strong>{track.title}</strong><small>{track.genres.length ? track.genres.join(" / ") : "genre: unknown"}</small></div>
      <span>{formatDuration(track.duration_seconds)}</span>
      {engagement && <LikeButton targetType="track" targetId={track.id} {...engagement} compact />}
    </div>)}
  </div>;
}

function LikeButton({ targetType, targetId, artist, onNeedIdentity, notify, compact = false }: {
  targetType: LikeTargetType;
  targetId: string;
  compact?: boolean;
} & EngagementProps) {
  const { request } = useApi();
  const [liked, setLiked] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    if (!artist) { setLiked(false); return; }
    request<{ is_liked: boolean }>(`/likes/${targetType}/${targetId}/status`)
      .then((result) => { if (live) setLiked(result.is_liked); })
      .catch(() => { if (live) setLiked(false); });
    return () => { live = false; };
  }, [artist, request, targetId, targetType]);

  const toggle = async () => {
    if (!artist) { onNeedIdentity(); return; }
    setBusy(true);
    try {
      await request(`/likes/${targetType}/${targetId}`, { method: liked ? "DELETE" : "POST" });
      setLiked(!liked);
      notify(liked ? "Убрано из понравившихся" : "Добавлено в понравившиеся");
    } catch (cause) {
      notify(cause instanceof Error ? cause.message : "Не удалось сохранить реакцию");
    } finally { setBusy(false); }
  };

  return <button
    className={`like-button ${compact ? "like-button--compact" : ""} ${liked ? "is-active" : ""}`}
    onClick={(event) => { event.stopPropagation(); void toggle(); }}
    disabled={busy}
    aria-label={liked ? "Убрать отметку нравится" : "Отметить как понравившееся"}
    title={liked ? "Убрать из понравившихся" : "Добавить в понравившиеся"}
  >
    <span>{liked ? "♥" : "♡"}</span>{!compact && <em>{liked ? "нравится" : "оценить"}</em>}
  </button>;
}

function FollowButton({ targetArtistId, artist, onNeedIdentity, notify }: {
  targetArtistId: string;
} & EngagementProps) {
  const { request } = useApi();
  const [following, setFollowing] = useState(false);
  const [busy, setBusy] = useState(false);
  const ownProfile = artist?.id === targetArtistId;

  useEffect(() => {
    let live = true;
    if (!artist || ownProfile) return;
    request<{ is_following: boolean }>(`/follows/${targetArtistId}/status`)
      .then((result) => { if (live) setFollowing(result.is_following); })
      .catch(() => { if (live) setFollowing(false); });
    return () => { live = false; };
  }, [artist, ownProfile, request, targetArtistId]);

  if (ownProfile) return null;
  const toggle = async () => {
    if (!artist) { onNeedIdentity(); return; }
    setBusy(true);
    try {
      await request(`/follows/${targetArtistId}`, { method: following ? "DELETE" : "POST" });
      setFollowing(!following);
      notify(following ? "Подписка отменена" : "Вы подписались на артиста");
    } catch (cause) {
      notify(cause instanceof Error ? cause.message : "Не удалось обновить подписку");
    } finally { setBusy(false); }
  };
  return <button className={`follow-button ${following ? "is-active" : ""}`} onClick={() => void toggle()} disabled={busy}>
    <span>{following ? "✓" : "+"}</span>{following ? "ВЫ ПОДПИСАНЫ" : "ПОДПИСАТЬСЯ"}
  </button>;
}

type EntitySelection = { type: "artist"; value: Artist } | { type: "release"; value: Release } | { type: "post"; value: Post } | { type: "playlist"; value: Playlist };

function GlobalSearch({ onSelect }: { onSelect(selection: EntitySelection): void }) {
  const { request } = useApi();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<{ artists: Artist[]; releases: Release[]; posts: Post[] }>({ artists: [], releases: [], posts: [] });

  useEffect(() => {
    if (query.trim().length < 2) { setResults({ artists: [], releases: [], posts: [] }); return; }
    const timer = window.setTimeout(async () => {
      setLoading(true);
      const encoded = encodeURIComponent(query.trim());
      try {
        const [artists, releases, posts] = await Promise.all([
          request<Artist[]>(`/artists/search?query=${encoded}&limit=6&offset=0`),
          request<Release[]>(`/releases/search?search_term=${encoded}&limit=6&offset=0`),
          request<Post[]>(`/posts/search?query=${encoded}&limit=6&offset=0`),
        ]);
        setResults({ artists, releases, posts });
      } finally { setLoading(false); }
    }, 260);
    return () => clearTimeout(timer);
  }, [query, request]);

  const count = results.artists.length + results.releases.length + results.posts.length;
  return <div className="global-search">
    <span className="search-glyph">⌕</span>
    <input value={query} onFocus={() => setOpen(true)} onChange={(event) => { setQuery(event.target.value); setOpen(true); }} placeholder="поиск по шуму..." aria-label="Глобальный поиск" />
    <kbd>FTS</kbd>
    {open && query.trim().length >= 2 && <div className="search-results">
      <div className="search-result-head"><span>полнотекстовый поиск</span><button onClick={() => setOpen(false)}>закрыть</button></div>
      {loading && <Loading label="сканирование" />}
      {!loading && count === 0 && <Empty title="Тишина" copy="Ничего не совпало с этим запросом." />}
      {!loading && results.artists.length > 0 && <div className="search-group"><small>АРТИСТЫ</small>{results.artists.map((artist) => <button key={artist.id} onClick={() => { onSelect({ type: "artist", value: artist }); setOpen(false); }}><i className={coverClass(artist.id)}>{initials(artist.displayed_name)}</i><span><strong>{artist.displayed_name}</strong><em>{artist.bio || "профиль артиста"}</em></span><b>↗</b></button>)}</div>}
      {!loading && results.releases.length > 0 && <div className="search-group"><small>РЕЛИЗЫ</small>{results.releases.map((release) => <button key={release.id} onClick={() => { onSelect({ type: "release", value: release }); setOpen(false); }}><i className={coverClass(release.id)}>{initials(release.title)}</i><span><strong>{release.title}</strong><em>{release.release_type} · {release.status}</em></span><b>↗</b></button>)}</div>}
      {!loading && results.posts.length > 0 && <div className="search-group"><small>ЗАПИСИ</small>{results.posts.map((post) => <button key={post.id} onClick={() => { onSelect({ type: "post", value: post }); setOpen(false); }}><i>TXT</i><span><strong>{post.title}</strong><em>{post.author_name || "анонимный сигнал"}</em></span><b>↗</b></button>)}</div>}
    </div>}
  </div>;
}

function AuthModal({ onClose, onAuthenticated }: { onClose(): void; onAuthenticated(tokens: TokenPair): void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError(null);
    try {
      const login = mode === "login";
      const response = await fetch(`${API_BASE}/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": login ? "application/x-www-form-urlencoded" : "application/json" },
        body: login ? new URLSearchParams({ username: email, password }) : JSON.stringify({ email, password }),
      });
      if (!response.ok) throw new Error(await responseError(response));
      onAuthenticated(await response.json() as TokenPair);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Не удалось подключиться"); }
    finally { setBusy(false); }
  };
  return <Modal onClose={onClose}>
    <div className="auth-panel">
      <div className="auth-signal"><NoiseMark large /><div className="wave-bars">{Array.from({ length: 18 }, (_, index) => <i key={index} />)}</div><p>PRIVATE FREQUENCY<br />CHANNEL 1998—∞</p></div>
      <div className="auth-form"><span className="micro">NODE AUTHORIZATION</span><h2>{mode === "login" ? "Вернуться в сеть" : "Создать узел"}</h2><p>Музыка для тех, кто остался онлайн слишком поздно.</p>
        <form onSubmit={(event) => void submit(event)}>
          <label>E-MAIL<input autoFocus type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@somewhere.net" required /></label>
          <label>ПАРОЛЬ<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="••••••••" required minLength={4} /></label>
          {error && <div className="form-error">{error}</div>}
          <button className="primary" disabled={busy}>{busy ? "соединение..." : mode === "login" ? "ВОЙТИ В СЕТЬ →" : "СОЗДАТЬ АККАУНТ →"}</button>
        </form>
        <button className="text-action" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }}>{mode === "login" ? "Нет идентификатора? Регистрация" : "Уже есть идентификатор? Войти"}</button>
      </div>
    </div>
  </Modal>;
}

function ReleaseCard({ release, onSelect }: { release: Release; onSelect(): void }) {
  const firstTrack = release.tracks?.[0];
  return <article className="release-tile">
    <button className={`cover-art ${coverClass(release.id)}`} onClick={onSelect}>
      <span className="cover-code">YN-{release.id.slice(0, 4).toUpperCase()}</span>
      <strong>{initials(release.title)}</strong><i /><em>{release.release_type}</em>
    </button>
    <div className="tile-meta"><button onClick={onSelect}><strong>{release.title}</strong><small>{release.author_name || "независимый артист"}</small></button>{firstTrack && <PlayTrackButton track={firstTrack} contextType="release" contextId={release.id} />}</div>
  </article>;
}

function Discover({ onSelect }: { onSelect(selection: EntitySelection): void }) {
  const { request } = useApi();
  const [releases, setReleases] = useState<Release[]>([]);
  const [artists, setArtists] = useState<Artist[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let live = true;
    Promise.all([
      request<Release[]>(`/releases/with-tracks-and-author?${LIMIT}`),
      request<Artist[]>(`/artists/?limit=8&offset=0`),
      request<Post[]>(`/posts/?limit=4&offset=0`),
    ]).then(([nextReleases, nextArtists, nextPosts]) => {
      if (live) { setReleases(nextReleases); setArtists(nextArtists); setPosts(nextPosts); }
    }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [request]);

  if (loading) return <Loading />;
  const featured = releases[0];
  const featuredTrack = featured?.tracks?.[0];
  const visibleTracks = releases.reduce((count, release) => count + (release.tracks?.length || 0), 0);
  return <>
    <section className="broadcast">
      <header className="broadcast-head">
        <div><span className="micro">YUKINOISE / РОТАЦИЯ {new Date().getFullYear()}</span><h1>Сейчас в эфире</h1></div>
        <dl>
          <div><dt>РЕЛИЗЫ</dt><dd>{releases.length}</dd></div>
          <div><dt>ТРЕКИ</dt><dd>{visibleTracks}</dd></div>
          <div><dt>АРТИСТЫ</dt><dd>{artists.length}</dd></div>
        </dl>
      </header>
      {featured ? <div className="broadcast-feature">
        <button className={`cover-art broadcast-cover ${coverClass(featured.id)}`} onClick={() => onSelect({ type: "release", value: featured })} aria-label={`Открыть релиз ${featured.title}`}>
          <span className="cover-code">YN-{featured.id.slice(0, 4).toUpperCase()}</span><strong>{initials(featured.title)}</strong><i /><em>{featured.release_type}</em>
        </button>
        <div className="broadcast-copy">
          <span className="micro">НОВЫЙ РЕЛИЗ / {formatDate(featured.release_date)}</span>
          <h2>{featured.title}</h2>
          <p className="broadcast-author">{featured.author_name || "независимый артист"}</p>
          <p>{featured.description || "Новый сигнал в каталоге YukiNoise."}</p>
          <div className="broadcast-actions">{featuredTrack && <PlayTrackButton track={featuredTrack} contextType="release" contextId={featured.id} label />}<button className="ghost" onClick={() => onSelect({ type: "release", value: featured })}>ОТКРЫТЬ РЕЛИЗ ↗</button></div>
        </div>
        <div className="rotation">
          <div className="rotation-head"><span>ПОСЛЕДНИЕ СИГНАЛЫ</span><b>{String(Math.min(releases.length, 4)).padStart(2, "0")}</b></div>
          {releases.slice(0, 4).map((release, index) => <button key={release.id} onClick={() => onSelect({ type: "release", value: release })}>
            <span>{String(index + 1).padStart(2, "0")}</span><div><strong>{release.title}</strong><small>{release.author_name || "unknown"}</small></div><em>{release.tracks?.[0] ? formatDuration(release.tracks[0].duration_seconds) : release.release_type}</em>
          </button>)}
        </div>
      </div> : <Empty title="Эфир пуст" copy="Первый опубликованный релиз займёт это место." />}
      <div className="broadcast-strip"><span>НЕЗАВИСИМЫЙ КАТАЛОГ</span><span>БЕЗ РЕКОМЕНДАТЕЛЬНЫХ АЛГОРИТМОВ</span><span>● СЕТЬ ДОСТУПНА</span></div>
    </section>

    <section className="content-section">
      <SectionTitle code="01 / NEW TRANSMISSIONS" title="Свежие релизы" aside={<span className="section-note">сигналы из независимой сети</span>} />
      {releases.length ? <div className="release-grid">{releases.slice(0, 8).map((release) => <ReleaseCard key={release.id} release={release} onSelect={() => onSelect({ type: "release", value: release })} />)}</div> : <Empty title="Эфир пуст" copy="Опубликованные релизы появятся здесь." />}
    </section>

    <section className="content-section split-section">
      <div><SectionTitle code="02 / PEOPLE" title="Узлы сети" />
        <div className="artist-stack">{artists.map((artist, index) => <button key={artist.id} onClick={() => onSelect({ type: "artist", value: artist })}><span>{String(index + 1).padStart(2, "0")}</span><i className={coverClass(artist.id)}>{initials(artist.displayed_name)}</i><div><strong>{artist.displayed_name}</strong><small>{artist.bio || "нет описания"}</small></div><b>↗</b></button>)}</div>
      </div>
      <div><SectionTitle code="03 / LOG" title="Дневники" />
        <div className="post-stack">{posts.map((post) => <button key={post.id} onClick={() => onSelect({ type: "post", value: post })}><span>{formatDate(post.created_at)}</span><h3>{post.title}</h3><p>{post.content}</p><small>by {post.author_name || "unknown"} →</small></button>)}</div>
      </div>
    </section>
  </>;
}

function ArtistsView({ onSelect }: { onSelect(selection: EntitySelection): void }) {
  const { request } = useApi();
  const [query, setQuery] = useState("");
  const [artists, setArtists] = useState<Artist[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setLoading(true);
      const path = query.trim() ? `/artists/search?query=${encodeURIComponent(query)}&${LIMIT}` : `/artists/?${LIMIT}`;
      request<Artist[]>(path).then(setArtists).finally(() => setLoading(false));
    }, query ? 250 : 0);
    return () => clearTimeout(timer);
  }, [query, request]);
  return <section className="page-section">
    <div className="page-hero"><span className="micro">DIRECTORY / FULL TEXT INDEX</span><h1>Артисты сети</h1><p>Люди по ту сторону белого шума.</p></div>
    <label className="page-search"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="имя, псевдоним, фрагмент..." /><kbd>POSTGRES FTS</kbd></label>
    {loading ? <Loading label="индексация" /> : artists.length ? <div className="artist-directory">{artists.map((artist, index) => <button key={artist.id} onClick={() => onSelect({ type: "artist", value: artist })}><span className="directory-no">{String(index + 1).padStart(3, "0")}</span><i className={coverClass(artist.id)}>{initials(artist.displayed_name)}</i><div><h2>{artist.displayed_name}</h2><p>{artist.bio || "Биография пока не передана."}</p></div><b>PROFILE ↗</b></button>)}</div> : <Empty title="Никого не найдено" copy="Попробуйте другой фрагмент имени." />}
  </section>;
}

function FeedView({ onSelect }: { onSelect(selection: EntitySelection): void }) {
  const { request } = useApi();
  const [query, setQuery] = useState("");
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setLoading(true);
      const path = query.trim() ? `/posts/search?query=${encodeURIComponent(query)}&${LIMIT}` : `/posts/?${LIMIT}`;
      request<Post[]>(path).then(setPosts).finally(() => setLoading(false));
    }, query ? 250 : 0);
    return () => clearTimeout(timer);
  }, [query, request]);
  return <section className="page-section">
    <div className="page-hero"><span className="micro">PUBLIC LOG / EN + RU</span><h1>Дневники</h1><p>Тексты, заметки и следы процесса.</p></div>
    <label className="page-search"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="искать внутри записей..." /><kbd>FULL TEXT</kbd></label>
    {loading ? <Loading /> : posts.length ? <div className="feed-grid">{posts.map((post, index) => <article key={post.id}><span className="micro">LOG.{String(index + 1).padStart(3, "0")} / {formatDate(post.created_at)}</span><h2>{post.title}</h2><p>{post.content}</p><button onClick={() => onSelect({ type: "post", value: post })}>читать полностью ↗</button><small>{post.author_name || "unknown artist"}</small></article>)}</div> : <Empty title="Записей нет" copy="По этому запросу дневники молчат." />}
  </section>;
}

function LibraryView({ onSelect, engagement }: { onSelect(selection: EntitySelection): void; engagement: EngagementProps }) {
  const { request } = useApi();
  const [tab, setTab] = useState<"playlists" | "tracks">("playlists");
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { Promise.all([request<Playlist[]>(`/playlists/?${LIMIT}`), request<Track[]>(`/tracks/?${LIMIT}`)]).then(([a, b]) => { setPlaylists(a); setTracks(b); }).finally(() => setLoading(false)); }, [request]);
  return <section className="page-section">
    <div className="page-hero"><span className="micro">ARCHIVE / ALL FREQUENCIES</span><h1>Архив</h1><p>Плейлисты и отдельные треки без алгоритмической магии.</p></div>
    <div className="segmented"><button className={tab === "playlists" ? "active" : ""} onClick={() => setTab("playlists")}>ПЛЕЙЛИСТЫ <span>{playlists.length}</span></button><button className={tab === "tracks" ? "active" : ""} onClick={() => setTab("tracks")}>ТРЕКИ <span>{tracks.length}</span></button></div>
    {loading ? <Loading /> : tab === "playlists" ? <div className="playlist-grid">{playlists.map((playlist) => <button className="playlist-tile" key={playlist.id} onClick={() => onSelect({ type: "playlist", value: playlist })}><i className={coverClass(playlist.id)}><span>≋</span></i><div><small>{playlist.playlist_type} / {playlist.is_private ? "private" : "public"}</small><h2>{playlist.title}</h2><p>{playlist.description || "Без описания"}</p></div><b>↗</b></button>)}</div> : <TrackList tracks={tracks} engagement={engagement} />}
  </section>;
}

function CommentaryThread({ postId, artist, onNeedIdentity, notify }: {
  postId: string;
} & EngagementProps) {
  const { request } = useApi();
  const [commentaries, setCommentaries] = useState<Commentary[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState("");
  const [replyTo, setReplyTo] = useState<Commentary | null>(null);
  const [editing, setEditing] = useState<Commentary | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setCommentaries(await request<Commentary[]>(`/posts/${postId}/commentaries?limit=100&offset=0`));
    } finally { setLoading(false); }
  }, [postId, request]);
  useEffect(() => { void load(); }, [load]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!artist) { onNeedIdentity(); return; }
    const content = draft.trim();
    if (!content) return;
    setBusy(true);
    try {
      await request(`/posts/${postId}/commentaries`, {
        method: "POST",
        body: JSON.stringify({ content, commentary_id: replyTo?.id ?? null }),
      });
      setDraft(""); setReplyTo(null); await load(); notify("Комментарий опубликован");
    } catch (cause) {
      notify(cause instanceof Error ? cause.message : "Не удалось опубликовать комментарий");
    } finally { setBusy(false); }
  };

  const saveEdit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editing) return;
    const data = new FormData(event.currentTarget);
    const content = String(data.get("content") || "").trim();
    if (!content) return;
    setBusy(true);
    try {
      await request(`/commentaries/${editing.id}`, { method: "PUT", body: JSON.stringify({ content }) });
      setEditing(null); await load(); notify("Комментарий обновлён");
    } catch (cause) {
      notify(cause instanceof Error ? cause.message : "Не удалось обновить комментарий");
    } finally { setBusy(false); }
  };

  const remove = async (commentary: Commentary) => {
    if (!confirm("Удалить комментарий?")) return;
    try {
      await request(`/commentaries/${commentary.id}`, { method: "DELETE" });
      await load(); notify("Комментарий удалён");
    } catch (cause) {
      notify(cause instanceof Error ? cause.message : "Не удалось удалить комментарий");
    }
  };

  const byId = new Map(commentaries.map((commentary) => [commentary.id, commentary]));
  const depth = (commentary: Commentary) => {
    let value = 0;
    let parentId = commentary.commentary_id;
    while (parentId && byId.has(parentId) && value < 2) {
      value += 1;
      parentId = byId.get(parentId)?.commentary_id ?? null;
    }
    return value;
  };

  return <section className="commentary-thread">
    <SectionTitle code="DISCUSSION" title={`Комментарии · ${commentaries.length}`} />
    <form className="commentary-compose" onSubmit={(event) => void submit(event)}>
      <div className="commentary-compose__head">
        <span>{artist ? `от имени ${artist.displayed_name}` : "нужен профиль артиста"}</span>
        {replyTo && <button type="button" onClick={() => setReplyTo(null)}>ответ для {replyTo.author_name || "автора"} ×</button>}
      </div>
      <textarea
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        placeholder={replyTo ? "Написать ответ..." : "Добавить комментарий..."}
        maxLength={5000}
        rows={3}
        onFocus={() => { if (!artist) onNeedIdentity(); }}
      />
      <div><small>{draft.length} / 5000</small><button className="primary compact" disabled={busy || !draft.trim()}>{busy ? "ОТПРАВКА..." : "ОПУБЛИКОВАТЬ →"}</button></div>
    </form>
    {loading ? <Loading label="загрузка обсуждения" /> : commentaries.length ? <div className="commentary-list">
      {commentaries.map((commentary) => <article className={`commentary depth-${depth(commentary)}`} key={commentary.id}>
        <div className={`commentary-avatar ${coverClass(commentary.artist_id)}`}>{initials(commentary.author_name)}</div>
        <div className="commentary-body">
          <header><strong>{commentary.author_name || "неизвестный артист"}</strong><span>{formatDate(commentary.created_at)}</span>{commentary.updated_at !== commentary.created_at && <em>изменено</em>}</header>
          {editing?.id === commentary.id ? <form className="commentary-edit" onSubmit={(event) => void saveEdit(event)}><textarea name="content" defaultValue={commentary.content} maxLength={5000} autoFocus /><div><button type="button" onClick={() => setEditing(null)}>отмена</button><button disabled={busy}>сохранить</button></div></form> : <p>{commentary.content}</p>}
          <footer>
            <LikeButton targetType="commentary" targetId={commentary.id} artist={artist} onNeedIdentity={onNeedIdentity} notify={notify} compact />
            <button onClick={() => { setReplyTo(commentary); setEditing(null); }}>ответить</button>
            {artist?.id === commentary.artist_id && <><button onClick={() => { setEditing(commentary); setReplyTo(null); }}>изменить</button><button className="danger" onClick={() => void remove(commentary)}>удалить</button></>}
          </footer>
        </div>
      </article>)}
    </div> : <div className="discussion-empty"><span>Первый комментарий пока не прозвучал.</span><p>Начните обсуждение релиза, процесса или идеи автора.</p></div>}
  </section>;
}

function EntityDetail({ selection, onClose, onSelect, engagement }: {
  selection: EntitySelection;
  onClose(): void;
  onSelect(selection: EntitySelection): void;
  engagement: EngagementProps;
}) {
  const { request } = useApi();
  const [loading, setLoading] = useState(true);
  const [artistData, setArtistData] = useState<{ releases: Release[]; tracks: Track[]; posts: Post[]; playlists: Playlist[] } | null>(null);
  const [release, setRelease] = useState<Release | null>(null);
  const [playlistTracks, setPlaylistTracks] = useState<Track[]>([]);
  useEffect(() => {
    setLoading(true);
    if (selection.type === "artist") {
      Promise.all([
        request<Release[]>(`/artists/${selection.value.id}/releases?${LIMIT}`),
        request<Track[]>(`/artists/${selection.value.id}/tracks?${LIMIT}`),
        request<Post[]>(`/artists/${selection.value.id}/posts?${LIMIT}`),
        request<Playlist[]>(`/artists/${selection.value.id}/playlists?${LIMIT}`),
      ]).then(([releases, tracks, posts, playlists]) => setArtistData({ releases, tracks, posts, playlists })).finally(() => setLoading(false));
    } else if (selection.type === "release") {
      request<Release>(`/releases/${selection.value.id}/with-tracks-and-author`).then(setRelease).finally(() => setLoading(false));
    } else if (selection.type === "playlist") {
      request<PlaylistTrack[]>(`/playlists/${selection.value.id}/tracks?${LIMIT}`).then((items) => setPlaylistTracks(items.flatMap((item) => item.track ? [item.track] : []))).finally(() => setLoading(false));
    } else setLoading(false);
  }, [request, selection]);

  return <Modal onClose={onClose} wide>
    {selection.type === "artist" && <div className="detail-page">
      <div className="detail-identity"><i className={coverClass(selection.value.id)}>{initials(selection.value.displayed_name)}</i><div><span className="micro">ARTIST NODE / {selection.value.id.slice(0, 8)}</span><h1>{selection.value.displayed_name}</h1><p>{selection.value.bio || "Этот узел пока не оставил описания."}</p><div className="detail-actions"><FollowButton targetArtistId={selection.value.id} {...engagement} /><div className="socials">{Object.entries(selection.value.social_links || {}).map(([name, url]) => <a key={name} href={url} target="_blank" rel="noreferrer">{name} ↗</a>)}</div></div></div></div>
      {loading ? <Loading /> : artistData && <div className="detail-columns"><div><SectionTitle code="DISCOGRAPHY" title={`Релизы · ${artistData.releases.length}`} /><div className="mini-releases">{artistData.releases.map((item) => <button key={item.id} onClick={() => onSelect({ type: "release", value: item })}><i className={coverClass(item.id)}>{initials(item.title)}</i><span><strong>{item.title}</strong><small>{item.release_type} · {formatDate(item.release_date)}</small></span><b>↗</b></button>)}</div><SectionTitle code="TRACK INDEX" title={`Треки · ${artistData.tracks.length}`} /><TrackList tracks={artistData.tracks} engagement={engagement} /></div><div><SectionTitle code="LOG" title="Записи" /><div className="post-stack">{artistData.posts.map((post) => <button key={post.id} onClick={() => onSelect({ type: "post", value: post })}><span>{formatDate(post.created_at)}</span><h3>{post.title}</h3><p>{post.content}</p></button>)}</div><SectionTitle code="CURATED" title="Плейлисты" />{artistData.playlists.map((playlist) => <button className="inline-link" key={playlist.id} onClick={() => onSelect({ type: "playlist", value: playlist })}>{playlist.title}<span>↗</span></button>)}</div></div>}
    </div>}
    {selection.type === "release" && <div className="detail-page">{loading || !release ? <Loading /> : <><div className="release-detail-head"><div className={`cover-art ${coverClass(release.id)}`}><span className="cover-code">YN-{release.id.slice(0, 4)}</span><strong>{initials(release.title)}</strong><i /><em>{release.release_type}</em></div><div><span className="micro">{release.status} / {release.release_type}</span><h1>{release.title}</h1><p className="release-author">{release.author_name || "independent artist"}</p><p>{release.description || "Описание не передано."}</p><div className="detail-actions">{release.tracks?.[0] && <PlayTrackButton track={release.tracks[0]} contextType="release" contextId={release.id} label />}<LikeButton targetType="release" targetId={release.id} {...engagement} /></div></div></div><SectionTitle code="TRACKLIST" title={`${release.tracks?.length || 0} tracks`} /><TrackList tracks={release.tracks || []} contextType="release" contextId={release.id} engagement={engagement} /></>}</div>}
    {selection.type === "post" && <article className="post-detail"><span className="micro">PUBLIC LOG / {formatDate(selection.value.created_at)}</span><h1>{selection.value.title}</h1><div className="post-by">by {selection.value.author_name || "unknown artist"}</div><LikeButton targetType="post" targetId={selection.value.id} {...engagement} /><p>{selection.value.content}</p><CommentaryThread postId={selection.value.id} {...engagement} /></article>}
    {selection.type === "playlist" && <div className="detail-page"><div className="playlist-detail-head"><i className={coverClass(selection.value.id)}>≋</i><div><span className="micro">{selection.value.playlist_type} / {selection.value.is_private ? "PRIVATE" : "PUBLIC"}</span><h1>{selection.value.title}</h1><p>{selection.value.description || "Без описания."}</p><LikeButton targetType="playlist" targetId={selection.value.id} {...engagement} /></div></div>{loading ? <Loading /> : <TrackList tracks={playlistTracks} contextType="playlist" contextId={selection.value.id} engagement={engagement} />}</div>}
  </Modal>;
}

type Editor = { type: "release" | "track" | "post" | "playlist"; item?: Release | Track | Post | Playlist } | null;

function StudioEditor({ editor, releases, onClose, onSaved }: { editor: NonNullable<Editor>; releases: Release[]; onClose(): void; onSaved(message: string): void }) {
  const { request, upload } = useApi();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const item = editor.item;
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy(true); setError(null);
    const data = new FormData(event.currentTarget);
    try {
      if (editor.type === "release") {
        if (item) {
          await request(`/releases/${item.id}/description?description=${encodeURIComponent(String(data.get("description") || ""))}`, { method: "PATCH" });
          const cover = data.get("cover") as File;
          if (cover?.size) { const form = new FormData(); form.append("cover", cover); await upload(`/releases/${item.id}/cover`, form, "PATCH"); }
        } else await request<Release>("/releases/", { method: "POST", body: JSON.stringify({ title: data.get("title"), description: data.get("description") || null, cover_path: null, release_type: data.get("release_type") }) });
      }
      if (editor.type === "track") {
        const genres = String(data.get("genres") || "").split(",").map((value) => value.trim()).filter(Boolean);
        if (item) await request(`/tracks/${item.id}`, { method: "PATCH", body: JSON.stringify({ title: data.get("title"), track_number_in_release: Number(data.get("track_number")), genres }) });
        else {
          const form = new FormData();
          form.append("release_id", String(data.get("release_id"))); form.append("title", String(data.get("title"))); form.append("track_number_in_release", String(data.get("track_number"))); form.append("file", data.get("file") as File); genres.forEach((genre) => form.append("genres", genre));
          await upload("/tracks/", form);
        }
      }
      if (editor.type === "post") {
        const body = JSON.stringify({ title: data.get("title"), content: data.get("content") });
        await request(item ? `/posts/${item.id}` : "/posts/", { method: item ? "PUT" : "POST", body });
      }
      if (editor.type === "playlist") {
        const body = JSON.stringify({ title: data.get("title"), description: data.get("description") || null, cover_url: data.get("cover_url") || null, is_private: data.get("is_private") === "on" });
        await request(item ? `/playlists/${item.id}` : "/playlists/", { method: item ? "PATCH" : "POST", body });
      }
      onSaved(item ? "Изменения записаны" : "Новый объект создан"); onClose();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Ошибка записи"); }
    finally { setBusy(false); }
  };
  const title = `${item ? "Редактировать" : "Создать"} ${{ release: "релиз", track: "трек", post: "запись", playlist: "плейлист" }[editor.type]}`;
  return <Modal onClose={onClose}><form className="editor" onSubmit={(event) => void submit(event)}><span className="micro">STUDIO / WRITE MODE</span><h2>{title}</h2>
    {(editor.type === "release" || editor.type === "track" || editor.type === "post" || editor.type === "playlist") && <label>НАЗВАНИЕ<input name="title" defaultValue={(item as Release | Track | Post | Playlist | undefined)?.title || ""} required disabled={editor.type === "release" && Boolean(item)} /></label>}
    {editor.type === "release" && <><label>ОПИСАНИЕ<textarea name="description" defaultValue={(item as Release | undefined)?.description || ""} rows={5} /></label>{!item && <label>ФОРМАТ<select name="release_type"><option value="single">single</option><option value="ep">EP</option><option value="album">album</option></select></label>}{item && <label>НОВАЯ ОБЛОЖКА<input name="cover" type="file" accept="image/*" /></label>}</>}
    {editor.type === "track" && <>{!item && <label>РЕЛИЗ<select name="release_id" required>{releases.filter((release) => !release.deleted_at).map((release) => <option value={release.id} key={release.id}>{release.title}</option>)}</select></label>}<div className="form-pair"><label>НОМЕР<input name="track_number" type="number" min="1" defaultValue={(item as Track | undefined)?.track_number_in_release || 1} required /></label><label>ЖАНРЫ<input name="genres" defaultValue={(item as Track | undefined)?.genres.join(", ") || ""} placeholder="breakcore, ambient" /></label></div>{!item && <label>АУДИО (MP3 / WAV)<input name="file" type="file" accept="audio/mpeg,audio/wav,.mp3,.wav" required /></label>}</>}
    {editor.type === "post" && <label>ТЕКСТ<textarea name="content" defaultValue={(item as Post | undefined)?.content || ""} rows={12} required /></label>}
    {editor.type === "playlist" && <><label>ОПИСАНИЕ<textarea name="description" defaultValue={(item as Playlist | undefined)?.description || ""} rows={4} /></label><label>URL ОБЛОЖКИ<input name="cover_url" type="url" defaultValue={(item as Playlist | undefined)?.cover_url || ""} placeholder="https://..." /></label><label className="checkbox"><input name="is_private" type="checkbox" defaultChecked={(item as Playlist | undefined)?.is_private} /><span>приватный плейлист</span></label></>}
    {error && <div className="form-error">{error}</div>}<div className="editor-actions"><button type="button" className="ghost" onClick={onClose}>отмена</button><button className="primary" disabled={busy}>{busy ? "запись..." : "СОХРАНИТЬ →"}</button></div>
  </form></Modal>;
}

function Studio({ artist, onArtistChanged, notify }: { artist: Artist | null; onArtistChanged(): Promise<void>; notify(message: string): void }) {
  const { request } = useApi();
  const [tab, setTab] = useState<"profile" | "releases" | "tracks" | "posts" | "playlists">("profile");
  const [releases, setReleases] = useState<Release[]>([]);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [allTracks, setAllTracks] = useState<Track[]>([]);
  const [playlistTracks, setPlaylistTracks] = useState<Record<string, PlaylistTrack[]>>({});
  const [editor, setEditor] = useState<Editor>(null);
  const [loading, setLoading] = useState(Boolean(artist));

  const load = useCallback(async () => {
    if (!artist) return;
    setLoading(true);
    const [a, b, c, d, all] = await Promise.all([
      request<Release[]>(`/releases/me?${LIMIT}`), request<Track[]>(`/tracks/me?${LIMIT}`), request<Post[]>(`/posts/me?${LIMIT}`), request<Playlist[]>(`/playlists/me?${LIMIT}`), request<Track[]>(`/tracks/?${LIMIT}`),
    ]);
    setReleases(a); setTracks(b); setPosts(c); setPlaylists(d); setAllTracks(all); setLoading(false);
  }, [artist, request]);
  useEffect(() => { void load(); }, [load]);

  if (!artist) return <section className="page-section studio-empty"><span className="micro">CREATOR ACCESS</span><h1>Создайте свой узел</h1><p>Профиль артиста открывает студию: релизы, загрузку треков, дневник и плейлисты.</p><form onSubmit={(event) => { event.preventDefault(); const data = new FormData(event.currentTarget); void request("/artists/", { method: "POST", body: JSON.stringify({ displayed_name: data.get("name"), bio: data.get("bio") || null, social_links: null }) }).then(() => onArtistChanged()).then(() => notify("Профиль артиста создан")); }}><label>ПСЕВДОНИМ<input name="name" required /></label><label>КОРОТКО О СЕБЕ<textarea name="bio" rows={5} /></label><button className="primary">ПОДКЛЮЧИТЬСЯ К СЕТИ →</button></form></section>;

  const remove = async (kind: "tracks" | "posts" | "playlists", id: string) => {
    if (!confirm("Удалить без возможности отмены?")) return;
    await request(`/${kind}/${id}`, { method: "DELETE" }); notify("Объект удалён"); await load();
  };
  const schedule = async (release: Release) => {
    if (release.status === "scheduled") await request(`/releases/${release.id}/release`, { method: "DELETE" });
    else {
      const raw = prompt("Дата и время публикации (YYYY-MM-DDTHH:mm)", new Date(Date.now() + 86_400_000).toISOString().slice(0, 16));
      if (!raw) return;
      await request(`/releases/${release.id}/release`, { method: "PATCH", body: JSON.stringify({ release_date: new Date(raw).toISOString() }) });
    }
    notify(release.status === "scheduled" ? "Публикация отменена" : "Релиз запланирован"); await load();
  };
  const openPlaylist = async (id: string) => {
    if (playlistTracks[id]) { setPlaylistTracks((current) => { const next = { ...current }; delete next[id]; return next; }); return; }
    const rows = await request<PlaylistTrack[]>(`/playlists/me/${id}/tracks?${LIMIT}`); setPlaylistTracks((current) => ({ ...current, [id]: rows }));
  };
  const addTrack = async (playlistId: string) => {
    const trackId = prompt(`ID трека для добавления:\n${allTracks.slice(0, 12).map((track) => `${track.id} — ${track.title}`).join("\n")}`);
    if (!trackId) return;
    await request(`/playlists/${playlistId}/tracks/${trackId.trim()}`, { method: "POST" }); notify("Трек добавлен");
    const rows = await request<PlaylistTrack[]>(`/playlists/me/${playlistId}/tracks?${LIMIT}`); setPlaylistTracks((current) => ({ ...current, [playlistId]: rows }));
  };
  const removePlaylistTrack = async (playlistId: string, trackId: string) => {
    await request(`/playlists/${playlistId}/tracks/${trackId}`, { method: "DELETE" });
    setPlaylistTracks((current) => ({ ...current, [playlistId]: current[playlistId].filter((row) => row.track_id !== trackId) })); notify("Трек убран из плейлиста");
  };

  const tabCounts = { profile: "", releases: releases.length, tracks: tracks.length, posts: posts.length, playlists: playlists.length };
  return <section className="page-section studio">
    <div className="page-hero"><span className="micro">PRIVATE CREATOR TERMINAL</span><h1>Студия</h1><p>{artist.displayed_name} / управление исходящим сигналом.</p></div>
    <div className="studio-tabs">{(["profile", "releases", "tracks", "posts", "playlists"] as const).map((name) => <button className={tab === name ? "active" : ""} onClick={() => setTab(name)} key={name}>{({ profile: "ПРОФИЛЬ", releases: "РЕЛИЗЫ", tracks: "ТРЕКИ", posts: "ЗАПИСИ", playlists: "ПЛЕЙЛИСТЫ" })[name]} {tabCounts[name] !== "" && <span>{tabCounts[name]}</span>}</button>)}</div>
    {loading ? <Loading /> : <>
      {tab === "profile" && <ProfileEditor artist={artist} onSaved={async () => { await onArtistChanged(); notify("Профиль обновлён"); }} />}
      {tab !== "profile" && <div className="studio-toolbar"><div><span className="micro">DATABASE / OWNED</span><h2>{({ releases: "Ваши релизы", tracks: "Ваши треки", posts: "Ваши записи", playlists: "Ваши плейлисты" } as Record<string, string>)[tab]}</h2></div><button className="primary compact" onClick={() => setEditor({ type: tab === "releases" ? "release" : tab === "tracks" ? "track" : tab === "posts" ? "post" : "playlist" })}>＋ СОЗДАТЬ</button></div>}
      {tab === "releases" && <div className="manage-list">{releases.map((release) => <div className="manage-row" key={release.id}><i className={coverClass(release.id)}>{initials(release.title)}</i><div><strong>{release.title}</strong><small>{release.release_type} / {release.status}{release.release_date ? ` / ${formatDate(release.release_date)}` : ""}</small></div><div className="row-actions"><button onClick={() => void schedule(release)}>{release.status === "scheduled" ? "отменить дату" : "публикация"}</button><button onClick={() => setEditor({ type: "release", item: release })}>описание / cover</button></div></div>)}</div>}
      {tab === "tracks" && <div className="manage-list">{tracks.map((track) => <div className="manage-row" key={track.id}><span className="mono-index">{String(track.track_number_in_release).padStart(2, "0")}</span><div><strong>{track.title}</strong><small>{track.genres.join(" / ") || "no genre"} · {formatDuration(track.duration_seconds)}</small></div><div className="row-actions"><PlayTrackButton track={track} /><button onClick={() => setEditor({ type: "track", item: track })}>изменить</button><button className="danger" onClick={() => void remove("tracks", track.id)}>удалить</button></div></div>)}</div>}
      {tab === "posts" && <div className="manage-list">{posts.map((post) => <div className="manage-row" key={post.id}><span className="mono-index">TXT</span><div><strong>{post.title}</strong><small>{formatDate(post.created_at)} · {post.content.slice(0, 80)}</small></div><div className="row-actions"><button onClick={() => setEditor({ type: "post", item: post })}>изменить</button><button className="danger" onClick={() => void remove("posts", post.id)}>удалить</button></div></div>)}</div>}
      {tab === "playlists" && <div className="manage-list">{playlists.map((playlist) => <div className="manage-block" key={playlist.id}><div className="manage-row"><i className={coverClass(playlist.id)}>≋</i><div><strong>{playlist.title}</strong><small>{playlist.is_private ? "private" : "public"} · {playlist.playlist_type}</small></div><div className="row-actions"><button onClick={() => void openPlaylist(playlist.id)}>{playlistTracks[playlist.id] ? "свернуть" : "треки"}</button><button onClick={() => void addTrack(playlist.id)}>＋ трек</button><button onClick={() => setEditor({ type: "playlist", item: playlist })}>изменить</button><button className="danger" onClick={() => void remove("playlists", playlist.id)}>удалить</button></div></div>{playlistTracks[playlist.id] && <div className="playlist-manage-tracks">{playlistTracks[playlist.id].map((row) => <div key={row.track_id}><span>{row.track?.title || row.track_id}</span><button onClick={() => void removePlaylistTrack(playlist.id, row.track_id)}>× убрать</button></div>)}{!playlistTracks[playlist.id].length && <p>Плейлист пуст.</p>}</div>}</div>)}</div>}
    </>}
    {editor && <StudioEditor editor={editor} releases={releases} onClose={() => setEditor(null)} onSaved={(message) => { notify(message); void load(); }} />}
  </section>;
}

function ProfileEditor({ artist, onSaved }: { artist: Artist; onSaved(): Promise<void> }) {
  const { request } = useApi();
  const [error, setError] = useState<string | null>(null);
  return <form className="profile-editor" onSubmit={(event) => { event.preventDefault(); const data = new FormData(event.currentTarget); let social: Record<string, string> | null = null; try { social = JSON.parse(String(data.get("social") || "null")) as Record<string, string> | null; } catch { setError("Социальные ссылки должны быть корректным JSON"); return; } setError(null); void request("/artists/me", { method: "PUT", body: JSON.stringify({ displayed_name: data.get("name"), bio: data.get("bio") || null, social_links: social }) }).then(onSaved).catch((cause: Error) => setError(cause.message)); }}>
    <div className={`profile-avatar ${coverClass(artist.id)}`}>{initials(artist.displayed_name)}</div><div><label>ОТОБРАЖАЕМОЕ ИМЯ<input name="name" defaultValue={artist.displayed_name} required /></label><label>БИОГРАФИЯ<textarea name="bio" defaultValue={artist.bio || ""} rows={7} /></label><label>ССЫЛКИ / JSON<textarea name="social" defaultValue={JSON.stringify(artist.social_links || {}, null, 2)} rows={5} spellCheck={false} /></label>{error && <div className="form-error">{error}</div>}<button className="primary">СОХРАНИТЬ ПРОФИЛЬ →</button></div>
  </form>;
}

function Settings({ user, artist, onLogout, notify }: { user: User; artist: Artist | null; onLogout(): void; notify(message: string): void }) {
  const { request, tokens } = useApi();
  const [deactivated, setDeactivated] = useState(false);
  const logout = async () => { try { if (tokens) await request("/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token: tokens.refresh_token }) }); } finally { onLogout(); } };
  const removeArtist = async () => { if (!confirm("Удалить профиль артиста и связанный с ним контент?")) return; await request("/artists/me", { method: "DELETE" }); notify("Профиль артиста удалён"); window.location.reload(); };
  const softDelete = async () => { if (!confirm("Деактивировать аккаунт? После этого его можно сразу восстановить, пока открыта эта страница.")) return; await request("/users/me", { method: "DELETE" }); setDeactivated(true); notify("Аккаунт деактивирован — доступно восстановление"); };
  const restore = async () => { await request("/users/restore", { method: "POST" }); setDeactivated(false); notify("Аккаунт восстановлен"); };
  const hardDelete = async () => { if (!confirm("Удалить аккаунт навсегда? Это действие необратимо.")) return; await request("/users/permanent", { method: "DELETE" }); onLogout(); };
  return <section className="page-section settings"><div className="page-hero"><span className="micro">IDENTITY / SECURITY</span><h1>Настройки</h1><p>Управление узлом и жизненным циклом аккаунта.</p></div>
    <div className="settings-grid"><article><span className="micro">CURRENT IDENTITY</span><h2>{user.email}</h2><dl><div><dt>USER ID</dt><dd>{user.id}</dd></div><div><dt>ROLE</dt><dd>{user.role}</dd></div><div><dt>STATE</dt><dd>{user.is_active ? "ACTIVE" : "DISABLED"}</dd></div><div><dt>ARTIST</dt><dd>{artist?.displayed_name || "NOT CONNECTED"}</dd></div></dl><button className="ghost" onClick={() => void logout()}>ЗАВЕРШИТЬ СЕССИЮ →</button></article>
      <article className="danger-zone"><span className="micro">DANGER ZONE</span><h2>Разорвать соединение</h2><p>Деактивация обратима, полное удаление — нет. После перезагрузки страницы удалённый аккаунт уже не сможет войти.</p>{artist && !deactivated && <button onClick={() => void removeArtist()}>Удалить только профиль артиста</button>}{deactivated ? <button className="restore" onClick={() => void restore()}>Восстановить аккаунт сейчас</button> : <button onClick={() => void softDelete()}>Деактивировать аккаунт</button>}<button className="danger" onClick={() => void hardDelete()}>Удалить аккаунт навсегда</button></article></div>
  </section>;
}

function Shell({ user, artist, onLogin, onLogout, onArtistChanged }: { user: User | null; artist: Artist | null; onLogin(): void; onLogout(): void; onArtistChanged(): Promise<void> }) {
  const [view, setView] = useState<ViewName>("discover");
  const [selection, setSelection] = useState<EntitySelection | null>(null);
  const [queueOpen, setQueueOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const notify = (message: string) => { setToast(message); window.setTimeout(() => setToast(null), 2800); };
  const onNeedIdentity = () => {
    if (!user) { onLogin(); return; }
    setSelection(null);
    setView("studio");
    notify("Создайте профиль артиста, чтобы участвовать в жизни сети");
  };
  const engagement: EngagementProps = { artist, onNeedIdentity, notify };
  const nav: Array<[ViewName, string, string]> = [["discover", "⌂", "Эфир"], ["artists", "◎", "Артисты"], ["feed", "▤", "Дневники"], ["library", "≋", "Архив"]];
  if (user) nav.push(["studio", "◈", "Студия"], ["settings", "⚙", "Настройки"]);
  return <div className={`site-shell ${user ? "is-authenticated" : ""}`}>
    <div className="crt-lines" />
    <header className="site-header"><NoiseMark /><GlobalSearch onSelect={setSelection} /><div className="header-actions"><span className="live-dot">● ON AIR</span>{user ? <button className="user-chip" onClick={() => setView("settings")}><i className={artist ? coverClass(artist.id) : ""}>{initials(artist?.displayed_name || user.email)}</i><span>{artist?.displayed_name || user.email.split("@")[0]}<small>{artist ? "artist node" : "listener"}</small></span></button> : <button className="primary compact" onClick={onLogin}>ВОЙТИ →</button>}</div></header>
    <aside className="side-nav"><div className="nav-frequency"><span>FREQ</span><strong>19.98</strong><i /></div><nav>{nav.map(([name, icon, label]) => <button key={name} className={view === name ? "active" : ""} onClick={() => setView(name)} title={label}><span>{icon}</span><em>{label}</em></button>)}</nav><div className="nav-footer"><span>NODE<br />{user ? user.id.slice(0, 6).toUpperCase() : "GUEST"}</span><i>●</i></div></aside>
    <main className="main-content">
      {view === "discover" && <Discover onSelect={setSelection} />}
      {view === "artists" && <ArtistsView onSelect={setSelection} />}
      {view === "feed" && <FeedView onSelect={setSelection} />}
      {view === "library" && <LibraryView onSelect={setSelection} engagement={engagement} />}
      {view === "studio" && user && <Studio artist={artist} onArtistChanged={onArtistChanged} notify={notify} />}
      {view === "settings" && user && <Settings user={user} artist={artist} onLogout={onLogout} notify={notify} />}
    </main>
    {user && <button className="queue-toggle" onClick={() => setQueueOpen(!queueOpen)}>≡ <span>ОЧЕРЕДЬ</span></button>}
    {user && queueOpen && <div className="queue-drawer"><button onClick={() => setQueueOpen(false)}>×</button><QueuePanel /></div>}
    {selection && <EntityDetail selection={selection} onClose={() => setSelection(null)} onSelect={setSelection} engagement={engagement} />}
    {toast && <div className="toast">● {toast}</div>}
  </div>;
}

export function App() {
  const [tokens, setTokens] = useState<TokenPair | null>(() => readTokens());
  const [user, setUser] = useState<User | null>(null);
  const [artist, setArtist] = useState<Artist | null>(null);
  const [authOpen, setAuthOpen] = useState(false);
  const [checking, setChecking] = useState(Boolean(tokens));

  const saveTokens = useCallback((next: TokenPair) => { localStorage.setItem(TOKEN_KEY, JSON.stringify(next)); setTokens(next); }, []);
  const logout = useCallback(() => { localStorage.removeItem(TOKEN_KEY); setTokens(null); setUser(null); setArtist(null); }, []);
  const loadArtist = useCallback(async () => {
    if (!tokens) { setArtist(null); return; }
    const response = await fetch(`${API_BASE}/artists/me`, { headers: { Authorization: `Bearer ${tokens.access_token}` } });
    if (response.ok) setArtist(await response.json() as Artist); else if (response.status === 404) setArtist(null);
  }, [tokens]);

  useEffect(() => {
    if (!tokens) { setChecking(false); return; }
    setChecking(true);
    fetch(`${API_BASE}/users/me`, { headers: { Authorization: `Bearer ${tokens.access_token}` } })
      .then(async (response) => { if (!response.ok) throw new ApiError("Сессия истекла", response.status); setUser(await response.json() as User); await loadArtist(); })
      .catch(logout).finally(() => setChecking(false));
  }, [loadArtist, logout, tokens]);

  const tokenProvider = useMemo(() => () => tokens?.access_token || "", [tokens]);
  const content = <ApiProvider tokens={tokens} onTokens={saveTokens} onUnauthorized={logout}>
    <Shell user={user} artist={artist} onLogin={() => setAuthOpen(true)} onLogout={logout} onArtistChanged={loadArtist} />
    {authOpen && <AuthModal onClose={() => setAuthOpen(false)} onAuthenticated={(next) => { saveTokens(next); setAuthOpen(false); }} />}
  </ApiProvider>;
  if (checking) return <div className="splash"><NoiseMark large /><div className="boot-copy">INITIALIZING NODE<span>█</span></div></div>;
  return tokens && user ? <PlaybackProvider apiBaseUrl={API_BASE} getAccessToken={tokenProvider}>{content}<PlayerBar /></PlaybackProvider> : content;
}
