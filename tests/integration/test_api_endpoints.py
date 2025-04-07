# tests/integration/test_api_endpoints.py
import pytest
from fastapi import status # Untuk kode status HTTP
from fastapi.testclient import TestClient # Import client type hint
import os # Untuk path file upload

# Sample file path (pastikan sample.docx ada dan bisa diakses dari root project)
SAMPLE_DOCX_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "sample.docx")
# Cek apakah file sampel ada
if not os.path.exists(SAMPLE_DOCX_PATH):
     pytest.skip("sample.docx not found, skipping upload test", allow_module_level=True)


# Gunakan fixture 'client' dari conftest.py
def test_health_check(client: TestClient):
    """Tes endpoint /health."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ok"
    assert data["embedding_model_loaded"] is True # Asumsi model berhasil load
    assert data["vector_store_initialized"] is True # Asumsi DB berhasil init

def test_upload_document_success(client: TestClient):
    """Tes upload dokumen yang valid (contoh: sample.docx)."""
    assert os.path.exists(SAMPLE_DOCX_PATH), f"Sample file not found at: {SAMPLE_DOCX_PATH}"

    with open(SAMPLE_DOCX_PATH, "rb") as f:
        files = {"file": (os.path.basename(SAMPLE_DOCX_PATH), f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        response = client.post("/api/v1/upload", files=files)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["filename"] == "sample.docx"
    assert data["message"] == "Document processed and added to vector store successfully."
    assert isinstance(data["chunks_added"], int)
    assert data["chunks_added"] > 0 # Harusnya ada chunk dari sample.docx

def test_upload_invalid_file_type(client: TestClient):
    """Tes upload file dengan tipe tidak valid."""
    # Buat file palsu dengan ekstensi tidak didukung
    files = {"file": ("invalid.zip", b"dummy zip content", "application/zip")}
    response = client.post("/api/v1/upload", files=files)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid file type" in response.json()["detail"]

def test_chat_endpoint_no_context(client: TestClient):
    """Tes chat endpoint saat belum ada konteks relevan (misalnya, setelah clear DB)."""
    # Harusnya mengembalikan fallback message dari LLM jika tidak ada konteks
    # (Ini mungkin perlu setup/teardown DB test atau mock RAG)
    response = client.post("/api/v1/chat", json={"question": "Pertanyaan acak tanpa konteks?"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # Assertion ini sangat bergantung pada prompt RAG dan perilaku LLM
    # Mungkin lebih baik mock RAG orchestrator di integration test untuk hasil deterministik
    assert "answer" in data
    # Contoh: assert "Maaf, saya belum bisa" in data["answer"] # Jika prompt Anda menghasilkan ini

def test_chat_endpoint_with_context(client: TestClient):
    """Tes chat setelah dokumen diupload (asumsi upload berhasil sebelumnya)."""
    # Pastikan test_upload_document_success dijalankan SEBELUM ini
    # (pytest biasanya menjalankan sesuai urutan file, tapi bisa dikontrol dg dependencies)

    # Pertanyaan yang relevan dengan sample.docx
    question = "Kapan FiktifCorp Indonesia didirikan?"
    response = client.post("/api/v1/chat", json={"question": question})

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "answer" in data
    # Jawaban harusnya mengandung '2020' berdasarkan sample.docx
    assert "2020" in data["answer"]
    print(f"\nChat response for '{question}': {data['answer']}")

def test_chat_empty_question(client: TestClient):
    """Tes chat dengan pertanyaan kosong."""
    response = client.post("/api/v1/chat", json={"question": ""})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Question cannot be empty" in response.json()["detail"]

def test_delete_context(client: TestClient):
    """Tes menghapus konteks."""
    # 1. Upload dulu (atau pastikan sudah ada dari test sebelumnya)
    #    Untuk keandalan, lebih baik upload di sini lagi
    with open(SAMPLE_DOCX_PATH, "rb") as f:
        files = {"file": ("sample_for_delete.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        upload_resp = client.post("/api/v1/upload", files=files)
        assert upload_resp.status_code == status.HTTP_200_OK

    # 2. Hapus konteks yang baru diupload
    filename_to_delete = "sample_for_delete.docx"
    delete_resp = client.delete(f"/api/v1/delete_context/{filename_to_delete}")
    assert delete_resp.status_code == status.HTTP_204_NO_CONTENT

    # 3. (Opsional) Coba tanya lagi, harusnya konteks sudah hilang
    response_after_delete = client.post("/api/v1/chat", json={"question": "Kapan FiktifCorp Indonesia didirikan?"})
    assert response_after_delete.status_code == status.HTTP_200_OK
    # Harusnya fallback message lagi karena konteks dihapus
    # assert "Maaf, saya belum bisa" in response_after_delete.json()["answer"] # Tergantung fallback Anda

def test_delete_nonexistent_context(client: TestClient):
     """Tes menghapus konteks yang tidak ada."""
     filename_to_delete = "file_yang_tidak_ada.pdf"
     # Meskipun file tidak ada, API delete di ChromaDB tidak error,
     # jadi kita tetap mengharapkan 204 No Content karena perintah delete berhasil dijalankan.
     delete_resp = client.delete(f"/api/v1/delete_context/{filename_to_delete}")
     assert delete_resp.status_code == status.HTTP_204_NO_CONTENT

# --- Test Persona Endpoints ---
def test_get_initial_persona(client: TestClient):
     """Tes mendapatkan persona default."""
     response = client.get("/api/v1/admin/persona")
     assert response.status_code == status.HTTP_200_OK
     data = response.json()
     assert data["ai_name"] == "AI Assistant" # Default dari main.py
     assert data["ai_role"] == "Customer Service AI" # Default
     assert data["ai_tone"] == "friendly, helpful, enthusiastic and engaging" # Default
     assert data["company"] == "-"

def test_set_and_get_persona(client: TestClient):
     """Tes mengubah dan mendapatkan persona."""
     new_persona = {
         "ai_name": "FiktiBot",
         "ai_role": "Sales Assistant",
         "ai_tone": "Profesional dan persuasif",
         "company": "FiktifCorp"
     }
     # Set persona baru
     put_response = client.put("/api/v1/admin/persona", json=new_persona)
     assert put_response.status_code == status.HTTP_200_OK
     updated_data = put_response.json()
     assert updated_data["ai_name"] == new_persona["ai_name"]
     assert updated_data["ai_role"] == new_persona["ai_role"]
     assert updated_data["ai_tone"] == new_persona["ai_tone"]
     assert updated_data["company"] == new_persona["company"]

     # Get lagi untuk memastikan tersimpan
     get_response = client.get("/api/v1/admin/persona")
     assert get_response.status_code == status.HTTP_200_OK
     retrieved_data = get_response.json()
     assert retrieved_data == updated_data # Harusnya sama dengan yang baru di-set