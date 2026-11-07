# FilmLog — Movie Watchlist & Review API
> Layanan backend RESTful API untuk platform kurasi film personal, pencatatan jurnal ulasan tontonan, dan rekomendasi cerdas berbasis Google Gemini AI.
> 
> **Penugasan Rekrutmen Hacker Backend Track — GDGoC Universitas Gadjah Mada 2026/2027**  
> **Kandidat:** Given Gerald Chandra

---

## 🌐 Tautan Live Deployment & Dokumentasi

* **Live Deployment URL (Vercel):** [https://movie-watchlist-starter.vercel.app](https://movie-watchlist-starter.vercel.app)
* **Interactive API Documentation (Swagger UI):** [https://movie-watchlist-starter.vercel.app/docs](https://movie-watchlist-starter.vercel.app/docs)
* **Alternative API Documentation (ReDoc):** [https://movie-watchlist-starter.vercel.app/redoc](https://movie-watchlist-starter.vercel.app/redoc)

---

## 🛠️ Tech Stack & Arsitektur Sistem

- **Bahasa & Runtime:** Python 3.10+
- **Framework Web:** FastAPI (ASGI via Uvicorn)
- **Database & ORM:** SQLite, SQLAlchemy 2.0
- **Skema & Validasi Data:** Pydantic v2
- **Keamanan & Autentikasi:** PyJWT (HS256) & enkripsi password langsung menggunakan library `bcrypt`
- **Kecerdasan Buatan:** Google GenAI SDK (`google-genai`), model `gemini-3.5-flash-lite` dengan *Closed-Domain Grounding*
- **Pengujian Otomatis:** Pytest (19 automated test cases, 100% pass rate)

---

## 🚀 Fitur Unggulan & Solusi Ekstra Terhadap Masalah Teknis

Berikut adalah rekayasa teknis dan solusi defensif ekstra yang diimplementasikan untuk menangani berbagai tantangan dalam pengembangan backend:

| Tantangan / Masalah Teknis | Risiko / Dampak | Solusi Ekstra yang Diterapkan | Lokasi Kode |
| :--- | :--- | :--- | :--- |
| **1. Serverless Cold-Start & Ephemeral DB** | Pada platform serverless seperti Vercel, container bisa mati saat tidak ada request. Token JWT valid milik user yang mendaftar di sesi sebelumnya bisa ditolak dengan HTTP 401 saat menyentuh container baru karena database SQLite di `/tmp` belum mencatat ID tersebut. | **Graceful Serverless User Recovery:** Pada `get_current_user`, jika tanda tangan digital JWT terbukti sah menggunakan `JWT_SECRET`, sistem secara otomatis memulihkan baris `User` ke dalam database SQLite container baru tanpa memaksa user logout/login ulang secara kasar. | `app/dependencies.py` |
| **2. Chrome Private Network Access (PNA)** | Frontend web yang di-deploy ke domain publik internet (HTTPS Vercel) secara default memicu peringatan izin keamanan browser jika memanggil `http://localhost:8000/api`. | **Adaptive Host Resolution:** Menambahkan deteksi cerdas berbasis origin (`isRemoteHost`) pada `frontend/app.js` sehingga otomatis menggunakan `/api` saat diakses via internet dan kembali ke `http://localhost:8000/api` saat pengujian lokal. | `frontend/app.js` |
| **3. Halusinasi Rekomendasi LLM** | Model AI generatif sering merekomendasikan film populer di luar 20 film katalog lokal bawaan panitia (*out-of-domain hallucination*). | **Strict Closed-Domain Grounding & Structured Outputs:** Seluruh metadata 20 film disuntikkan ke dalam *system instruction* model `gemini-3.5-flash-lite`. Output dikunci menggunakan `response_schema` JSON terstruktur (`movie_id` dan `reasoning`) via SDK resmi `google-genai`. | `app/ai_service.py` |
| **4. Failover saat Kuota / Jaringan AI Gangguan** | Kegagalan koneksi atau habisnya kuota Google Gemini API bisa merusak pengalaman pengguna (*service disruption*). | **Transparent Hybrid Fallback:** Jika pemanggilan Gemini gagal, sistem otomatis beralih ke pencocokan kata kunci lokal berbasis genre dan sinopsis dengan menyertakan penanda transparan `source: "gemini"` vs `source: "local_fallback"`. | `app/ai_service.py` |
| **5. Duplikasi Data & Race Condition** | Validasi duplikasi yang hanya dilakukan di level router rawan ditembus saat terjadi *concurrent requests*. | **Composite Unique Constraint:** Menetapkan aturan unik ganda `UniqueConstraint("user_id", "movie_id")` langsung pada tabel `watchlists` di level database SQLAlchemy, serta mengembalikan status HTTP 409 Conflict. | `app/models.py`<br>`app/routers/watchlist.py` |
| **6. Input Kotor & Rating Out-of-Bounds** | Pengguna mengirimkan rating angka negatif, nol, di atas 5, atau ulasan kosong. | **Defensive Bounds Checking:** Validasi Pydantic v2 `Field(..., ge=1.0, le=5.0)` dan pembersihan teks spasi kosong (*whitespace sanitization*). | `app/schemas.py` |
| **7. Dual-Mode Root Routing** | Frontend SPA dan API dokumentasi perlu disajikan secara efisien dari satu server backend. | **Content Negotiation Root Route:** Rute root `/` mendeteksi *header* `Accept`: jika diminta oleh peramban web disajikan antarmuka SPA Letterboxd, sedangkan jika dipanggil oleh klien API/cURL mengembalikan status JSON dan tautan dokumentasi. | `main.py` |

---

## 🗄️ Rancangan Database (Entity-Relationship)

Sistem menggunakan 4 tabel relasional yang saling terhubung:

1. **`users`**: Menyimpan kredensial pengguna (`id`, `username`, `email`, `password_hash`, `created_at`).
2. **`movies`**: Menyimpan katalog 20 film kurasi awal (`id`, `title`, `year`, `director`, `genres`, `rating`, `duration`, `synopsis`, `poster_url`, `cast_members`).
3. **`watchlists`**: Menyimpan relasi tontonan pengguna terhadap film (`id`, `user_id`, `movie_id`, `added_at`). Dijaga oleh `UniqueConstraint("user_id", "movie_id")` dan foreign keys dengan aturan `ON DELETE CASCADE`.
4. **`reviews`**: Menyimpan jurnal ulasan dan rating pengguna (`id`, `user_id`, `movie_id`, `rating`, `review`, `created_at`).

---

## 💻 Panduan Menjalankan Secara Lokal (Setup Guide)

### 1. Prasyarat
- Python 3.10 atau versi lebih baru
- Git
- Virtual environment (`venv`)

### 2. Instalasi & Konfigurasi
Clone repositori dan masuk ke direktori proyek:
```bash
git clone https://github.com/9iven/movie-watchlist-starter.git
cd movie-watchlist-starter
```

Buat dan aktifkan virtual environment:
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

Pasang seluruh dependency yang dibutuhkan:
```bash
pip install -r requirements.txt
```

Buat berkas konfigurasi `.env` pada root direktori:
```env
DATABASE_URL=sqlite:///./filmlog.db
JWT_SECRET=super_secret_filmlog_jwt_key_gdgoc_2026
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
GEMINI_API_KEY=your_google_ai_studio_api_key_here
```

### 3. Menjalankan Aplikasi
Jalankan server pengembangan menggunakan Uvicorn:
```bash
uvicorn main:app --reload --port 8000
```
*(Atau di Windows, kamu cukup menjalankan skrip batch: `.\start.bat`)*

Saat aplikasi pertama kali berjalan, sistem otomatis membuat tabel database dan mengimpor 20 data film awal dari `data/movies.json` via `app/seeder.py`.

Akses melalui peramban:
- **Web Companion:** `http://localhost:8000/`
- **Swagger UI Docs:** `http://localhost:8000/docs`

---

## 🧪 Pengujian Otomatis (Automated Testing)

Proyek ini dilengkapi dengan 19 skenario pengujian komprehensif menggunakan Pytest yang mencakup pengujian auth, duplikasi, pembatasan rating, dan grounding Gemini:

```bash
pytest -v
```

Hasil pengujian:
```text
test_main.py::test_root_endpoint PASSED                                  [  5%]
test_main.py::test_health_endpoint PASSED                                [ 10%]
test_main.py::test_get_all_movies PASSED                                 [ 15%]
test_main.py::test_filter_movies_by_genre PASSED                         [ 21%]
test_main.py::test_search_movies PASSED                                  [ 26%]
test_main.py::test_get_movie_detail_success PASSED                       [ 31%]
test_main.py::test_get_movie_detail_not_found PASSED                     [ 36%]
test_main.py::test_auth_register_and_duplicate PASSED                    [ 42%]
test_main.py::test_auth_login_success PASSED                             [ 47%]
test_main.py::test_auth_login_invalid_password PASSED                    [ 52%]
test_main.py::test_watchlist_requires_auth PASSED                        [ 57%]
test_main.py::test_watchlist_add_and_duplicate PASSED                    [ 63%]
test_main.py::test_watchlist_get_list PASSED                             [ 68%]
test_main.py::test_watchlist_add_invalid_movie PASSED                    [ 73%]
test_main.py::test_watchlist_remove PASSED                               [ 78%]
test_main.py::test_watched_requires_auth PASSED                          [ 84%]
test_main.py::test_log_watched_and_review PASSED                         [ 89%]
test_main.py::test_log_watched_invalid_rating PASSED                     [ 94%]
test_main.py::test_movie_recommendation_grounded PASSED                  [100%]

============================= 19 passed in ~6s =============================
```
