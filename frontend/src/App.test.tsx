import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

const artist = {
  id: "10000000-0000-4000-8000-000000000001",
  user_id: "20000000-0000-4000-8000-000000000001",
  displayed_name: "Dead Waltz",
  bio: "Noise from a cold room",
  social_links: null,
  created_at: "2026-08-01T12:00:00Z",
  updated_at: "2026-08-01T12:00:00Z",
};

const track = {
  id: "30000000-0000-4000-8000-000000000001",
  release_id: "40000000-0000-4000-8000-000000000001",
  title: "Asphyxia",
  duration_seconds: 142,
  track_number_in_release: 1,
  genres: ["breakcore"],
  path: "/audio/asphyxia.mp3",
};

const release = {
  id: track.release_id,
  artist_id: artist.id,
  title: "Afterimage",
  description: "A short transmission from the archive.",
  cover_path: null,
  release_type: "single",
  status: "published",
  release_date: "2026-08-02T12:00:00Z",
  created_at: "2026-08-01T12:00:00Z",
  updated_at: "2026-08-02T12:00:00Z",
  deleted_at: null,
  author_name: artist.displayed_name,
  tracks: [track],
};

const post = {
  id: "50000000-0000-4000-8000-000000000001",
  artist_id: artist.id,
  title: "Как появился Afterimage",
  content: "Небольшая заметка о записи релиза.",
  author_name: artist.displayed_name,
  created_at: "2026-08-03T12:00:00Z",
  updated_at: "2026-08-03T12:00:00Z",
  deleted_at: null,
};

function response(payload: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  } as Response;
}

describe("App discovery", () => {
  beforeEach(() => {
    const storage = new Map<string, string>();
    vi.stubGlobal("localStorage", {
      clear: () => storage.clear(),
      getItem: (key: string) => storage.get(key) ?? null,
      removeItem: (key: string) => storage.delete(key),
      setItem: (key: string, value: string) => storage.set(key, value),
    });
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/releases/with-tracks-and-author")) return response([release]);
      if (url.includes("/artists/")) return response([artist]);
      if (url.includes("/posts/") && url.includes("/commentaries")) return response([{
        id: "60000000-0000-4000-8000-000000000001",
        artist_id: artist.id,
        post_id: post.id,
        commentary_id: null,
        content: "Ждём полный альбом.",
        author_name: artist.displayed_name,
        created_at: "2026-08-04T12:00:00Z",
        updated_at: "2026-08-04T12:00:00Z",
      }]);
      if (url.includes("/posts/")) return response([post]);
      throw new Error(`Unexpected request: ${url}`);
    }));
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows a data-driven broadcast instead of the decorative radar", async () => {
    const { container } = render(<App />);

    expect(await screen.findByRole("heading", { name: "Сейчас в эфире" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: release.title })).toBeTruthy();
    expect(screen.queryByText("СЛУШАЙ")).toBeNull();
    expect(container.querySelector(".orb")).toBeNull();
  });

  it("opens the new commentary thread from a post", async () => {
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: new RegExp(post.title) }));

    expect(await screen.findByRole("heading", { name: "Комментарии · 1" })).toBeTruthy();
    expect(screen.getByText("Ждём полный альбом.")).toBeTruthy();
    expect(screen.getByPlaceholderText("Добавить комментарий...")).toBeTruthy();
  });
});
