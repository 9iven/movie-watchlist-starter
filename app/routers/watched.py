from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Movie, Review
from app.schemas import WatchedCreate, WatchedResponse
from app.dependencies import get_current_user
from app.seeder import format_movie_dict

router = APIRouter(prefix="/api/watched", tags=["Watched & Reviews (Protected)"])

@router.get("", response_model=List[WatchedResponse])
def get_user_watched_reviews(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    reviews = db.query(Review).filter(Review.user_id == current_user.id).order_by(Review.created_at.desc()).all()
    
    results = []
    for item in reviews:
        movie = db.query(Movie).filter(Movie.id == item.movie_id).first()
        results.append({
            "id": item.id,
            "movieId": item.movie_id,
            "movie_id": item.movie_id,
            "rating": item.rating,
            "review": item.review,
            "created_at": item.created_at,
            "movie": format_movie_dict(movie) if movie else None
        })
    return results

@router.post("", status_code=status.HTTP_201_CREATED)
def log_movie_watched(
    payload: WatchedCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_movie_id = payload.movieId or payload.movie_id
    
    movie = db.query(Movie).filter(Movie.id == target_movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Movie with ID {target_movie_id} does not exist"
        )
    
    if payload.rating < 1.0 or payload.rating > 5.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be between 1.0 and 5.0 stars"
        )
    
    review_entry = Review(
        user_id=current_user.id,
        movie_id=target_movie_id,
        rating=float(payload.rating),
        review=payload.review
    )
    db.add(review_entry)
    db.commit()
    db.refresh(review_entry)
    
    return {
        "message": "Movie logged as watched with review successfully",
        "data": {
            "id": review_entry.id,
            "movieId": review_entry.movie_id,
            "movie_id": review_entry.movie_id,
            "rating": review_entry.rating,
            "review": review_entry.review,
            "created_at": review_entry.created_at,
            "movie": format_movie_dict(movie)
        }
    }
