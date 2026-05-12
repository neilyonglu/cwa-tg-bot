import os
import asyncio
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL")
MAX_FAVORITES = 5


@contextmanager
def _db():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── 喜愛點 ──────────────────────────────────────────────────────────

async def get_favorites(user_id: int) -> list:
    def _fetch():
        with _db() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, name, lat, lon FROM user_favorites"
                " WHERE user_id = %s ORDER BY created_at",
                (user_id,),
            )
            return [dict(r) for r in cur.fetchall()]
    return await asyncio.to_thread(_fetch)


async def add_favorite(user_id: int, name: str, lat: float, lon: float) -> dict:
    existing = await get_favorites(user_id)
    if len(existing) >= MAX_FAVORITES:
        return {"error": "limit_exceeded"}
    if any(f["name"] == name for f in existing):
        return {"error": "duplicate"}

    def _insert():
        with _db() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_favorites (user_id, name, lat, lon) VALUES (%s, %s, %s, %s)",
                (user_id, name, lat, lon),
            )
    await asyncio.to_thread(_insert)
    return {"data": "ok"}


async def delete_favorite(fav_id: int, user_id: int) -> None:
    def _delete():
        with _db() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_favorites WHERE id = %s AND user_id = %s",
                (fav_id, user_id),
            )
    await asyncio.to_thread(_delete)


# ── 回饋 ────────────────────────────────────────────────────────────

async def add_feedback(user_id: int, username: str, text: str) -> None:
    def _insert():
        with _db() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO feedback (user_id, username, text) VALUES (%s, %s, %s)",
                (user_id, username or "", text),
            )
    await asyncio.to_thread(_insert)


async def get_all_feedback() -> list:
    def _fetch():
        with _db() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, user_id, username, text, created_at"
                " FROM feedback ORDER BY created_at DESC LIMIT 20"
            )
            return [dict(r) for r in cur.fetchall()]
    return await asyncio.to_thread(_fetch)


async def delete_feedback_item(feedback_id: int) -> None:
    def _delete():
        with _db() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM feedback WHERE id = %s", (feedback_id,))
    await asyncio.to_thread(_delete)


# ── 使用者追蹤 ───────────────────────────────────────────────────────

async def save_user(user_id: int, username: str) -> None:
    def _upsert():
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
            cur.execute(
                "INSERT INTO users (user_id, username) VALUES (%s, %s)"
                " ON CONFLICT (user_id) DO NOTHING",
                (user_id, username or ""),
            )
    await asyncio.to_thread(_upsert)


async def toggle_subscription(user_id: int) -> bool:
    """切換訂閱狀態，回傳切換後的新狀態。"""
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
