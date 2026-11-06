import json
from pathlib import Path
from sqlalchemy.orm import Session
from app.models import Movie
from app.config import BASE_DIR

def parse_list_field(val: str) -> list:
    if not val:
        return []
    try:
        parsed = json.loads(val)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed]
    except Exception:
        pass
    return [x.strip() for x in str(val).split(",") if x.strip()]

def format_movie_dict(movie: Movie) -> dict:
    return {
        "id": movie.id,
        "title": movie.title,
        "year": movie.year,
        "director": movie.director,
        "genres": parse_list_field(movie.genres),
        "rating": float(movie.rating),
        "duration": movie.duration,
        "synopsis": movie.synopsis,
        "poster_url": movie.poster_url,
        "cast": parse_list_field(movie.cast_members),
    }

def seed_movies_if_empty(db: Session) -> int:
    existing_count = db.query(Movie).count()
    if existing_count > 0:
        return existing_count

    json_path = BASE_DIR / "data" / "movies.json"
    if not json_path.exists():
        print(f"[Warning] Seeder file not found at: {json_path}")
        return 0

    with open(json_path, "r", encoding="utf-8") as f:
        movies_data = json.load(f)

    for item in movies_data:
        genres_str = json.dumps(item.get("genres", []))
        cast_str = json.dumps(item.get("cast", []))
        
        movie = Movie(
            id=item["id"],
            title=item["title"],
            year=item["year"],
            director=item["director"],
            genres=genres_str,
            rating=float(item["rating"]),
            duration=item["duration"],
            synopsis=item["synopsis"],
            poster_url=item["poster_url"],
            cast_members=cast_str
        )
        db.merge(movie)

    db.commit()
    count = db.query(Movie).count()
    print(f"[Seeder] Successfully populated database with {count} movies.")
    return count
