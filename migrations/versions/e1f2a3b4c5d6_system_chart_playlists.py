"""add global system chart playlists

Revision ID: e1f2a3b4c5d6
Revises: d8e4a9b6c201
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d8e4a9b6c201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("playlists", "artist_id", existing_type=sa.UUID(), nullable=True)
    op.add_column("playlists", sa.Column("system_key", sa.String(32), nullable=True))
    op.add_column("playlists", sa.Column("period_start", sa.Date(), nullable=True))
    op.add_column("playlists", sa.Column("period_end", sa.Date(), nullable=True))
    op.create_index(
        "uq_playlists_system_key",
        "playlists",
        ["system_key"],
        unique=True,
        postgresql_where=sa.text("system_key IS NOT NULL"),
    )
    op.add_column(
        "playlist_tracks",
        sa.Column(
            "position", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
    )

    op.execute(
        """
        INSERT INTO playlists
            (id, artist_id, title, description, is_private, playlist_type, system_key)
        VALUES
            ('71000000-0000-4000-8000-000000000001', NULL, 'Топ дня',
             'Самые прослушиваемые треки за завершённый день.', FALSE, 'SYSTEM', 'top_day'),
            ('71000000-0000-4000-8000-000000000002', NULL, 'Топ недели',
             'Самые прослушиваемые треки за завершённую неделю.', FALSE, 'SYSTEM', 'top_week'),
            ('71000000-0000-4000-8000-000000000003', NULL, 'Топ месяца',
             'Самые прослушиваемые треки за завершённый месяц.', FALSE, 'SYSTEM', 'top_month')
        ON CONFLICT DO NOTHING
        """
    )
    op.execute(
        """
        WITH reference AS (
            SELECT (now() AT TIME ZONE 'UTC')::date AS today
        ),
        periods(system_key, period_start, period_end) AS (
            SELECT 'top_day', today - 1, today
            FROM reference
            UNION ALL
            SELECT
                'top_week',
                date_trunc('week', today)::date - 7,
                date_trunc('week', today)::date
            FROM reference
            UNION ALL
            SELECT
                'top_month',
                (date_trunc('month', today)::date - INTERVAL '1 month')::date,
                date_trunc('month', today)::date
            FROM reference
        )
        UPDATE playlists AS playlist
        SET period_start = periods.period_start,
            period_end = periods.period_end,
            updated_at = now()
        FROM periods
        WHERE playlist.system_key = periods.system_key
        """
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT
                playlist.id AS playlist_id,
                metrics.track_id,
                row_number() OVER (
                    PARTITION BY playlist.id
                    ORDER BY sum(metrics.qualified_plays) DESC, metrics.track_id ASC
                ) AS position
            FROM playlists AS playlist
            JOIN track_metrics_daily AS metrics
              ON metrics.bucket_date >= playlist.period_start
             AND metrics.bucket_date < playlist.period_end
            JOIN tracks AS track ON track.id = metrics.track_id
            JOIN releases AS release ON release.id = track.release_id
            WHERE playlist.system_key IS NOT NULL
              AND track.deleted_at IS NULL
              AND release.deleted_at IS NULL
              AND (
                  release.status = 'PUBLISHED'
                  OR (release.status = 'SCHEDULED' AND release.release_date <= now())
              )
            GROUP BY playlist.id, metrics.track_id
            HAVING sum(metrics.qualified_plays) > 0
        )
        INSERT INTO playlist_tracks (playlist_id, track_id, position)
        SELECT playlist_id, track_id, position
        FROM ranked
        WHERE position <= 100
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM playlists WHERE system_key IS NOT NULL")
    op.drop_column("playlist_tracks", "position")
    op.drop_index("uq_playlists_system_key", table_name="playlists")
    op.drop_column("playlists", "period_end")
    op.drop_column("playlists", "period_start")
    op.drop_column("playlists", "system_key")
    op.alter_column("playlists", "artist_id", existing_type=sa.UUID(), nullable=False)
