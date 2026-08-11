import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PlaybackProvider } from "./PlaybackProvider";
import { PlayerBar } from "./PlayerBar";
import { QueuePanel } from "./QueuePanel";
import type { PlaybackState } from "./types";

class AudioMock extends EventTarget {
  src = "";
  currentTime = 0;
  play = vi.fn(async () => undefined);
  pause = vi.fn();
}

class WebSocketMock {
  static OPEN = 1;
  onopen: (() => void) | null = null;
  onmessage: (() => void) | null = null;
  onclose: (() => void) | null = null;
  send = vi.fn();
  close = vi.fn();
}

const deviceId = "10000000-0000-4000-8000-000000000001";
const state: PlaybackState = {
  session_id: "20000000-0000-4000-8000-000000000001",
  revision: 1,
  active_device_id: deviceId,
  context: { type: "release", id: "30000000-0000-4000-8000-000000000001" },
  current_track: {
    id: "40000000-0000-4000-8000-000000000001",
    title: "Snowfall",
    duration_ms: 120_000,
    stream_url: "/tracks/40000000-0000-4000-8000-000000000001/stream",
  },
  current_index: 0,
  queue_length: 2,
  attempt_id: "50000000-0000-4000-8000-000000000001",
  heartbeat_sequence: 0,
  position_ms: 30_000,
  is_playing: true,
  repeat_mode: "off",
  listened_ms: 25_000,
  counted: false,
};

describe("PlaybackProvider", () => {
  beforeEach(() => {
    vi.stubGlobal("Audio", AudioMock);
    vi.stubGlobal("WebSocket", WebSocketMock);
  });

  afterEach(() => cleanup());

  it("restores server state and renders the global player", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => state,
    })));

    render(
      <PlaybackProvider apiBaseUrl="http://api.test" getAccessToken={() => "token"} deviceId={deviceId}>
        <PlayerBar />
      </PlaybackProvider>,
    );

    expect(await screen.findByText("Snowfall")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Pause" })).toBeTruthy();
    expect(screen.getByText("0:30")).toBeTruthy();
  });

  it("sends repeat commands with the stable device id", async () => {
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => ({
      ok: true,
      status: 200,
      json: async () => state,
      init,
    }));
    vi.stubGlobal("fetch", fetchMock);
    render(
      <PlaybackProvider apiBaseUrl="http://api.test" getAccessToken={() => "token"} deviceId={deviceId}>
        <PlayerBar />
      </PlaybackProvider>,
    );
    fireEvent.click(await screen.findByRole("button", { name: "Repeat" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/me/player/repeat",
      expect.objectContaining({ body: JSON.stringify({ device_id: deviceId, mode: "context" }) }),
    ));
  });

  it("loads the queue once when playback state becomes available", async () => {
    const fetchMock = vi.fn(async (url: string) => ({
      ok: true,
      status: 200,
      json: async () => url.endsWith("/queue")
        ? { current_index: 0, tracks: [state.current_track] }
        : state,
    }));
    vi.stubGlobal("fetch", fetchMock);

    render(
      <PlaybackProvider apiBaseUrl="http://api.test" getAccessToken={() => "token"} deviceId={deviceId}>
        <QueuePanel />
      </PlaybackProvider>,
    );

    await waitFor(() => {
      const queueRequests = fetchMock.mock.calls.filter(
        ([url]) => url === "http://api.test/me/player/queue",
      );
      expect(queueRequests).toHaveLength(1);
    });
    await new Promise((resolve) => setTimeout(resolve, 20));
    const queueRequests = fetchMock.mock.calls.filter(
      ([url]) => url === "http://api.test/me/player/queue",
    );
    expect(queueRequests).toHaveLength(1);
  });
});
