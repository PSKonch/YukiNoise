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
- Track ingestion is queued through Taskiq; run the worker with `taskiq worker yn.tasks:broker`.
- Album covers are queued through Taskiq and uploaded to MinIO in the worker.
- Scheduled album releases are handled by the Taskiq scheduler; run it with `taskiq scheduler yn.tasks.scheduler:scheduler yn.tasks`.
