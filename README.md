# YukiNoise
Highload Music Service For Independent Artists

## Run locally

This project uses a `src/` layout, so the package must be installed into the active virtual environment before running Uvicorn.

```bash
./venv/bin/pip install -e .
./venv/bin/uvicorn yn.main:app --host 0.0.0.0 --reload
```

## Discovery search and curation

Install the project with Poetry so that PyTorch uses the configured CPU package
source:

```bash
VIRTUAL_ENV="$PWD/venv" ./venv/bin/poetry install
./venv/bin/alembic upgrade head
./venv/bin/python scripts/backfill_track_embeddings.py --dry-run --restart
./venv/bin/python scripts/backfill_track_embeddings.py --restart
```

Backfill builds embeddings for tracks that existed before indexing was enabled.
It processes UUIDs in pages and checkpoints completed pages. Run it again without
`--restart` to resume after a failure; use `--restart` for a fresh scan after a
model/schema change. Dry runs do not load model weights or write vectors/checkpoints.
Only public, nondeleted tracks are indexed. Draft releases remain outside search.

Set `DISCOVERY_ENABLED=true` in the app and worker environment, then restart them.
Run the API, Kafka/outbox publisher, Taskiq worker and scheduler as usual. Track
creation/update/deletion, release description/scheduling/publication, and artist
name/bio changes enqueue indexing through the transactional outbox. Release and
artist events queue related tracks in pages of 100. Hard deletion cascades remove
the corresponding embeddings through foreign keys.

Authenticated endpoints:

- `POST /discovery/search`: `{"query": "ambient для вечера", "limit": 8}`.
- `POST /discovery/curations/preview`: the same request, with `LLM_API_KEY` and
  `LLM_GENERATION_MODEL` configured for Groq.

In the frontend, open **Куратор** and sign in using the normal login dialog.
Enter a mood or instruction, choose the number of tracks, and submit. The answer
includes the curator's explanation for each selected track and playback buttons.
An artist profile is not required.

Keep the Groq key in the ignored `.env` file:

```dotenv
DISCOVERY_ENABLED=true
LLM_API_KEY=your-groq-api-key
LLM_GENERATION_MODEL=openai/gpt-oss-120b
```

The API key identifies your Groq account; the model is chosen separately by its
ID. Restart the API after changing these settings. Docker Compose passes the
settings to the API and enables indexing in the worker and scheduler.

Search runs locally with E5 and does not require a generation API key. The first
model initialization downloads its weights; later calls reuse the local cache.

The regular pytest suite covers checkpoints, event dispatch, transactional event
ordering and rate limiting. To run the PostgreSQL tests, set
`YUKINOISE_TEST_PG_DSN` to a separate disposable PostgreSQL database with pgvector
available, then run `pytest tests/modules/discovery/test_postgres.py`.

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

Sign in through the frontend login dialog to use playback and the curator.
The API allows `http://localhost:5173` by default; override `CORS_ORIGINS` with a
comma-separated list in other environments.

The frontend is also part of Docker Compose and is available at
`http://localhost:5173` after `docker compose up --build`. Nginx serves the static
bundle and proxies same-origin `/api/*` requests and player WebSockets to FastAPI.
The OpenAPI UI is available directly at `http://localhost:8000/docs` and through
the frontend proxy at `http://localhost:5173/api/docs`.
