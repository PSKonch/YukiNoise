import { type ReactNode, useCallback, useEffect, useRef, useState } from "react";
import { useApi } from "./api";
import type { Release, ReleaseFeedPage } from "./models";

function releaseDate(release: Release): string {
  const value = release.release_date || release.created_at;
  if (!value) return "без даты";
  const utc = /(?:Z|[+-]\d\d:\d\d)$/.test(value) ? value : `${value}Z`;
  return new Intl.DateTimeFormat("ru", { day: "numeric", month: "short", year: "numeric" }).format(new Date(utc));
}

export function FollowingFeed({ hasArtist, renderRelease, onBrowse, onCreateArtist }: {
  hasArtist: boolean;
  renderRelease(release: Release): ReactNode;
  onBrowse(): void;
  onCreateArtist(): void;
}) {
  const { request } = useApi();
  const [items, setItems] = useState<Release[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  const nextOffset = useRef(0);

  const load = useCallback(async (offset: number) => {
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    setBusy(true);
    setError(null);
    try {
      const page = await request<ReleaseFeedPage>(`/me/feed/releases?limit=12&offset=${offset}`, { signal: abort.signal });
      if (abort.signal.aborted) return;
      nextOffset.current = offset + page.items.length;
      setItems((current) => offset === 0 ? page.items : [...new Map([...current, ...page.items].map((item) => [item.id, item])).values()]);
      setHasMore(page.has_more);
    } catch {
      if (!abort.signal.aborted) setError("Не удалось загрузить релизы. Попробуйте ещё раз.");
    } finally {
      if (!abort.signal.aborted) setBusy(false);
    }
  }, [request]);

  useEffect(() => {
    if (hasArtist) void load(0);
    return () => controller.current?.abort();
  }, [hasArtist, load]);

  return <section className="page-section following-feed">
    <div className="page-hero"><span className="micro">YOUR FREQUENCIES</span><h1>Подписки</h1><p>Новые релизы артистов, за которыми вы следите.</p></div>
    {!hasArtist ? <div className="empty"><span>◎</span><h3>Подключитесь к сообществу</h3><p>Создайте профиль артиста, чтобы подписываться и собирать свою ленту.</p><button className="primary" onClick={onCreateArtist}>СОЗДАТЬ ПРОФИЛЬ →</button></div> : <>
      <div className="following-toolbar"><span>СНАЧАЛА НОВЫЕ</span><button className="ghost" disabled={busy} onClick={() => void load(0)}>Обновить ленту</button></div>
      {error && <div className="form-error" role="alert">{error}<button className="ghost" disabled={busy} onClick={() => void load(nextOffset.current)}>Повторить</button></div>}
      {busy && !items.length && <p role="status">Принимаем новые сигналы…</p>}
      {!busy && !error && !items.length && <div className="empty"><span>∿</span><h3>Пока тихо</h3><p>Подпишитесь на артистов. Их опубликованные релизы появятся здесь.</p><button className="primary" onClick={onBrowse}>НАЙТИ АРТИСТОВ →</button></div>}
      <div className="release-grid">{items.map((release) => <div key={release.id}>{renderRelease(release)}<p className="following-release-date">{release.author_name || "Независимый артист"} · {releaseDate(release)}</p></div>)}</div>
      {hasMore && <button className="ghost following-more" disabled={busy} onClick={() => void load(nextOffset.current)}>{busy ? "Загружаем…" : "Ещё релизы"}</button>}
    </>}
  </section>;
}
