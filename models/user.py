import asyncio
from services.db_conn import _db


async def _ensure_schema():
    def _run():
        with _db() as conn, conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id    BIGINT PRIMARY KEY,
                    username   TEXT,
                    subscribed BOOLEAN DEFAULT FALSE,
                    first_seen TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS subscribed BOOLEAN DEFAULT FALSE"
            )
    await asyncio.to_thread(_run)


async def save_user(user_id: int, username: str) -> None:
    def _upsert():
        with _db() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (user_id, username) VALUES (%s, %s)"
                " ON CONFLICT (user_id) DO NOTHING",
                (user_id, username or ""),
            )
    await asyncio.to_thread(_upsert)


async def toggle_subscription(user_id: int) -> bool:
    def _toggle():
        with _db() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET subscribed = NOT subscribed"
                " WHERE user_id = %s RETURNING subscribed",
                (user_id,),
            )
            row = cur.fetchone()
            return bool(row[0]) if row else False
    return await asyncio.to_thread(_toggle)


async def get_subscription_status(user_id: int) -> bool:
    def _fetch():
        with _db() as conn, conn.cursor() as cur:
            cur.execute("SELECT subscribed FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return bool(row[0]) if row else False
    return await asyncio.to_thread(_fetch)


async def get_subscribed_user_ids() -> list[int]:
    def _fetch():
        with _db() as conn, conn.cursor() as cur:
            cur.execute("SELECT user_id FROM users WHERE subscribed = TRUE")
            return [row[0] for row in cur.fetchall()]
    try:
        return await asyncio.to_thread(_fetch)
    except Exception:
        return []
