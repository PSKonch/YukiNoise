import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiProvider } from "./api";
import { FollowingFeed } from "./FollowingFeed";
import { NotificationBell } from "./NotificationBell";
import type { AppNotification, Release } from "./models";

const tokens = { access_token: "test-access", refresh_token: "test-refresh", token_type: "bearer" };
const release: Release = {
  id: "release-1", artist_id: "artist-1", title: "Winter", description: null,
  cover_path: null, release_type: "album", status: "published", release_date: "2026-10-09T12:00:00",
  created_at: "2026-10-01T12:00:00Z", updated_at: null, deleted_at: null, author_name: "Snow",
};
const notification: AppNotification = {
  id: "notification-1", type: "new_release", title: "Новый релиз", message: "Snow — Winter",
  payload: { release_id: release.id }, release_id: release.id,
  created_at: "2026-10-09T12:00:00", read_at: null,
};

function response(payload: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => payload } as Response;
}

function provider(children: React.ReactNode) {
  return <ApiProvider tokens={tokens} onTokens={vi.fn()} onUnauthorized={vi.fn()}>{children}</ApiProvider>;
}

beforeEach(() => {
  vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("notification center", () => {
  it("shows the badge, marks a message read, and opens its release", async () => {
    let unread = 1;
    const onOpen = vi.fn();
    const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer test-access");
      if (path.endsWith("/unread-count")) return response({ unread_count: unread });
      if (path.includes("/notifications?")) return response({ items: [notification], unread_count: unread, has_more: false });
      if (path.endsWith("/notification-1/read")) {
        expect(init?.method).toBe("PATCH");
        unread = 0;
        return response({ ...notification, read_at: "2026-10-09T12:05:00" });
      }
      if (path.endsWith("/releases/release-1/with-tracks-and-author")) return response(release);
      throw new Error(`Unexpected request ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);
    render(provider(<NotificationBell onOpenRelease={onOpen} />));
    fireEvent.click(await screen.findByRole("button", { name: "Уведомления: 1 непрочитанных" }));
    fireEvent.click(await screen.findByRole("button", { name: /Новый релиз Snow — Winter/ }));
    await waitFor(() => expect(onOpen).toHaveBeenCalledWith(release));
    expect(screen.queryByRole("region", { name: "Центр уведомлений" })).toBeNull();
    expect(screen.getByRole("button", { name: "Уведомления" })).toBeTruthy();
  });

  it("marks all read and reloads both the messages and count", async () => {
    let read = false;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/unread-count")) return response({ unread_count: read ? 0 : 1 });
      if (path.endsWith("/read-all")) { expect(init?.method).toBe("POST"); read = true; return response({ updated_count: 1 }); }
      return response({ items: [{ ...notification, read_at: read ? "2026-10-09T12:05:00Z" : null }], unread_count: read ? 0 : 1, has_more: false });
    }));
    render(provider(<NotificationBell onOpenRelease={vi.fn()} />));
    fireEvent.click(await screen.findByRole("button", { name: "Уведомления: 1 непрочитанных" }));
    await screen.findByText("Snow — Winter");
    fireEvent.click(screen.getByRole("button", { name: "Прочитать все" }));
    expect(await screen.findByText("Прочитано")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Уведомления" })).toBeTruthy();
    expect((screen.getByRole("button", { name: "Прочитать все" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("recovers from a failed load and closes with Escape", async () => {
    let fail = true;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/unread-count")) return response({ unread_count: 0 });
      if (fail) return response({ detail: "Unavailable" }, 503);
      return response({ items: [], unread_count: 0, has_more: false });
    }));
    render(provider(<NotificationBell onOpenRelease={vi.fn()} />));
    fireEvent.click(screen.getByRole("button", { name: "Уведомления" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    fail = false;
    fireEvent.click(screen.getByRole("button", { name: "Обновить" }));
    expect(await screen.findByText("Новых сигналов нет")).toBeTruthy();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("region", { name: "Центр уведомлений" })).toBeNull();
  });

  it("keeps a missing release error visible without navigating", async () => {
    const onOpen = vi.fn();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/unread-count")) return response({ unread_count: 0 });
      if (path.includes("/releases/")) return response({ detail: "Not found" }, 404);
      return response({ items: [{ ...notification, read_at: notification.created_at }], unread_count: 0, has_more: false });
    }));
    render(provider(<NotificationBell onOpenRelease={onOpen} />));
    fireEvent.click(screen.getByRole("button", { name: "Уведомления" }));
    fireEvent.click(await screen.findByRole("button", { name: /Новый релиз Snow — Winter/ }));
    expect(await screen.findByText("Этот релиз больше недоступен.")).toBeTruthy();
    expect(onOpen).not.toHaveBeenCalled();
  });

  it("loads older notifications without losing already displayed messages", async () => {
    const first = Array.from({ length: 20 }, (_, index) => ({ ...notification, id: `note-${index}`, message: `Release ${index}` }));
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/unread-count")) return response({ unread_count: 21 });
      if (path.includes("offset=20")) return response({ items: [{ ...notification, message: "Older release" }], unread_count: 21, has_more: false });
      return response({ items: first, unread_count: 21, has_more: true });
    }));
    render(provider(<NotificationBell onOpenRelease={vi.fn()} />));
    fireEvent.click(screen.getByRole("button", { name: "Уведомления" }));
    fireEvent.click(await screen.findByRole("button", { name: "Ещё уведомления" }));
    expect(await screen.findByText("Older release")).toBeTruthy();
    expect(screen.getByText("Release 0")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Ещё уведомления" })).toBeNull();
  });
});

describe("following release feed", () => {
  function mount(hasArtist = true) {
    const browse = vi.fn();
    const create = vi.fn();
    render(provider(<FollowingFeed hasArtist={hasArtist} onBrowse={browse} onCreateArtist={create} renderRelease={(item) => <article>{item.title}</article>} />));
    return { browse, create };
  }

  it("offers artist setup when the account cannot follow yet", () => {
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    const { create } = mount(false);
    fireEvent.click(screen.getByRole("button", { name: "СОЗДАТЬ ПРОФИЛЬ →" }));
    expect(create).toHaveBeenCalledOnce();
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("guides an empty feed to artist discovery", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => response({ items: [], has_more: false })));
    const { browse } = mount();
    fireEvent.click(await screen.findByRole("button", { name: "НАЙТИ АРТИСТОВ →" }));
    expect(browse).toHaveBeenCalledOnce();
  });

  it("appends the next page and replaces stale results on refresh", async () => {
    let refreshed = false;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (refreshed) return response({ items: [{ ...release, title: "Latest release" }], has_more: false });
      if (path.includes("offset=12")) return response({ items: [{ ...release, id: "older", title: "Older release" }], has_more: false });
      return response({ items: Array.from({ length: 12 }, (_, index) => ({ ...release, id: `release-${index}`, title: `Winter ${index}` })), has_more: true });
    }));
    mount();
    fireEvent.click(await screen.findByRole("button", { name: "Ещё релизы" }));
    expect(await screen.findByText("Older release")).toBeTruthy();
    expect(screen.getByText("Winter 0")).toBeTruthy();
    refreshed = true;
    fireEvent.click(screen.getByRole("button", { name: "Обновить ленту" }));
    expect(await screen.findByText("Latest release")).toBeTruthy();
    expect(screen.queryByText("Older release")).toBeNull();
    expect(screen.queryByText("Winter 0")).toBeNull();
  });

  it("retries a failed feed request", async () => {
    let fail = true;
    vi.stubGlobal("fetch", vi.fn(async () => fail ? response({ detail: "Unavailable" }, 503) : response({ items: [release], has_more: false })));
    mount();
    await screen.findByRole("alert");
    fail = false;
    fireEvent.click(screen.getByRole("button", { name: "Повторить" }));
    expect(await screen.findByText("Winter")).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
