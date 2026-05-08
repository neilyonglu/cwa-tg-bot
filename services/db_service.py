import os
import asyncio
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
MAX_FAVORITES = 5

_client: Client = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


async def get_favorites(user_id: int) -> list:
    client = _get_client()
    result = await asyncio.to_thread(
        lambda: client.table("user_favorites")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at")
        .execute()
    )
    return result.data


async def add_favorite(user_id: int, name: str, lat: float, lon: float) -> dict:
    existing = await get_favorites(user_id)
    if len(existing) >= MAX_FAVORITES:
        return {"error": "limit_exceeded"}
    for fav in existing:
        if fav["name"] == name:
            return {"error": "duplicate"}
    client = _get_client()
    result = await asyncio.to_thread(
        lambda: client.table("user_favorites")
        .insert({"user_id": user_id, "name": name, "lat": lat, "lon": lon})
        .execute()
    )
    return {"data": result.data}


async def delete_favorite(fav_id: int, user_id: int) -> None:
    client = _get_client()
    await asyncio.to_thread(
        lambda: client.table("user_favorites")
        .delete()
        .eq("id", fav_id)
        .eq("user_id", user_id)
        .execute()
    )
