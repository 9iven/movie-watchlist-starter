from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, model_validator, ConfigDict

# --- Auth Schemas ---
class UserRegister(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=6)
    username: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AuthResponse(BaseModel):
    token: str
    user: UserResponse

# --- Movie Schemas ---
class MovieResponse(BaseModel):
    id: int
    title: str
    year: int
    director: str
    genres: List[str]
    rating: float
    duration: str
    synopsis: str
    poster_url: str
    cast: List[str]

    model_config = ConfigDict(from_attributes=True)

# --- Watchlist Schemas ---
class WatchlistCreate(BaseModel):
    movieId: Optional[int] = None
    movie_id: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def check_movie_id(cls, data: Any):
        if isinstance(data, dict):
            mid = data.get("movieId") or data.get("movie_id")
            if not mid:
                raise ValueError("movieId or movie_id is required")
            data["movieId"] = int(mid)
            data["movie_id"] = int(mid)
        return data

class WatchlistItemResponse(BaseModel):
    id: int
    movieId: int
    movie_id: int
    added_at: Optional[datetime] = None
    movie: Optional[MovieResponse] = None

    model_config = ConfigDict(from_attributes=True)

# --- Watched & Review Schemas ---
class WatchedCreate(BaseModel):
    movieId: Optional[int] = None
    movie_id: Optional[int] = None
    rating: float = Field(..., ge=1.0, le=5.0)
    review: Optional[str] = None
    opinion: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_watched(cls, data: Any):
        if isinstance(data, dict):
            mid = data.get("movieId") or data.get("movie_id")
            if not mid:
                raise ValueError("movieId or movie_id is required")
            data["movieId"] = int(mid)
            data["movie_id"] = int(mid)
            
            rev = data.get("review") or data.get("opinion")
            if not rev or not str(rev).strip():
                raise ValueError("review text is required")
            data["review"] = str(rev).strip()
            data["opinion"] = str(rev).strip()
        return data

class WatchedResponse(BaseModel):
    id: int
    movieId: int
    movie_id: int
    rating: float
    review: str
    created_at: Optional[datetime] = None
    movie: Optional[MovieResponse] = None

    model_config = ConfigDict(from_attributes=True)

# --- AI Recommendation Schemas ---
class RecommendRequest(BaseModel):
    prompt: Optional[str] = None
    query: Optional[str] = None
    description: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def extract_prompt(cls, data: Any):
        if isinstance(data, dict):
            p = data.get("prompt") or data.get("query") or data.get("description")
            if not p or not str(p).strip():
                raise ValueError("Prompt or description cannot be empty")
            data["prompt"] = str(p).strip()
        return data

class RecommendResponse(BaseModel):
    movie_id: int
    movieId: int
    reasoning: str
    movie: Optional[MovieResponse] = None
    source: Optional[str] = "gemini"
