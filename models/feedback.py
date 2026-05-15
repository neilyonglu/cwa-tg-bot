import asyncio
from psycopg2.extras import RealDictCursor
from services.db_conn import _db


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
