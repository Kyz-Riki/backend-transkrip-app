from youtube_transcript_api import YouTubeTranscriptApi


def get_transcript(video_id: str) -> str:
    ytt = YouTubeTranscriptApi()

    # Try Indonesian first, then English
    for lang_codes in [["id"], ["en"]]:
        try:
            transcript = ytt.fetch(video_id, languages=lang_codes)
            text_parts = [
                entry["text"] if isinstance(entry, dict) else entry.text
                for entry in transcript
            ]
            full_text = " ".join(text_parts)
            if full_text.strip():
                return full_text
        except Exception:
            continue

    # Fallback: try without specifying language
    try:
        transcript = ytt.fetch(video_id)
        text_parts = [
            entry["text"] if isinstance(entry, dict) else entry.text
            for entry in transcript
        ]
        full_text = " ".join(text_parts)
        if full_text.strip():
            return full_text
    except Exception as e:
        error_name = type(e).__name__
        if "TranscriptsDisabled" in error_name:
            raise ValueError(
                "Transkrip dinonaktifkan untuk video ini. "
                "Video mungkin tidak memiliki subtitle/caption."
            )
        elif "NoTranscriptFound" in error_name:
            raise ValueError(
                "Tidak ada transkrip yang tersedia untuk video ini."
            )
        else:
            raise ValueError(f"Gagal mengambil transkrip: {str(e)}")

    raise ValueError(
        "Tidak ada transkrip yang tersedia untuk video ini "
        "dalam Bahasa Indonesia maupun Inggris."
    )
