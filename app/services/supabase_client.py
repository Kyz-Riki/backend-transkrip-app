import logging
from typing import Any
from supabase import create_client, Client
from app.config import settings

logger = logging.getLogger("uvicorn.error")

_client: Client | None = None


def get_supabase_client() -> Client | None:
    """Return an initialized Supabase Client if credentials are configured."""
    global _client
    if _client is not None:
        return _client

    url = settings.SUPABASE_URL.strip()
    key = settings.SUPABASE_KEY.strip()

    if not url or not key or "your_supabase" in url or "your_supabase" in key:
        return None

    try:
        _client = create_client(url, key)
        return _client
    except Exception as e:
        logger.warning(f"Gagal inisialisasi Supabase Client: {str(e)}")
        return None


def register_user(email: str, password: str):
    """Register user using Supabase Auth."""
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase client belum dikonfigurasi. Periksa SUPABASE_URL dan SUPABASE_KEY.")
    return client.auth.sign_up({"email": email, "password": password})


def login_user(email: str, password: str):
    """Login user using Supabase Auth."""
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase client belum dikonfigurasi. Periksa SUPABASE_URL dan SUPABASE_KEY.")
    return client.auth.sign_in_with_password({"email": email, "password": password})


def get_user_from_token(token: str) -> Any | None:
    """Verify JWT access token and return user object."""
    client = get_supabase_client()
    if not client:
        return None

    try:
        res = client.auth.get_user(jwt=token)
        if res and hasattr(res, "user") and res.user:
            return res.user
    except Exception as e:
        logger.warning(f"Gagal verifikasi token Supabase Auth: {str(e)}")

    return None


def get_summary_by_video_id(video_id: str) -> dict[str, Any] | None:
    """Find existing summary in Supabase by video_id."""
    client = get_supabase_client()
    if not client:
        return None

    try:
        response = (
            client.table("summaries")
            .select("*")
            .eq("video_id", video_id)
            .limit(1)
            .execute()
        )
        if response.data and len(response.data) > 0:
            return response.data[0]
    except Exception as e:
        logger.error(f"Error fetching summary from Supabase for video_id {video_id}: {str(e)}")

    return None


def save_summary(
    video_id: str, url: str, transcript: str, summary: str, user_id: str | None = None
) -> dict[str, Any] | None:
    """Save or update summary record in Supabase."""
    client = get_supabase_client()
    if not client:
        return None

    data = {
        "video_id": video_id,
        "url": url,
        "transcript": transcript,
        "summary": summary,
    }
    if user_id:
        data["user_id"] = user_id

    try:
        response = (
            client.table("summaries")
            .upsert(data, on_conflict="video_id")
            .execute()
        )
        if response.data and len(response.data) > 0:
            return response.data[0]
    except Exception as e:
        logger.error(f"Error saving summary to Supabase for video_id {video_id}: {str(e)}")

    return None


def assign_summary_to_user(video_id: str, user_id: str) -> dict[str, Any] | None:
    """Assign an existing summary to a user_id."""
    client = get_supabase_client()
    if not client:
        return None

    try:
        response = (
            client.table("summaries")
            .update({"user_id": user_id})
            .eq("video_id", video_id)
            .execute()
        )
        if response.data and len(response.data) > 0:
            return response.data[0]
    except Exception as e:
        logger.error(f"Error assigning summary {video_id} to user {user_id}: {str(e)}")

    return None


def get_all_summaries(limit: int = 50, user_id: str | None = None) -> list[dict[str, Any]]:
    """Retrieve list of recent summaries for history view, optionally filtered by user_id."""
    client = get_supabase_client()
    if not client:
        return []

    try:
        query = client.table("summaries").select("id, video_id, url, summary, user_id, created_at")
        if user_id:
            query = query.eq("user_id", user_id)
        
        response = query.order("created_at", desc=True).limit(limit).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Error fetching summary history from Supabase: {str(e)}")
        return []

