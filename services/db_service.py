import os
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL")
MAX_FAVORITES = 5


async def get_favorites(user_id: int) -> list:
    def _fetch():
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, name, lat, lon FROM user_favorites"
                    " WHERE user_id = %s ORDER BY created_at",
                    (user_id,),
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
    return await asyncio.to_thread(_fetch)


async def add_favorite(user_id: int, name: str, lat: float, lon: float) -> dict:
    existing = await get_favorites(user_id)
    if len(existing) >= MAX_FAVORITES:
        return {"error": "limit_exceeded"}
    for fav in existing:
        if fav["name"] == name:
            return {"error": "duplicate"}

    def _insert():
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO user_favorites (user_id, name, lat, lon)"
                    " VALUES (%s, %s, %s, %s)",
                    (user_id, name, lat, lon),
                )
            conn.commit()
        finally:
            conn.close()
    await asyncio.to_thread(_insert)
    return {"data": "ok"}


async def delete_favorite(fav_id: int, user_id: int) -> None:
    def _delete():
        conn = psycopg2.connect(DATABASE_URL)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM user_favorites WHERE id = %s AND user_id = %s",
                    (fav_id, user_id),
                )
            conn.commit()
        finally:
            conn.close()
    await asyncio.to_thread(_delete)
