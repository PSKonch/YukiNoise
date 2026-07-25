#!/bin/sh
set -eu

: "${POSTGRES_REPLICATION_USER:?POSTGRES_REPLICATION_USER must be set}"
: "${POSTGRES_REPLICATION_PASSWORD:?POSTGRES_REPLICATION_PASSWORD must be set}"

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=ON_ERROR_STOP=1 \
  --set=replication_user="$POSTGRES_REPLICATION_USER" \
  --set=replication_password="$POSTGRES_REPLICATION_PASSWORD" <<'SQL'
CREATE ROLE :"replication_user" WITH REPLICATION LOGIN PASSWORD :'replication_password';
SQL
