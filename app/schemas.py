from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    url: str = Field(
        ...,
        description="URL video YouTube yang ingin diringkas",
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
    )


class SummarizeResponse(BaseModel):
    video_id: str = Field(description="ID video YouTube")
    summary: str = Field(description="Hasil ringkasan dari transkrip video")
    transcript: str = Field(description="Transkrip mentah dari video YouTube")
    cached: bool = Field(default=False, description="Status apakah hasil diambil dari cache database")


class SummaryHistoryItem(BaseModel):
    id: str | None = Field(default=None, description="UUID di Supabase")
    video_id: str = Field(description="ID video YouTube")
    url: str = Field(description="URL video YouTube")
    summary: str = Field(description="Hasil ringkasan dari transkrip video")
    created_at: str | None = Field(default=None, description="Timestamp pembuatan")


class HistoryResponse(BaseModel):
    total: int = Field(description="Jumlah histori ringkasan")
    items: list[SummaryHistoryItem] = Field(description="Daftar histori ringkasan")


class ErrorResponse(BaseModel):
    detail: str = Field(description="Pesan error")

