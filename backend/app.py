"""
app.py
FastAPI backend serving the Mood of the City API.

Endpoints:
  GET /api/mood-map        → all cities' mood data
  GET /api/city/{city}     → single city detail
  GET /api/genres          → genre summary across all cities
  POST /api/refresh        → manually trigger a scrape+analyze pipeline run
  GET /health              → health check

Run: uvicorn backend.app:app --reload --port 8000
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [API] %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(
    title="Mood of the City API",
    description="Emotional geography of Indian music — live sentiment from YouTube + Genius",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent.parent
DATA_DIR      = BASE_DIR / "data"
FRONTEND_DIR  = BASE_DIR / "frontend"
CITY_MOODS    = DATA_DIR / "city_moods.json"
DEMO_DATA     = DATA_DIR / "demo_data.json"

def load_city_moods() -> dict:
    """Load city mood data. Falls back to demo data if real data not yet generated."""
    path = CITY_MOODS if CITY_MOODS.exists() else DEMO_DATA
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.get("/")
async def root():
    """Serve the frontend index.html."""
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "Mood of the City API", "docs": "/docs"}


@app.get("/dashboard.js")
async def serve_dashboard_js():
    """Serve dashboard.js from frontend folder."""
    f = FRONTEND_DIR / "dashboard.js"
    if f.exists():
        return FileResponse(str(f), media_type="application/javascript")
    raise HTTPException(status_code=404, detail="dashboard.js not found")


@app.get("/demo_data.json")
async def serve_demo_data():
    """Serve demo_data.json from frontend folder."""
    f = FRONTEND_DIR / "demo_data.json"
    if not f.exists():
        f = DATA_DIR / "demo_data.json"
    if f.exists():
        return FileResponse(str(f), media_type="application/json")
    raise HTTPException(status_code=404, detail="demo_data.json not found")


@app.get("/favicon.ico")
async def favicon():
    raise HTTPException(status_code=204)


@app.get("/health")
async def health():
    data_exists = CITY_MOODS.exists()
    return {
        "status": "ok",
        "data_ready": data_exists,
        "last_updated": (
            datetime.fromtimestamp(CITY_MOODS.stat().st_mtime).isoformat()
            if data_exists else None
        ),
    }


@app.get("/api/mood-map")
async def get_mood_map():
    """
    Returns mood data for all cities.
    Response shape: { city_name: { dominant_mood, emotion_breakdown, songs, ... } }
    """
    data = load_city_moods()
    if not data:
        raise HTTPException(status_code=503, detail="Data not yet generated. Run the pipeline first.")

    # Strip heavy fields for the map overview
    slim = {}
    for city, info in data.items():
        slim[city] = {
            "city":           info["city"],
            "lat":            info["lat"],
            "lng":            info["lng"],
            "dominant_mood":  info["dominant_mood"],
            "mood_colors":    info["mood_colors"],
            "insight":        info["insight"],
            "top_genre":      info.get("top_genre"),
            "emotion_breakdown": info.get("emotion_breakdown", {}),
            "genre_breakdown": info.get("genre_breakdown", {}),
        }
    return slim


@app.get("/api/city/{city_name}")
async def get_city_detail(city_name: str):
    """Full city detail including song list."""
    data = load_city_moods()
    # Case-insensitive lookup
    match = next(
        (v for k, v in data.items() if k.lower() == city_name.lower()),
        None
    )
    if not match:
        raise HTTPException(status_code=404, detail=f"City '{city_name}' not found.")
    return match


@app.get("/api/genres")
async def get_genres():
    """Aggregated genre breakdown across all cities."""
    data = load_city_moods()
    totals: dict[str, int] = {}
    for city_data in data.values():
        for genre, info in city_data.get("genre_breakdown", {}).items():
            totals[genre] = totals.get(genre, 0) + info.get("count", 0)
    return dict(sorted(totals.items(), key=lambda x: -x[1]))


@app.get("/api/trending")
async def get_trending(limit: int = 20):
    """Top songs across all cities by view count."""
    data = load_city_moods()
    all_songs = []
    for city_name, city_data in data.items():
        for song in city_data.get("songs", []):
            all_songs.append({**song, "city": city_name})
    all_songs.sort(key=lambda x: x.get("views", 0), reverse=True)
    return all_songs[:limit]


@app.post("/api/refresh")
async def trigger_refresh(background_tasks: BackgroundTasks):
    """
    Manually trigger a full scrape + analyze pipeline run.
    Runs in background — poll /health to check when done.
    """
    def run_pipeline():
        import sys
        sys.path.insert(0, str(BASE_DIR))
        log.info("Pipeline started...")
        try:
            from scraper.youtube_scraper import run as yt_run
            yt_run()
            from scraper.genius_scraper import run as genius_run
            genius_run()
            from scraper.comment_scraper import run as comment_run
            comment_run()
            from analyzer.emotion_engine import run as emotion_run
            emotion_run()
            from analyzer.city_aggregator import run as agg_run
            agg_run()
            log.info("Pipeline complete!")
        except Exception as e:
            log.error(f"Pipeline failed: {e}")

    background_tasks.add_task(run_pipeline)
    return {"status": "Pipeline started in background", "poll": "/health"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
