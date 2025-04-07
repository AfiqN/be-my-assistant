# tests/unit/test_document_processor.py
import pytest

# Import fungsi yang akan diuji dari path yang benar
from app.core.document_processor import split_text_into_chunks

def test_split_text_into_chunks_basic():
    """Tes pemisahan teks dasar."""
    text = "Ini adalah kalimat pertama. Ini adalah kalimat kedua. Dan ini kalimat ketiga."
    chunks = split_text_into_chunks(text, chunk_size=30, chunk_overlap=5)

    assert isinstance(chunks, list)
    assert len(chunks) > 1 # Harusnya terpisah jadi beberapa chunk
    assert chunks[0] == "Ini adalah kalimat pertama." # Contoh assertion, sesuaikan chunk size/overlap
    # Anda bisa menambahkan assertion lebih detail tentang isi chunk dan overlapnya
    print(f"\nChunks generated: {chunks}") # Untuk debugging saat menjalankan pytest -v

def test_split_text_into_chunks_overlap():
    """Tes overlap antar chunk."""
    text = "abcdefghijklmnopqrstuvwxyz"
    chunks = split_text_into_chunks(text, chunk_size=10, chunk_overlap=3)

    assert len(chunks) == 4 # Disesuaikan berdasarkan perhitungan manual
    assert chunks[0] == "abcdefghij"
    assert chunks[1] == "hijklmnopq" # 'hij' overlap
    assert chunks[2] == "opqrstuvwx" # 'opq' overlap
    assert chunks[3] == "vwxyz"
    print(f"\nChunks with overlap: {chunks}")

def test_split_text_with_empty_input():
    """Tes jika input teks kosong."""
    text = ""
    chunks = split_text_into_chunks(text, chunk_size=100, chunk_overlap=10)
    assert chunks == []

def test_split_text_smaller_than_chunk_size():
    """Tes jika teks lebih pendek dari chunk size."""
    text = "Teks pendek."
    chunks = split_text_into_chunks(text, chunk_size=100, chunk_overlap=10)
    assert len(chunks) == 1
    assert chunks[0] == text

# --- Contoh Test dengan Mocking (jika menguji fungsi yang punya dependensi) ---
# Misal kita tes fungsi lain di document_processor yang memanggil load_pdf_text
# from unittest.mock import patch # atau from pytest_mock import mocker

# def test_some_function_using_pdf(mocker): # Gunakan fixture mocker dari pytest-mock
#     # Mock fungsi load_pdf_text agar tidak membaca file sungguhan
#     mocked_load = mocker.patch('app.core.document_processor.load_pdf_text')
#     # Atur return value dari mock
#     mocked_load.return_value = "Ini teks palsu dari PDF"

#     # Panggil fungsi Anda yang ingin dites
#     result = some_function_that_calls_load_pdf("dummy_path.pdf")

#     # Assert hasilnya
#     assert result == "Hasil yang diharapkan berdasarkan teks palsu"
#     # Pastikan mock dipanggil
#     mocked_load.assert_called_once_with("dummy_path.pdf")