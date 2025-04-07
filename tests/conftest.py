# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from typing import Generator
import os

# Import FastAPI app instance dari app.main
# Pastikan path importnya benar dari root project
from app.main import app

# Set environment variable untuk testing jika diperlukan
# Misalnya, jika Anda ingin menggunakan DB atau API Key khusus test
# os.environ["YOUR_TEST_ENV_VAR"] = "test_value"

@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """
    Fixture untuk membuat TestClient FastAPI per modul test.
    'scope="module"' berarti client akan dibuat sekali untuk semua test dalam satu file.
    """
    # Anda bisa melakukan setup tambahan di sini jika perlu
    # sebelum client dibuat, misalnya setup test database.
    print("\n--- Creating TestClient ---")
    with TestClient(app) as test_client:
        yield test_client # TestClient siap digunakan oleh test function
    # Teardown (jika ada) setelah semua test di modul selesai
    print("\n--- Tearing down TestClient ---")
    # Misalnya, membersihkan test database.

# Anda bisa menambahkan fixtures lain di sini, misalnya:
# @pytest.fixture
# def mock_embedding_model():
#     # Kode untuk membuat mock object embedding model
#     pass

# @pytest.fixture
# def test_vector_collection():
#     # Kode untuk setup/teardown collection ChromaDB khusus testing
#     # (Mungkin menggunakan instance in-memory atau collection dengan nama unik)
#     pass