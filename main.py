import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal, Base, get_db
from app.seeder import seed_movies_if_empty
from app.models import Movie
from app.routers import auth, movies, watchlist, watched

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database schema is created and seeded
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_movies_if_empty(db)
    finally:
        db.close()
    yield
    # Shutdown logic (if any)

app = FastAPI(
    title="FilmLog — GDGoC Movie Watchlist & Review API",
    description="A minimalist, high-performance RESTful API for movie tracking, diary reviews, and Google Gemini AI recommendations.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware to support companion frontend and local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth.router)
app.include_router(movies.router)
app.include_router(watchlist.router)
app.include_router(watched.router)

@app.get("/", tags=["Health"])
def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return FileResponse(FRONTEND_DIR / "index.html")
    return {
        "status": "online",
        "app": "FilmLog API",
        "version": "1.0.0",
        "documentation": "/docs",
        "redoc": "/redoc"
    }

@app.get("/api/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    count = db.query(Movie).count()
    return {
        "status": "healthy",
        "database": "connected",
        "movies_count": count
    }

# Mount static files for companion frontend assets
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

