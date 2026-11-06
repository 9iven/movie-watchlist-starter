import json
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.models import Movie
from app.config import GEMINI_API_KEY
from app.seeder import parse_list_field

class GeminiRecommendationSchema(BaseModel):
    movie_id: int = Field(
        ...,
        description="The exact integer ID of the recommended movie, which MUST exist within the LOCAL_DATABASE_CATALOG."
    )
    reasoning: str = Field(
        ...,
        description="A compelling and insightful 1-3 sentence explanation of why this specific film matches the user's mood or prompt."
    )

def generate_catalog_context(movies: List[Movie]) -> str:
    lines = []
    for m in movies:
        genres = ", ".join(parse_list_field(m.genres))
        lines.append(
            f"ID: {m.id} | Title: {m.title} ({m.year}) | Director: {m.director} | Genres: {genres} | Synopsis: {m.synopsis}"
        )
    return "\n".join(lines)

def fallback_local_recommendation(prompt: str, movies: List[Movie]) -> Dict[str, Any]:
    prompt_lower = prompt.lower()
    best_match = movies[0] if movies else None
    highest_score = -1

    for m in movies:
        score = 0
        title_lower = m.title.lower()
        director_lower = m.director.lower()
        genres_lower = " ".join(parse_list_field(m.genres)).lower()
        synopsis_lower = m.synopsis.lower()

        # Score matching
        for word in prompt_lower.split():
            clean_word = word.strip(",.!?\"'")
            if len(clean_word) <= 2:
                continue
            if clean_word in genres_lower:
                score += 3
            if clean_word in title_lower:
                score += 5
            if clean_word in director_lower:
                score += 4
            if clean_word in synopsis_lower:
                score += 2

        if score > highest_score:
            highest_score = score
            best_match = m

    genres = ", ".join(parse_list_field(best_match.genres)) if best_match else ""
    return {
        "movie_id": best_match.id if best_match else 1,
        "reasoning": f"Film '{best_match.title}' ({best_match.year}) karya sutradara {best_match.director} dipilih karena memiliki tema ({genres}) dan atmosfer narasi yang sangat selaras dengan suasana film yang Anda inginkan: \"{prompt}\".",
        "source": "local_fallback"
    }

def get_ai_movie_recommendation(prompt: str, db: Session) -> Dict[str, Any]:
    movies = db.query(Movie).all()
    if not movies:
        return {
            "movie_id": 1,
            "reasoning": "Tidak ada film yang tersedia di database lokal."
        }

    valid_ids = {m.id for m in movies}

    if not GEMINI_API_KEY or GEMINI_API_KEY.strip() == "" or GEMINI_API_KEY == "your_gemini_api_key_here":
        return fallback_local_recommendation(prompt, movies)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)
        catalog_context = generate_catalog_context(movies)

        system_instruction = (
            "You are FilmLog Cinephile AI, an expert film recommendation engine.\n"
            "Your task is to recommend EXACTLY ONE movie to the user based on their mood, query, or aesthetic description.\n\n"
            "STRICT GROUNDING RULES:\n"
            "1. You are strictly FORBIDDEN from recommending any movie that does not exist in the LOCAL_DATABASE_CATALOG below.\n"
            "2. Even if the user mentions external movies (e.g. 'Titanic', 'Avatar', 'Tenet'), you must find the closest thematic match that ACTUALLY EXISTS in the catalog.\n"
            "3. You must output valid JSON strictly matching the provided schema with 'movie_id' (integer) and 'reasoning' (string).\n"
            "4. The reasoning should be in Indonesian if the prompt is in Indonesian, or English if in English, explaining specifically why the film matches.\n\n"
            "[LOCAL_DATABASE_CATALOG]\n"
            f"{catalog_context}\n"
            "[/LOCAL_DATABASE_CATALOG]"
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=GeminiRecommendationSchema,
                temperature=0.4,
            )
        )

        # Parse structured response
        data = json.loads(response.text)
        rec_id = int(data.get("movie_id", 0))
        reasoning = str(data.get("reasoning", "")).strip()

        # Sanity check: Ensure the returned ID really exists in local DB
        if rec_id in valid_ids:
            return {
                "movie_id": rec_id,
                "reasoning": reasoning,
                "source": "gemini"
            }
        else:
            # Fallback if model returned an ungrounded ID
            return fallback_local_recommendation(prompt, movies)

    except Exception as e:
        print(f"[Gemini AI Service Error] Fallback triggered: {e}")
        return fallback_local_recommendation(prompt, movies)
