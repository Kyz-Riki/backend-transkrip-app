import google.generativeai as genai
from app.config import settings


def _get_model():
    """Configure and return the Gemini generative model."""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel(settings.GEMINI_MODEL)


SUMMARIZE_PROMPT = """\
Kamu adalah asisten AI yang ahli meringkas konten video.
Berikut adalah transkrip dari sebuah video YouTube.

TRANSKRIP:
\"\"\"
{transcript}
\"\"\"

INSTRUKSI:
1. Buat ringkasan yang komprehensif dari transkrip di atas.
2. Gunakan format berikut:
   - **Judul/Topik Utama**: Satu kalimat yang menangkap topik utama video.
   - **Poin-Poin Penting**: Daftar bullet point dari poin-poin kunci (maksimal 7-10 poin).
   - **Ringkasan**: Paragraf ringkasan (2-3 paragraf) yang menjelaskan isi video secara menyeluruh.
3. Jika transkrip dalam Bahasa Inggris, tetap tulis ringkasan dalam Bahasa Indonesia.
4. Jangan menambahkan informasi yang tidak ada di transkrip.
5. Gunakan bahasa yang jelas dan mudah dipahami.
6. jawaban langsung to the point langsung kasih judul, point penting, ringkasanaja gausah ada kalimat seperti berikut adalah ringkasan blablabla
7. jika video tersebut ada sponsor, jangan diringkas bagian sponsornya, kamu bisa skip aja pada bagian sponsor.
8. koreksi juga kata kata mentah dari transkrip ke bahasa yang nyambung dengan pembahasannya, contoh penamaan karakter yang asli, nama orang, nama tempat, dll.
"""


def summarize_transcript(transcript: str) -> str:
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY belum dikonfigurasi. "
            "Silakan isi API key di file .env"
        )

    # Truncate if too long
    if len(transcript) > settings.MAX_TRANSCRIPT_CHARS:
        transcript = transcript[: settings.MAX_TRANSCRIPT_CHARS]
        transcript += "\n\n[...transkrip dipotong karena terlalu panjang...]"

    prompt = SUMMARIZE_PROMPT.format(transcript=transcript)

    try:
        model = _get_model()
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        raise RuntimeError(f"Gagal menghasilkan ringkasan dari Gemini API: {str(e)}")
