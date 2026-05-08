import os
import asyncio
import requests as _req

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
MAX_FAVORITES = 5

_BASE = lambda: f"{SUPABASE_URL}/rest/v1"
_HEADERS = lambda: {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


async def get_favorites(user_id: int) -> list:
    def _fetch():
        r = _req.get(
            f"{_BASE()}/user_favorites",
            headers=_HEADERS(),
            params={"user_id": f"eq.{user_id}", "order": "created_at"},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    return await asyncio.to_thread(_fetch)


async def add_favorite(user_id: int, name: str, lat: float, lon: float) -> dict:
    existing = await get_favorites(user_id)
    if len(existing) >= MAX_FAVORITES:
        return {"error": "limit_exceeded"}
    for fav in existing:
        if fav["name"] == name:
            return {"error": "duplicate"}

    def _insert():
        r = _req.post(
            f"{_BASE()}/user_favorites",
            headers=_HEADERS(),
            json={"user_id": user_id, "name": name, "lat": lat, "lon": lon},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    data = await asyncio.to_thread(_insert)
    return {"data": data}


async def delete_favorite(fav_id: int, user_id: int) -> None:
    def _delete():
        r = _req.delete(
            f"{_BASE()}/user_favorites",
            headers=_HEADERS(),
            params={"id": f"eq.{fav_id}", "user_id": f"eq.{user_id}"},
            timeout=10,
        )
        r.raise_for_status()
    await asyncio.to_thread(_delete)
