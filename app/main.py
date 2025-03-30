from fastapi import FastAPI


app = FastAPI(
    title="Be My Assistant API",
    description="API for RAG Chatbot Assistant",
    version="0.1.0"
)

@app.get("/")
async def read_root():
    """
    Endpoint root/utama. Berguna untuk cek status server.
    Mengembalikan pesan selamat datang sederhana dalam format JSON.
    """
    # Fungsi ini akan dijalankan ketika ada request GET ke "/"
    # Mengembalikan dictionary Python, FastAPI otomatis mengubahnya jadi JSON response.
    return {"message": "Welcome to Be My Assistant API!"}

@app.get("/health")
async def health_check():
    """
    Endpoint sederhana untuk memeriksa apakah API berjalan dengan baik.
    """
    return {"status": "ok"}