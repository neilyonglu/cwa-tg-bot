import asyncio
from services.db_conn import _db

MAX_FAVORITES = 5


async def _ensure_schema():
    def _run():
        with _db() as conn, conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_favorites (
                    id         SERIAL PRIMARY KEY,
                    user_id    BIGINT NOT NULL,
                    name       TEXT NOT NULL,
                    lat        DOUBLE PRECISION NOT NULL,
                    lon        DOUBLE PRECISION NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

    await asyncio.to_thread(_run)


async def get_favorites(user_id: int) -> list:
    def _fetch():
        from psycopg2.extras import RealDictCursor

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
