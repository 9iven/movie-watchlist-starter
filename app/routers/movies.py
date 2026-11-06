import random
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Movie
from app.schemas import MovieResponse, RecommendRequest, RecommendResponse
from app.seeder import format_movie_dict, parse_list_field
from app.ai_service import get_ai_movie_recommendation

router = APIRouter(prefix="/api/movies", tags=["Movies & AI Discovery"])

@router.get("", response_model=List[MovieResponse])
def get_movies(
    genre: Optional[str] = Query(None, description="Filter movies by genre (e.g. Sci-Fi)"),
    search: Optional[str] = Query(None, description="Search by movie title or director"),
    shuffle: bool = Query(False, description="Randomly shuffle movie list"),
    db: Session = Depends(get_db)
):
    query = db.query(Movie)
    
    if search:
        search_term = f"%{search.strip().lower()}%"
        query = query.filter(
            (Movie.title.ilike(search_term)) | (Movie.director.ilike(search_term))
        )
    
    all_records = query.all()
    results = []

    for m in all_records:
        movie_dict = format_movie_dict(m)
        if genre and genre.upper() != "ALL":
            movie_genres = [g.upper() for g in movie_dict["genres"]]
            if genre.upper() not in movie_genres:
                continue
        results.append(movie_dict)
    
    if shuffle:
        random.shuffle(results)
        
    return results

@router.get("/{movie_id}", response_model=MovieResponse)
def get_movie_detail(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with ID {movie_id} was not found"
        )
    return format_movie_dict(movie)

@router.post("/recommend", response_model=RecommendResponse)
def recommend_movie(payload: RecommendRequest, db: Session = Depends(get_db)):
    rec = get_ai_movie_recommendation(payload.prompt, db)
    matched_movie = db.query(Movie).filter(Movie.id == rec["movie_id"]).first()
    
    if not matched_movie:
        # Fallback to first movie if ID is somehow out of sync
        matched_movie = db.query(Movie).first()
        rec["movie_id"] = matched_movie.id if matched_movie else 1

    formatted_movie = format_movie_dict(matched_movie) if matched_movie else None

    return {
        "movie_id": rec["movie_id"],
        "movieId": rec["movie_id"],
        "reasoning": rec["reasoning"],
        "movie": formatted_movie,
        "source": rec.get("source", "gemini")
    }
