from slowapi import Limiter
from slowapi.util import get_remote_address

# Menggunakan alamat IP remote sebagai kunci identifikasi klien
limiter = Limiter(key_func=get_remote_address)