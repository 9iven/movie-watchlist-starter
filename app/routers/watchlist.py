from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError
from app.database import get_db
from app.models import User, Movie, Watchlist
from app.schemas import WatchlistCreate, WatchlistItemResponse
from app.dependencies import get_current_user
from app.seeder import format_movie_dict

router = APIRouter(prefix="/api/watchlist", tags=["Watchlist (Protected)"])

@router.get("", response_model=List[WatchlistItemResponse])
def get_user_watchlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    entries = db.query(Watchlist).filter(Watchlist.user_id == current_user.id).order_by(Watchlist.added_at.desc()).all()
    
    results = []
    for item in entries:
        movie = db.query(Movie).filter(Movie.id == item.movie_id).first()
        results.append({
            "id": item.id,
            "movieId": item.movie_id,
            "movie_id": item.movie_id,
            "added_at": item.added_at,
            "movie": format_movie_dict(movie) if movie else None
        })
    return results

@router.post("", status_code=status.HTTP_201_CREATED)
def add_to_watchlist(
    payload: WatchlistCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_movie_id = payload.movieId or payload.movie_id
    
    # Check if movie exists in local database
    movie = db.query(Movie).filter(Movie.id == target_movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Movie with ID {target_movie_id} does not exist"
        )
    
    # Check for duplicate entry (prevent 409 Conflict)
    existing = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.movie_id == target_movie_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Movie is already in your watchlist"
        )
    
    entry = Watchlist(
        user_id=current_user.id,
        movie_id=target_movie_id
    )
    db.add(entry)
    try:
        db.commit()
        db.refresh(entry)
    except (IntegrityError, OperationalError):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Movie is already in your watchlist"
        )
    
    return {
        "message": "Movie added to watchlist successfully",
        "data": {
            "id": entry.id,
            "movieId": entry.movie_id,
            "movie_id": entry.movie_id,
            "movie": format_movie_dict(movie)
        }
    }

@router.delete("/{movie_id}", status_code=status.HTTP_200_OK)
def remove_from_watchlist(
    movie_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    entry = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.movie_id == movie_id
    ).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie is not in your watchlist"
        )
    
    db.delete(entry)
    db.commit()
    
    return {
        "message": "Movie removed from watchlist successfully",
        "movieId": movie_id
    }
