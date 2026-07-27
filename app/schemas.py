from pydantic import BaseModel, Field


# Auth Schemas
class RegisterRequest(BaseModel):
    email: str = Field(..., description="Email untuk pendaftaran akun", examples=["user@example.com"])
    password: str = Field(..., min_length=6, description="Password minimal 6 karakter")


class LoginRequest(BaseModel):
    email: str = Field(..., description="Email akun", examples=["user@example.com"])
    password: str = Field(..., description="Password akun")


class UserResponse(BaseModel):
    id: str = Field(description="UUID User dari Supabase Auth")
    email: str = Field(description="Email User")


class AuthResponse(BaseModel):
    access_token: str = Field(description="JWT Access Token dari Supabase")
    refresh_token: str | None = Field(default=None, description="JWT Refresh Token")
    token_type: str = Field(default="bearer", description="Tipe token HTTP Auth")
    user: UserResponse = Field(description="Data profil user yang login")


# Summary Schemas
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
    user_id: str | None = Field(default=None, description="UUID User pemilik ringkasan jika tersimpan")


class SummaryHistoryItem(BaseModel):
    id: str | None = Field(default=None, description="UUID di Supabase")
    video_id: str = Field(description="ID video YouTube")
    url: str = Field(description="URL video YouTube")
    summary: str = Field(description="Hasil ringkasan dari transkrip video")
    user_id: str | None = Field(default=None, description="UUID User pemilik ringkasan")
    created_at: str | None = Field(default=None, description="Timestamp pembuatan")


class SaveSummaryResponse(BaseModel):
    message: str = Field(description="Pesan sukses penyimpanan")
    video_id: str = Field(description="ID video YouTube yang disimpan")
    user_id: str = Field(description="UUID User yang menyimpannya")


class HistoryResponse(BaseModel):
    total: int = Field(description="Jumlah histori ringkasan")
    items: list[SummaryHistoryItem] = Field(description="Daftar histori ringkasan")


class ErrorResponse(BaseModel):
    detail: str = Field(description="Pesan error")


