from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router

app = FastAPI(
    title="YouTube Transcript Summarizer",
    description="API untuk meringkas video YouTube menggunakan transkrip dan Gemini AI",
    version="1.0.0",
)

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
