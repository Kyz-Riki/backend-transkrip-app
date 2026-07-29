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


def register_user(email: str, password: str, username: str = ""):
    """Register user using Supabase Auth with username in user_metadata."""
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase client belum dikonfigurasi. Periksa SUPABASE_URL dan SUPABASE_KEY.")
    return client.auth.sign_up({
        "email": email,
        "password": password,
        "options": {"data": {"username": username}},
    })


def login_user(email: str, password: str):
    """Login user using Supabase Auth."""
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase client belum dikonfigurasi. Periksa SUPABASE_URL dan SUPABASE_KEY.")
    return client.auth.sign_in_with_password({"email": email, "password": password})


def logout_user() -> None:
    """Sign out current user session from Supabase Auth."""
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase client belum dikonfigurasi.")
    client.auth.sign_out()


import jwt


class SimpleUser:
    def __init__(self, user_id: str, email: str = "", username: str = ""):
        self.id = user_id
        self.email = email
        self.username = username


def get_user_from_token(token: str) -> Any | None:
    """Verify JWT access token (locally using SUPABASE_JWT_SECRET if provided, fallback to Supabase API) and return user object."""
    jwt_secret = settings.SUPABASE_JWT_SECRET.strip()
    if jwt_secret:
        try:
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
            user_id = payload.get("sub")
            email = payload.get("email", "")
            user_metadata = payload.get("user_metadata", {})
            username = user_metadata.get("username", "") if isinstance(user_metadata, dict) else ""
            if user_id:
                return SimpleUser(user_id=user_id, email=email, username=username)
        except Exception as e:
            logger.warning(f"Verifikasi lokal JWT (SUPABASE_JWT_SECRET) gagal: {str(e)}. Fallback ke Supabase API.")

    client = get_supabase_client()
    if not client:
        return None

    try:
        res = client.auth.get_user(jwt=token)
        if res and hasattr(res, "user") and res.user:
            user = res.user
            # Wrap Supabase user agar memiliki atribut .username yang konsisten
            metadata = getattr(user, "user_metadata", {}) or {}
            username = metadata.get("username", "")
            return SimpleUser(user_id=user.id, email=user.email or "", username=username)
    except Exception as e:
        logger.warning(f"Gagal verifikasi token Supabase Auth: {str(e)}")

    return None


def get_summary_by_video_id(video_id: str, user_id: str | None = None) -> dict[str, Any] | None:
    """Find existing summary in Supabase by video_id (preferring the user's own if user_id is provided)."""
    client = get_supabase_client()
    if not client:
        return None

    try:
        # First, try to find the user's own record if user_id is provided
        if user_id:
            response = (
                client.table("summaries")
                .select("*")
                .eq("video_id", video_id)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data[0]

        # If not found or no user_id, just get any record
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
    video_id: str, url: str, transcript: str, summary: str,
    user_id: str | None = None, owner_username: str = "",
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
    if owner_username:
        data["owner_username"] = owner_username

    try:
        # Manual check to avoid upsert on_conflict issues since unique constraint on video_id was removed
        query = client.table("summaries").select("id").eq("video_id", video_id)
        if user_id:
            query = query.eq("user_id", user_id)
        else:
            query = query.is_("user_id", "null")
            
        existing = query.limit(1).execute()

        if existing.data and len(existing.data) > 0:
            # Update existing record
            update_query = client.table("summaries").update(data).eq("video_id", video_id)
            if user_id:
                update_query = update_query.eq("user_id", user_id)
            else:
                update_query = update_query.is_("user_id", "null")
            response = update_query.execute()
        else:
            # Insert new record
            response = client.table("summaries").insert(data).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]
    except Exception as e:
        logger.error(f"Error saving summary to Supabase for video_id {video_id}: {str(e)}")

    return None


def assign_summary_to_user(video_id: str, user_id: str, owner_username: str = "") -> dict[str, Any] | None:
    """Assign an existing summary (that has no owner) to a user_id."""
    client = get_supabase_client()
    if not client:
        return None

    try:
        response = (
            client.table("summaries")
            .update({"user_id": user_id, "owner_username": owner_username})
            .eq("video_id", video_id)
            .is_("user_id", "null")
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


def save_summary_for_user(
    video_id: str, url: str, transcript: str, summary: str,
    user_id: str, owner_username: str = "",
) -> dict[str, Any] | None:
    """Save a new summary record specifically owned by a user (for reprocess flow).
    
    Berbeda dari save_summary biasa, fungsi ini selalu meng-insert record baru
    untuk user tertentu. Jika user sudah punya record untuk video ini,
    record tersebut di-update (bukan membuat duplikat).
    """
    client = get_supabase_client()
    if not client:
        return None

    data = {
        "video_id": video_id,
        "url": url,
        "transcript": transcript,
        "summary": summary,
        "user_id": user_id,
        "owner_username": owner_username,
    }

    try:
        # Cek apakah user sudah punya record untuk video ini
        existing = (
            client.table("summaries")
            .select("id")
            .eq("video_id", video_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if existing.data and len(existing.data) > 0:
            # Update record yang sudah ada
            response = (
                client.table("summaries")
                .update({"transcript": transcript, "summary": summary, "updated_at": "now()"})
                .eq("video_id", video_id)
                .eq("user_id", user_id)
                .execute()
            )
        else:
            # Insert record baru
            response = (
                client.table("summaries")
                .insert(data)
                .execute()
            )

        if response.data and len(response.data) > 0:
            return response.data[0]
    except Exception as e:
        logger.error(f"Error saving reprocessed summary for user {user_id}, video {video_id}: {str(e)}")

    return None


def unassign_summary_from_user(video_id: str, user_id: str) -> dict[str, Any] | None:
    """Release ownership of a summary by setting user_id and owner_username to NULL.

    Row tetap ada di tabel sebagai cache konten. Hanya kepemilikan yang dilepas.
    """
    client = get_supabase_client()
    if not client:
        return None

    try:
        response = (
            client.table("summaries")
            .update({"user_id": None, "owner_username": None})
            .eq("video_id", video_id)
            .eq("user_id", user_id)
            .execute()
        )
        if response.data and len(response.data) > 0:
            return response.data[0]
    except Exception as e:
        logger.error(f"Error unassigning summary {video_id} from user {user_id}: {str(e)}")

    return None
