import asyncio
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from services.db_conn import _db


async def _ensure_schema():
    def _run():
        with _db() as conn, conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS radar_frames (
                    station_key  TEXT NOT NULL,
                    img_time     TIMESTAMP NOT NULL,
                    img_bytes    BYTEA NOT NULL,
                    fetched_at   TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (station_key, img_time)
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_radar_frames_st_time
                    ON radar_frames (station_key, img_time DESC)
            """)
    await asyncio.to_thread(_run)


async def save_frame(station_key: str, img_time: datetime, img_bytes: bytes) -> bool:
    def _insert():
        with _db() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO radar_frames (station_key, img_time, img_bytes)"
                " VALUES (%s, %s, %s)"
                " ON CONFLICT (station_key, img_time) DO NOTHING"
                " RETURNING station_key",
                (station_key, img_time, psycopg2.Binary(img_bytes)),
            )
            return cur.fetchone() is not None
    return await asyncio.to_thread(_insert)


async def get_recent_frames(station_key: str, limit: int = 5) -> list[dict]:
    def _fetch():
        with _db() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT img_time, img_bytes FROM radar_frames"
                " WHERE station_key = %s"
                " ORDER BY img_time DESC LIMIT %s",
                (station_key, limit),
            )
            return [
                {"img_time": row["img_time"], "img_bytes": bytes(row["img_bytes"])}
                for row in cur.fetchall()
            ]
    return await asyncio.to_thread(_fetch)


async def trim_keep_n(station_key: str, keep: int = 5) -> int:
    def _delete():
        with _db() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM radar_frames"
                " WHERE station_key = %s"
                "   AND img_time < ("
                "     SELECT MIN(img_time) FROM ("
                "       SELECT img_time FROM radar_frames"
                "       WHERE station_key = %s"
                "       ORDER BY img_time DESC LIMIT %s"
                "     ) t"
                "   )",
                (station_key, station_key, keep),
            )
            return cur.rowcount
    return await asyncio.to_thread(_delete)
