from fastapi import APIRouter, HTTPException

from app.schemas import SummarizeRequest, SummarizeResponse
from app.utils import extract_video_id
from app.services.transcript import get_transcript
from app.services.summarizer import summarize_transcript

router = APIRouter()


@router.post(
    "/summarize",
    response_model=SummarizeResponse,
    summary="Ringkas video YouTube",
    description="Menerima URL video YouTube, mengekstrak transkrip, "
    "dan mengembalikan ringkasan menggunakan Gemini AI.",
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

    # 2. Fetch transcript
    try:
        transcript = get_transcript(video_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 3. Summarize with Gemini
    try:
        summary = summarize_transcript(transcript)
    except ValueError as e:
        # Config error (missing API key)
        raise HTTPException(status_code=500, detail=str(e))
    except RuntimeError as e:
        # Gemini API error
        raise HTTPException(status_code=502, detail=str(e))

    return SummarizeResponse(
        video_id=video_id, summary=summary, transcript=transcript
    )
