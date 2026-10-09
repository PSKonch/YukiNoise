import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, useApi } from "./api";
import type { AppNotification, NotificationPage, Release } from "./models";

function dateLabel(value: string): string {
  // Backend timestamps use naive UTC. Explicit offsets are already unambiguous.
  const utc = /(?:Z|[+-]\d\d:\d\d)$/.test(value) ? value : `${value}Z`;
  return new Intl.DateTimeFormat("ru", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(utc));
}

export function NotificationBell({ onOpenRelease }: { onOpenRelease(release: Release): void }) {
  const { request } = useApi();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [busy, setBusy] = useState(false);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const root = useRef<HTMLDivElement | null>(null);
  const controller = useRef<AbortController | null>(null);
  const actionController = useRef<AbortController | null>(null);
  const nextOffset = useRef(0);

  const load = useCallback(async (offset = 0) => {
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    setBusy(true);
    setError(null);
    try {
      const page = await request<NotificationPage>(`/notifications?limit=20&offset=${offset}`, { signal: abort.signal });
      if (abort.signal.aborted) return;
      nextOffset.current = offset + page.items.length;
      setItems((current) => offset === 0 ? page.items : [...new Map([...current, ...page.items].map((item) => [item.id, item])).values()]);
      setUnreadCount(page.unread_count);
      setHasMore(page.has_more);
    } catch {
      if (!abort.signal.aborted) setError("Не удалось загрузить уведомления.");
    } finally { if (!abort.signal.aborted) setBusy(false); }
  }, [request]);

  useEffect(() => {
    const abort = new AbortController();
    const refreshCount = async () => {
      if (document.visibilityState === "hidden") return;
      try {
        const result = await request<{ unread_count: number }>("/notifications/unread-count", { signal: abort.signal });
        if (!abort.signal.aborted) setUnreadCount(result.unread_count);
      } catch { /* Keep the last known count during a temporary outage. */ }
    };
    void refreshCount();
    const timer = window.setInterval(() => void refreshCount(), 30_000);
    window.addEventListener("focus", refreshCount);
    document.addEventListener("visibilitychange", refreshCount);
    return () => {
      abort.abort();
      window.clearInterval(timer);
      window.removeEventListener("focus", refreshCount);
      document.removeEventListener("visibilitychange", refreshCount);
    };
  }, [request]);

  useEffect(() => {
    if (open) void load();
    return () => controller.current?.abort();
  }, [open, load]);

  useEffect(() => () => actionController.current?.abort(), []);

  useEffect(() => {
    if (!open) return;
    const closeOutside = (event: MouseEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false); };
    const closeEscape = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", closeOutside);
    document.addEventListener("keydown", closeEscape);
    return () => {
      document.removeEventListener("mousedown", closeOutside);
      document.removeEventListener("keydown", closeEscape);
    };
  }, [open]);

  const act = async (item?: AppNotification) => {
    if (acting) return;
    const abort = new AbortController();
    actionController.current = abort;
    const options = { signal: abort.signal };
    setActing(true);
    setError(null);
    try {
      if (!item) {
        await request("/notifications/read-all", { ...options, method: "POST" });
        if (!abort.signal.aborted) await load();
      } else {
        if (!item.read_at) {
          const updated = await request<AppNotification>(`/notifications/${item.id}/read`, { ...options, method: "PATCH" });
          if (abort.signal.aborted) return;
          setItems((current) => current.map((row) => row.id === item.id ? updated : row));
          const count = await request<{ unread_count: number }>("/notifications/unread-count", options);
          if (abort.signal.aborted) return;
          setUnreadCount(count.unread_count);
        }
        const releaseId = item.release_id || item.payload.release_id;
        if (releaseId) {
          const release = await request<Release>(`/releases/${releaseId}/with-tracks-and-author`, options);
          if (abort.signal.aborted) return;
          onOpenRelease(release);
          setOpen(false);
        }
      }
    } catch (cause) {
      if (!abort.signal.aborted) setError(cause instanceof ApiError && cause.status === 404 ? "Этот релиз больше недоступен." : "Не удалось выполнить действие. Попробуйте ещё раз.");
    } finally { if (!abort.signal.aborted) setActing(false); }
  };

  return <div className="notification-center" ref={root}>
    <button className="notification-bell" aria-label={`Уведомления${unreadCount ? `: ${unreadCount} непрочитанных` : ""}`} aria-expanded={open} aria-controls="notification-panel" onClick={() => setOpen(!open)}>
      <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></svg>
      {unreadCount > 0 && <span className="notification-count">{unreadCount > 99 ? "99+" : unreadCount}</span>}
    </button>
    {open && <section className="notification-panel" id="notification-panel" aria-label="Центр уведомлений">
      <header><div><span className="micro">INCOMING SIGNALS</span><h2>Уведомления</h2></div><button className="ghost" onClick={() => setOpen(false)} aria-label="Закрыть уведомления">×</button></header>
      <div className="notification-actions"><button className="ghost" disabled={busy || acting} onClick={() => void load()}>Обновить</button><button className="ghost" disabled={!unreadCount || acting || busy} onClick={() => void act()}>Прочитать все</button></div>
      {error && <div className="form-error" role="alert">{error}</div>}
      {busy && !items.length && <p role="status">Загружаем уведомления…</p>}
      {!busy && !error && !items.length && <div className="notification-empty"><strong>Новых сигналов нет</strong><p>Когда у артиста из подписок выйдет релиз, он появится здесь.</p></div>}
      <ul>{items.map((item) => <li key={item.id}><button className={`notification-item ${item.read_at ? "" : "is-unread"}`} disabled={acting} onClick={() => void act(item)}><span className="notification-indicator" /><span><strong>{item.title}</strong><span>{item.message}</span><time dateTime={item.created_at}>{dateLabel(item.created_at)}</time><small>{item.read_at ? "Прочитано" : "Не прочитано"}</small></span><b aria-hidden="true">↗</b></button></li>)}</ul>
      {hasMore && <button className="ghost notification-more" disabled={busy || acting} onClick={() => void load(nextOffset.current)}>{busy ? "Загружаем…" : "Ещё уведомления"}</button>}
    </section>}
  </div>;
}
