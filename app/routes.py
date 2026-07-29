from typing import Any
from fastapi import APIRouter, HTTPException, Depends, status
from gotrue.errors import AuthApiError

from app.schemas import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    UserResponse,
    SummarizeRequest,
    SummarizeResponse,
    SummaryDetailResponse,
    SaveSummaryResponse,
    HistoryResponse,
    SummaryHistoryItem,
)
from app.deps import get_current_user, get_optional_current_user
from app.utils import extract_video_id
from app.services.transcript import get_transcript
from app.services.summarizer import summarize_transcript
from app.services.supabase_client import (
    register_user,
    login_user,
    logout_user,
    get_summary_by_video_id,
    save_summary,
    save_summary_for_user,
    assign_summary_to_user,
    get_all_summaries,
)

router = APIRouter()


# --------------------------------------------------------------------------
# Auth Endpoints
# --------------------------------------------------------------------------

@router.post(
    "/auth/register",
    response_model=AuthResponse,
    summary="Registrasi user baru",
    description="Mendaftarkan akun baru menggunakan Supabase Auth.",
    tags=["Auth"],
)
async def register(request: RegisterRequest):
    try:
        res = register_user(request.email, request.password, request.username)
        if not res or not res.user:
            raise HTTPException(
                status_code=400,
                detail="Gagal melakukan pendaftaran. Silakan periksa email/password.",
            )
        
        has_session = res.session is not None
        access_token = res.session.access_token if has_session else None
        refresh_token = res.session.refresh_token if has_session else None
        
        msg = "Registrasi berhasil." if has_session else "Registrasi berhasil. Silakan cek email Anda jika verifikasi email diaktifkan pada Supabase."

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse(
                id=res.user.id,
                email=res.user.email or request.email,
                username=request.username,
            ),
            message=msg,
        )
    except AuthApiError as e:
        msg_str = str(e)
        if "User already registered" in msg_str:
            raise HTTPException(status_code=400, detail="Email sudah terdaftar. Silakan login.")
        elif "rate limit" in msg_str.lower():
            raise HTTPException(status_code=429, detail="Terlalu banyak percobaan registrasi (Rate Limit Supabase). Silakan tunggu beberapa menit.")
        elif "invalid" in msg_str.lower() and "email" in msg_str.lower():
            raise HTTPException(status_code=400, detail=f"Email tidak valid / dilarang Supabase: {msg_str}")
        else:
            raise HTTPException(status_code=400, detail=msg_str)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/auth/login",
    response_model=AuthResponse,
    summary="Login user",
    description="Autentikasi user dan mengembalikan JWT access token.",
    tags=["Auth"],
)
async def login(request: LoginRequest):
    try:
        res = login_user(request.email, request.password)
        if not res or not res.session or not res.user:
            raise HTTPException(
                status_code=401,
                detail="Email atau password salah.",
            )
        # Ambil username dari user_metadata Supabase
        metadata = getattr(res.user, 'user_metadata', {}) or {}
        username = metadata.get('username', '')

        return AuthResponse(
            access_token=res.session.access_token,
            refresh_token=res.session.refresh_token,
            user=UserResponse(
                id=res.user.id,
                email=res.user.email or request.email,
                username=username,
            ),
            message="Login berhasil.",
        )
    except AuthApiError as e:
        msg_str = str(e)
        if "Invalid login credentials" in msg_str:
            raise HTTPException(status_code=401, detail="Email atau password salah.")
        elif "Email not confirmed" in msg_str:
            raise HTTPException(status_code=401, detail="Email Anda belum dikonfirmasi. Silakan periksa email Anda.")
        else:
            raise HTTPException(status_code=400, detail=msg_str)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Gagal login: {str(e)}",
        )


@router.get(
    "/auth/me",
    response_model=UserResponse,
    summary="Dapatkan info user yang sedang login",
    description="Mengambil profil user terautentikasi berdasarkan Bearer Token.",
    tags=["Auth"],
)
async def get_me(current_user: Any = Depends(get_current_user)):
    username = getattr(current_user, 'username', '') or ''
    return UserResponse(
        id=current_user.id,
        email=current_user.email or "",
        username=username,
    )


