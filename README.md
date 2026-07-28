# YukiNoise
Highload Music Service For Independent Artists

## Run locally

This project uses a `src/` layout, so the package must be installed into the active virtual environment before running Uvicorn.

```bash
./venv/bin/pip install -e .
./venv/bin/uvicorn yn.main:app --host 0.0.0.0 --reload
```

## Media uploads

- Track uploads now accept only `mp3` and `wav` files.
- Track ingestion is queued through Taskiq; run the worker with `taskiq worker yn.tasks:broker`.
- Release covers are queued through Taskiq and uploaded to MinIO in the worker.
- Scheduled releases are handled by the Taskiq scheduler; run it with `taskiq scheduler yn.tasks.scheduler:scheduler yn.tasks`.

## Player module

The Spotify-style player API is available below `/me/player`. Live state and queue
snapshots are stored in Redis; PostgreSQL stores the aggregate track play count.

The reusable React/TypeScript player and its demo are in `frontend/`:

```bash
cd frontend
npm install --ignore-scripts
npm run dev
```

Set `yukinoise.demo.access-token` in browser local storage before opening the demo.
The API allows `http://localhost:5173` by default; override `CORS_ORIGINS` with a
comma-separated list in other environments.

The frontend is also part of Docker Compose and is available at
`http://localhost:5173` after `docker compose up --build`. Nginx serves the static
bundle and proxies same-origin `/api/*` requests and player WebSockets to FastAPI.
The OpenAPI UI is available directly at `http://localhost:8000/docs` and through
the frontend proxy at `http://localhost:5173/api/docs`.
