# YukiNoise
Highload Music Service For Independent Artists

## Run locally

This project uses a `src/` layout, so the package must be installed into the active virtual environment before running Uvicorn.

```bash
./venv/bin/pip install -e .
./venv/bin/uvicorn yn.main:app --reload
```

## Media uploads

- Track uploads now accept only `mp3` and `wav` files.
- Track ingestion is queued through Taskiq; run the worker with `taskiq worker yn.tasks.track_upload:broker`.
- Album covers are uploaded separately through `PATCH /albums/{album_id}/picture`.
