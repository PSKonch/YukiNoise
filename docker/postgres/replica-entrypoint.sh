#!/bin/sh
set -eu

if [ ! -s "$PGDATA/PG_VERSION" ]; then
  : "${POSTGRES_REPLICATION_USER:?POSTGRES_REPLICATION_USER must be set}"
  : "${POSTGRES_REPLICATION_PASSWORD:?POSTGRES_REPLICATION_PASSWORD must be set}"

  until pg_isready -h db -p 5432 -U "$POSTGRES_REPLICATION_USER"; do
    sleep 1
  done

  export PGPASSWORD="$POSTGRES_REPLICATION_PASSWORD"
  pg_basebackup \
    --host=db \
    --port=5432 \
    --username="$POSTGRES_REPLICATION_USER" \
    --pgdata="$PGDATA" \
    --format=plain \
    --wal-method=stream \
    --progress \
    --write-recovery-conf
fi

exec docker-entrypoint.sh "$@"
