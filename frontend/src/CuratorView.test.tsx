import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiProvider } from "./api";
import { CuratorView } from "./CuratorView";

const playContext = vi.hoisted(() => vi.fn(async () => undefined));
vi.mock("./PlaybackProvider", () => ({ usePlaybackOptional: () => ({ state: null, playContext }) }));

const curation = {
  title: "Холодный вечер", summary: "Музыка для ночной прогулки.",
  tracks: [{ track_id: "track-yuki", reason: "Зимняя атмосфера подходит для уединения.", sources: ["release.description"] }],
};
const track = { id: "track-yuki", release_id: "release-yuki", title: "Yuki", genres: ["breakcore"], duration_seconds: 129 };

function response(payload: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => payload } as Response;
}

function mount(authenticated = true) {
  const onLogin = vi.fn();
  render(<ApiProvider tokens={authenticated ? { access_token: "access", refresh_token: "refresh", token_type: "bearer" } : null} onTokens={vi.fn()} onUnauthorized={vi.fn()}><CuratorView onLogin={onLogin} /></ApiProvider>);
  return onLogin;
}

function submit(query = "Холодная музыка для прогулки") {
  fireEvent.change(screen.getByLabelText("ВАШ ЗАПРОС"), { target: { value: query } });
  fireEvent.click(screen.getByRole("button", { name: "ПОЛУЧИТЬ ПОДБОРКУ →" }));
}

describe("CuratorView", () => {
  beforeEach(() => {
    playContext.mockClear();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/curations/preview")) return response(curation);
      if (url.endsWith("/tracks/track-yuki")) return response(track);
      if (url.endsWith("/releases/release-yuki/with-tracks-and-author")) return response({ title: "Yuki", author_name: "Dead Waltz" });
      throw new Error(`Unexpected request: ${url}`);
    }));
  });
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

  it("requires sign-in before sending a curator request", () => {
    const onLogin = mount(false);
    fireEvent.click(screen.getByRole("button", { name: "ВОЙТИ И ПОПРОБОВАТЬ →" }));
    expect(onLogin).toHaveBeenCalledOnce();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("normalizes the instruction, sends the chosen limit and renders playable explanations", async () => {
    mount();
    fireEvent.change(screen.getByLabelText("ТРЕКОВ"), { target: { value: "3" } });
    submit("  Холодная   музыка\nдля прогулки  ");
    expect(await screen.findByText("Dead Waltz · Yuki · 2:09")).toBeTruthy();
    expect(screen.getByRole("heading", { name: curation.title })).toBeTruthy();
    expect(screen.getByText(curation.tracks[0].reason)).toBeTruthy();
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(init?.body).toBe(JSON.stringify({ query: "Холодная музыка для прогулки", limit: 3 }));
    expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer access");
    fireEvent.click(screen.getByRole("button", { name: "Слушать Yuki" }));
    await waitFor(() => expect(playContext).toHaveBeenCalledWith({ context: { type: "track", id: "track-yuki" } }));
  });

  it("prevents duplicate submissions while the response is pending", async () => {
    let complete!: (value: Response) => void;
    vi.mocked(fetch).mockImplementationOnce(() => new Promise((resolve) => { complete = resolve; }));
    mount(); submit();
    const pending = screen.getByRole("button", { name: "ПОДБИРАЕМ МУЗЫКУ…" }) as HTMLButtonElement;
    expect(pending.disabled).toBe(true);
    fireEvent.click(pending);
    expect(fetch).toHaveBeenCalledOnce();
    complete(response({ title: "Нет совпадений", summary: "", tracks: [] }));
    expect(await screen.findByText("Подходящих треков пока нет")).toBeTruthy();
  });

  it("keeps the query and allows retrying after a provider failure", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(response({ detail: "Provider unavailable" }, 503));
    mount(); submit();
    expect((await screen.findByRole("alert")).textContent).toContain("Куратор сейчас недоступен");
    expect((screen.getByLabelText("ВАШ ЗАПРОС") as HTMLTextAreaElement).value).toBe("Холодная музыка для прогулки");
    fireEvent.click(screen.getByRole("button", { name: "ПОЛУЧИТЬ ПОДБОРКУ →" }));
    expect(await screen.findByText("Dead Waltz · Yuki · 2:09")).toBeTruthy();
  });

  it("preserves the answer when a selected track becomes unavailable", async () => {
    vi.mocked(fetch).mockImplementation(async (input) => String(input).endsWith("/curations/preview") ? response(curation) : response({ detail: "Not found" }, 404));
    mount(); submit();
    expect(await screen.findByText("Трек недоступен")).toBeTruthy();
    expect(screen.getByText(curation.tracks[0].reason)).toBeTruthy();
    expect((screen.getByRole("button", { name: "Слушать трек" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("offers editable examples and prevents too-short requests", () => {
    mount();
    expect((screen.getByRole("button", { name: "ПОЛУЧИТЬ ПОДБОРКУ →" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: /Холодный атмосферный breakcore/ }));
    expect((screen.getByLabelText("ВАШ ЗАПРОС") as HTMLTextAreaElement).value).toContain("ночной прогулки");
    expect(fetch).not.toHaveBeenCalled();
  });
});
