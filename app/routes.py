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
        res = register_user(request.email, request.password)
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
            user=UserResponse(id=res.user.id, email=res.user.email or request.email),
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
        return AuthResponse(
            access_token=res.session.access_token,
            refresh_token=res.session.refresh_token,
            user=UserResponse(id=res.user.id, email=res.user.email or request.email),
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
    return UserResponse(
        id=current_user.id,
        email=current_user.email or "",
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

    # 2. Cek Cache Supabase terlebih dahulu
    cached_record = get_summary_by_video_id(video_id)
    if cached_record:
        if user_id and not cached_record.get("user_id"):
            assign_summary_to_user(video_id, user_id)
            cached_record["user_id"] = user_id

        return SummarizeResponse(
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
    save_summary(
        video_id=video_id,
        url=request.url,
        transcript=transcript,
        summary=summary,
        user_id=user_id,
    )

    return SummarizeResponse(
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

    updated = assign_summary_to_user(video_id, current_user.id)
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
    response_model=SummarizeResponse,
    summary="Ambil detail ringkasan berdasarkan video_id",
    description="Mengambil data transkrip dan ringkasan yang tersimpan untuk video ID tertentu.",
    tags=["Summaries"],
)
async def get_summary_detail(video_id: str):
    record = get_summary_by_video_id(video_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Ringkasan untuk video_id '{video_id}' tidak ditemukan di database.",
        )
    return SummarizeResponse(
        video_id=video_id,
        summary=record.get("summary", ""),
        transcript=record.get("transcript", ""),
        cached=True,
        user_id=record.get("user_id"),
    )


