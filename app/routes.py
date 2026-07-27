from fastapi import APIRouter, HTTPException

from app.schemas import (
    SummarizeRequest,
    SummarizeResponse,
    HistoryResponse,
    SummaryHistoryItem,
)
from app.utils import extract_video_id
from app.services.transcript import get_transcript
from app.services.summarizer import summarize_transcript
from app.services.supabase_client import (
    get_summary_by_video_id,
    save_summary,
    get_all_summaries,
)

router = APIRouter()


@router.post(
    "/summarize",
    response_model=SummarizeResponse,
    summary="Ringkas video YouTube",
    description="Menerima URL video YouTube, mengekstrak transkrip, "
    "dan mengembalikan ringkasan menggunakan Gemini AI (dengan caching Supabase).",
)
async def summarize(request: SummarizeRequest):
    # 1. Extract video ID
    video_id = extract_video_id(request.url)
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="URL YouTube tidak valid. "
            "Gunakan format seperti: https://www.youtube.com/watch?v=VIDEO_ID",
        )

    # 2. Cek Cache Supabase terlebih dahulu
    cached_record = get_summary_by_video_id(video_id)
    if cached_record:
        return SummarizeResponse(
            video_id=video_id,
            summary=cached_record.get("summary", ""),
            transcript=cached_record.get("transcript", ""),
            cached=True,
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
        # Config error (missing API key)
        raise HTTPException(status_code=500, detail=str(e))
    except RuntimeError as e:
        # Gemini API error
        raise HTTPException(status_code=502, detail=str(e))

    # 5. Simpan ke Supabase untuk caching & histori (jika tersambung)
    save_summary(
        video_id=video_id,
        url=request.url,
        transcript=transcript,
        summary=summary,
    )

    return SummarizeResponse(
        video_id=video_id,
        summary=summary,
        transcript=transcript,
        cached=False,
    )


@router.get(
    "/history",
    response_model=HistoryResponse,
    summary="Daftar histori ringkasan",
    description="Mengambil daftar histori ringkasan video yang tersimpan di Supabase.",
)
async def get_history(limit: int = 50):
    records = get_all_summaries(limit=limit)
    items = [
        SummaryHistoryItem(
            id=str(r.get("id")) if r.get("id") else None,
            video_id=r.get("video_id", ""),
            url=r.get("url", ""),
            summary=r.get("summary", ""),
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
    )

