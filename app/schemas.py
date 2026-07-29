from pydantic import BaseModel, Field


# Auth Schemas
class RegisterRequest(BaseModel):
    email: str = Field(..., description="Email untuk pendaftaran akun", examples=["user@example.com"])
    password: str = Field(..., min_length=6, description="Password minimal 6 karakter")
    username: str = Field(..., min_length=3, max_length=30, description="Username untuk profil publik", examples=["johndoe"])


class LoginRequest(BaseModel):
    email: str = Field(..., description="Email akun", examples=["user@example.com"])
    password: str = Field(..., description="Password akun")


class UserResponse(BaseModel):
    id: str = Field(description="UUID User dari Supabase Auth")
    email: str = Field(description="Email User")
    username: str = Field(default="", description="Username publik")


class AuthResponse(BaseModel):
    access_token: str | None = Field(default=None, description="JWT Access Token dari Supabase")
    refresh_token: str | None = Field(default=None, description="JWT Refresh Token")
    token_type: str = Field(default="bearer", description="Tipe token HTTP Auth")
    user: UserResponse = Field(description="Data profil user yang login")
    message: str | None = Field(default=None, description="Pesan informasi opsional")


# Summary Schemas
class SummarizeRequest(BaseModel):
    url: str = Field(
        ...,
        description="URL video YouTube yang ingin diringkas",
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
    )


class SummarizeResponse(BaseModel):
    id: str | None = Field(default=None, description="ID summary dari database")
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


class SummaryDetailResponse(BaseModel):
    """Response untuk halaman detail ringkasan (publik). Tidak menyertakan transcript mentah."""
    video_id: str = Field(description="ID video YouTube")
    url: str = Field(description="URL video YouTube")
    summary: str = Field(description="Hasil ringkasan dari transkrip video")
    cached: bool = Field(default=True, description="Status apakah hasil diambil dari cache database")
    owner_user_id: str | None = Field(default=None, description="UUID pemilik asli ringkasan")
    owner_username: str = Field(default="", description="Username pemilik asli ringkasan")
    is_owner: bool = Field(default=False, description="Apakah user yang mengakses adalah pemilik ringkasan ini")


class SaveSummaryResponse(BaseModel):
    message: str = Field(description="Pesan sukses penyimpanan")
    video_id: str = Field(description="ID video YouTube yang disimpan")
    user_id: str = Field(description="UUID User yang menyimpannya")


class HistoryResponse(BaseModel):
    total: int = Field(description="Jumlah histori ringkasan")
    items: list[SummaryHistoryItem] = Field(description="Daftar histori ringkasan")


class ErrorResponse(BaseModel):
    detail: str = Field(description="Pesan error")


