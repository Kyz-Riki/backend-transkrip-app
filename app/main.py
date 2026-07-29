from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler as _default_handler
from slowapi.errors import RateLimitExceeded

from app.routes import router
from app.rate_limiter import limiter, rate_limit_exceeded_handler

app = FastAPI(
    title="YouTube Transcript Summarizer",
    description="API untuk meringkas video YouTube menggunakan transkrip dan Gemini AI",
    version="1.0.0",
)

# Rate limiter setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# CORS — allow all origins for development, tighten for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": "YouTube Transcript Summarizer API is running"}
