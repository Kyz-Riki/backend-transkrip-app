import re
from urllib.parse import urlparse, parse_qs


def extract_video_id(url: str) -> str | None:
    if not url or not isinstance(url, str):
        return None

    url = url.strip()

    # Try regex for youtu.be short links
    short_match = re.match(
        r"(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})", url
    )
    if short_match:
        return short_match.group(1)

    # Parse the URL for standard formats
    try:
        parsed = urlparse(url)
    except Exception:
        return None

    # Must be a YouTube domain
    hostname = parsed.hostname or ""
    if not any(
        hostname.endswith(domain)
        for domain in ("youtube.com", "youtu.be", "youtube-nocookie.com")
    ):
        return None

    # youtube.com/watch?v=VIDEO_ID
    if parsed.path == "/watch":
        qs = parse_qs(parsed.query)
        video_id = qs.get("v", [None])[0]
        if video_id and re.match(r"^[a-zA-Z0-9_-]{11}$", video_id):
            return video_id

    # /embed/VIDEO_ID, /v/VIDEO_ID, /shorts/VIDEO_ID
    path_match = re.match(
        r"/(?:embed|v|shorts)/([a-zA-Z0-9_-]{11})", parsed.path
    )
    if path_match:
        return path_match.group(1)

    return None
