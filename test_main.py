import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.seeder import seed_movies_if_empty
from main import app

# StaticPool ensures the in-memory SQLite database remains alive across all connections & threads
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    seed_movies_if_empty(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)

client = TestClient(app)

# --- 1. Health & Discovery Tests ---

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "FilmLog" in data["app"]

def test_health_endpoint():
    # Note: health_check endpoint uses SessionLocal, but movies endpoint uses get_db
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_get_all_movies():
    response = client.get("/api/movies")
    assert response.status_code == 200
    movies = response.json()
    assert isinstance(movies, list)
    assert len(movies) == 20
    assert movies[0]["title"] == "Inception"
    assert isinstance(movies[0]["genres"], list)
    assert isinstance(movies[0]["cast"], list)

def test_filter_movies_by_genre():
    response = client.get("/api/movies?genre=Animation")
    assert response.status_code == 200
    movies = response.json()
    assert len(movies) > 0
    for m in movies:
        assert "Animation" in m["genres"]

def test_search_movies():
    response = client.get("/api/movies?search=Nolan")
    assert response.status_code == 200
    movies = response.json()
    assert len(movies) >= 3  # Inception, Dark Knight, Interstellar, Memento, Oppenheimer
    for m in movies:
        assert "Nolan" in m["director"] or "Nolan" in m["title"]

def test_get_movie_detail_success():
    response = client.get("/api/movies/1")
    assert response.status_code == 200
    movie = response.json()
    assert movie["id"] == 1
    assert movie["title"] == "Inception"
    assert movie["year"] == 2010

def test_get_movie_detail_not_found():
    response = client.get("/api/movies/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

# --- 2. Authentication Tests ---

def test_auth_register_and_duplicate():
    payload = {
        "email": "testcinephile@example.com",
        "password": "securepassword123",
        "username": "cinephile_test"
    }
    # First registration
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "registered successfully" in data["message"]

    # Duplicate registration (should return 409 Conflict)
    dup_response = client.post("/api/auth/register", json=payload)
    assert dup_response.status_code == 409
    assert "already registered" in dup_response.json()["detail"]

def test_auth_login_success():
    payload = {
        "email": "testcinephile@example.com",
        "password": "securepassword123"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["user"]["email"] == "testcinephile@example.com"

def test_auth_login_invalid_password():
    payload = {
        "email": "testcinephile@example.com",
        "password": "wrongpassword"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 401
    assert "invalid email or password" in response.json()["detail"].lower()

# --- 3. Watchlist CRUD & Guard Tests ---

def get_auth_token():
    payload = {
        "email": "testcinephile@example.com",
        "password": "securepassword123"
    }
    res = client.post("/api/auth/login", json=payload)
    return res.json()["token"]

def test_watchlist_requires_auth():
    response = client.get("/api/watchlist")
    assert response.status_code == 401

def test_watchlist_add_and_duplicate():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Add movie 1 (Inception) to watchlist
    res = client.post("/api/watchlist", json={"movieId": 1}, headers=headers)
    assert res.status_code == 201
    assert res.json()["data"]["movieId"] == 1

    # Adding duplicate movie 1 should return 409 Conflict
    dup_res = client.post("/api/watchlist", json={"movieId": 1}, headers=headers)
    assert dup_res.status_code == 409
    assert "already in your watchlist" in dup_res.json()["detail"].lower()

def test_watchlist_get_list():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/watchlist", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    assert items[0]["movieId"] == 1
    assert items[0]["movie"]["title"] == "Inception"

def test_watchlist_add_invalid_movie():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/watchlist", json={"movieId": 9999}, headers=headers)
    assert res.status_code == 400
    assert "does not exist" in res.json()["detail"].lower()

def test_watchlist_remove():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.delete("/api/watchlist/1", headers=headers)
    assert res.status_code == 200
    assert "removed" in res.json()["message"].lower()

    # Deleting again should return 404
    res_del_again = client.delete("/api/watchlist/1", headers=headers)
    assert res_del_again.status_code == 404

# --- 4. Watched & Review Tests ---

def test_watched_requires_auth():
    response = client.get("/api/watched")
    assert response.status_code == 401

def test_log_watched_and_review():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "movieId": 2,
        "rating": 5.0,
        "review": "Parasite adalah mahakarya satir sosial dengan tensi yang luar biasa!"
    }
    res = client.post("/api/watched", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["movieId"] == 2
    assert data["rating"] == 5.0
    assert "Parasite" in data["movie"]["title"]

    # Verify in GET /api/watched
    list_res = client.get("/api/watched", headers=headers)
    assert list_res.status_code == 200
    reviews = list_res.json()
    assert len(reviews) >= 1
    assert reviews[0]["movieId"] == 2

def test_log_watched_invalid_rating():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "movieId": 2,
        "rating": 6.5,  # Exceeds max 5.0
        "review": "Too high rating"
    }
    res = client.post("/api/watched", json=payload, headers=headers)
    assert res.status_code in [400, 422]

# --- 5. AI Recommendation Grounding Test ---

def test_movie_recommendation_grounded():
    payload = {
        "prompt": "Saya ingin menonton film sci-fi mind-bending tentang manipulasi alam bawah sadar"
    }
    res = client.post("/api/movies/recommend", json=payload)
    assert res.status_code == 200
    data = res.json()
    
    assert "movie_id" in data
    assert 1 <= data["movie_id"] <= 20  # Strictly grounded in initial 20 movies
    assert "reasoning" in data
    assert len(data["reasoning"]) > 10
    assert "movie" in data
    assert data["movie"]["id"] == data["movie_id"]
