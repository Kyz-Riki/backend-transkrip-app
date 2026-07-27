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


class ErrorResponse(BaseModel):
    detail: str = Field(description="Pesan error")