@router.post(
    "/auth/logout",
    summary="Logout user",
    description="Menghapus session user yang sedang login di Supabase Auth.",
    tags=["Auth"],
)
async def logout(current_user: Any = Depends(get_current_user)):
    try:
        logout_user()
        return {"message": "Logout berhasil."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal logout: {str(e)}")


# --------------------------------------------------------------------------
# Summaries & History Endpoints
# --------------------------------------------------------------------------

@router.post(
    "/summarize",
    response_model=SummarizeResponse,
    summary="Ringkas video YouTube",
    description="Menerima URL video YouTube, mengekstrak transkrip, "
    "dan mengembalikan ringkasan menggunakan Gemini AI (dengan caching Supabase).",
    tags=["Summaries"],
)
async def summarize(
    request: SummarizeRequest,
    current_user: Any | None = Depends(get_optional_current_user),
):
    # 1. Extract video ID
    video_id = extract_video_id(request.url)
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="URL YouTube tidak valid. "
            "Gunakan format seperti: https://www.youtube.com/watch?v=VIDEO_ID",
        )

    user_id = current_user.id if current_user else None
    owner_username = getattr(current_user, 'username', '') if current_user else ''

    # 2. Cek Cache Supabase terlebih dahulu
    cached_record = get_summary_by_video_id(video_id, user_id)
    if cached_record:
        return SummarizeResponse(
            id=cached_record.get("id"),
            video_id=video_id,
            summary=cached_record.get("summary", ""),
            transcript=cached_record.get("transcript", ""),
            cached=True,
            user_id=cached_record.get("user_id"),
        )

    # 3. Fetch transcript dari YouTube
    try:
        transcript = get_transcript(video_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 4. Summarize dengan Gemini AI
    try:
        summary = summarize_transcript(transcript)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # 5. Simpan ke Supabase untuk caching & histori
    saved_record = save_summary(
        video_id=video_id,
        url=request.url,
        transcript=transcript,
        summary=summary,
        user_id=user_id,
        owner_username=owner_username or '',
    )

    summary_id = saved_record.get("id") if saved_record else None

    return SummarizeResponse(
        id=summary_id,
        video_id=video_id,
        summary=summary,
        transcript=transcript,
        cached=False,
        user_id=user_id,
    )


@router.post(
    "/summaries/{video_id}/save",
    response_model=SaveSummaryResponse,
    summary="Simpan summary ke akun user",
    description="Menghubungkan ringkasan video ke akun user yang sedang login.",
    tags=["Summaries"],
)
async def save_summary_to_user_account(
    video_id: str,
    current_user: Any = Depends(get_current_user),
):
    record = get_summary_by_video_id(video_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Ringkasan untuk video_id '{video_id}' tidak ditemukan.",
        )

    owner_username = getattr(current_user, 'username', '') or ''
    
    # Jika record tidak punya pemilik (dibuat oleh guest), assign ke user ini
    if record.get("user_id") is None:
        updated = assign_summary_to_user(video_id, current_user.id, owner_username)
    else:
        # Jika record dimiliki orang lain, buat copy baru untuk user ini
        updated = save_summary_for_user(
            video_id=video_id,
            url=record.get("url", ""),
            transcript=record.get("transcript", ""),
            summary=record.get("summary", ""),
            user_id=current_user.id,
            owner_username=owner_username,
        )

    if not updated:
        raise HTTPException(
            status_code=500,
            detail="Gagal menyimpan ringkasan ke akun user.",
        )

    return SaveSummaryResponse(
        message="Ringkasan berhasil disimpan ke akun Anda.",
        video_id=video_id,
        user_id=current_user.id,
    )


@router.get(
    "/history",
    response_model=HistoryResponse,
    summary="Daftar histori ringkasan",
    description="Mengambil daftar histori ringkasan video. Jika disertai Bearer Token, mengembalikan histori khusus milik user.",
    tags=["Summaries"],
)
async def get_history(
    limit: int = 50,
    current_user: Any | None = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    records = get_all_summaries(limit=limit, user_id=user_id)
    items = [
        SummaryHistoryItem(
            id=str(r.get("id")) if r.get("id") else None,
            video_id=r.get("video_id", ""),
            url=r.get("url", ""),
            summary=r.get("summary", ""),
            user_id=r.get("user_id"),
            created_at=str(r.get("created_at")) if r.get("created_at") else None,
        )
        for r in records
    ]
    return HistoryResponse(total=len(items), items=items)


@router.get(
    "/summaries/{video_id}",
    response_model=SummaryDetailResponse,
    summary="Ambil detail ringkasan berdasarkan video_id (publik)",
    description="Mengambil ringkasan yang tersimpan untuk video ID tertentu. "
    "Tidak memerlukan login. Menyertakan info kepemilikan jika token disertakan.",
    tags=["Summaries"],
)
async def get_summary_detail(
    video_id: str,
    current_user: Any | None = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    record = get_summary_by_video_id(video_id, user_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Ringkasan untuk video_id '{video_id}' tidak ditemukan di database.",
        )

    # Tentukan status kepemilikan
    owner_user_id = record.get("user_id")
    is_owner = False
    if current_user and owner_user_id:
        is_owner = str(current_user.id) == str(owner_user_id)

    # Kembalikan response TANPA transcript mentah
    return SummaryDetailResponse(
        video_id=video_id,
        url=record.get("url", ""),
        summary=record.get("summary", ""),
        cached=True,
        owner_user_id=owner_user_id,
        owner_username=record.get("owner_username", "") or "",
        is_owner=is_owner,
    )


@router.post(
    "/summaries/{video_id}/reprocess",
    response_model=SummarizeResponse,
    summary="Proses ulang ringkasan video ke akun sendiri",
    description="Mengambil transkrip dari YouTube dan membuat ringkasan baru "
    "yang tersimpan sebagai milik user yang sedang login. "
    "Tidak memindahkan kepemilikan data lama.",
    tags=["Summaries"],
)
async def reprocess_summary(
    video_id: str,
    current_user: Any = Depends(get_current_user),
):
    # 1. Ambil URL dari record yang sudah ada (bisa record milik siapapun)
    existing = get_summary_by_video_id(video_id)
    if not existing:
        raise HTTPException(
            status_code=404,
            detail=f"Ringkasan untuk video_id '{video_id}' tidak ditemukan.",
        )

    url = existing.get("url", "")
    if not url:
        raise HTTPException(
            status_code=400,
            detail="URL video tidak tersedia untuk diproses ulang.",
        )

    # 2. Fetch transcript dari YouTube
    try:
        transcript = get_transcript(video_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 3. Summarize ulang dengan Gemini AI
    try:
        summary = summarize_transcript(transcript)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # 4. Simpan sebagai record milik user ini (bukan menimpa record lama)
    owner_username = getattr(current_user, 'username', '') or ''
    saved_record = save_summary_for_user(
        video_id=video_id,
        url=url,
        transcript=transcript,
        summary=summary,
        user_id=current_user.id,
        owner_username=owner_username,
    )

    summary_id = saved_record.get("id") if saved_record else None

    return SummarizeResponse(
        id=summary_id,
        video_id=video_id,
        summary=summary,
        transcript=transcript,
        cached=False,
        user_id=current_user.id,
    )

