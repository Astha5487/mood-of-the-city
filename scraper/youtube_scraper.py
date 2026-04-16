"""
youtube_scraper.py
Scrapes trending music per Indian city using yt-dlp and BeautifulSoup.
Saves raw video metadata to data/youtube_raw.json
"""

import yt_dlp
import json
import time
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [YT] %(message)s")
log = logging.getLogger(__name__)

# City → search query mapping
CITY_QUERIES = {
    "Mumbai":    ["Mumbai trending songs 2024", "Bollywood hits Mumbai", "Marathi trending songs"],
    "Delhi":     ["Delhi trending music 2024", "Punjabi hits Delhi", "Hindi rap trending Delhi"],
    "Bangalore": ["Bangalore trending songs", "Kannada hits 2024", "Indie music Bangalore"],
    "Kolkata":   ["Kolkata trending songs", "Bengali music hits 2024", "Bollywood Kolkata"],
    "Chennai":   ["Chennai trending songs", "Tamil hits 2024", "A.R. Rahman new songs"],
    "Hyderabad": ["Hyderabad trending songs", "Telugu hits 2024", "Tollywood music 2024"],
    "Pune":      ["Pune trending songs", "Marathi pop 2024", "Bollywood Pune"],
    "Jaipur":    ["Jaipur trending songs", "Rajasthani folk 2024", "Hindi songs Jaipur"],
}

RESULTS_PER_QUERY = 8  # songs per query
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "youtube_raw.json")


def fetch_city_songs(city: str, queries: list[str]) -> list[dict]:
    """Fetch top songs for a city across multiple search queries."""
    all_songs = []
    seen_ids = set()

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlistend": RESULTS_PER_QUERY,
    }

    for query in queries:
        log.info(f"Searching: '{query}'")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                results = ydl.extract_info(
                    f"ytsearch{RESULTS_PER_QUERY}:{query}", download=False
                )
            for entry in results.get("entries", []):
                if not entry or entry.get("id") in seen_ids:
                    continue
                if entry.get("duration", 0) > 600:  # skip >10 min (not songs)
                    continue
                seen_ids.add(entry["id"])
                all_songs.append({
                    "id":       entry.get("id"),
                    "title":    entry.get("title"),
                    "artist":   entry.get("uploader", "Unknown"),
                    "duration": entry.get("duration"),
                    "views":    entry.get("view_count", 0),
                    "url":      f"https://youtube.com/watch?v={entry.get('id')}",
                    "thumbnail":entry.get("thumbnail"),
                    "city":     city,
                    "query":    query,
                    "scraped_at": datetime.utcnow().isoformat(),
                })
            time.sleep(1.5)  # respectful delay between queries
        except Exception as e:
            log.error(f"Failed query '{query}': {e}")

    # Sort by views descending, keep top 15 per city
    all_songs.sort(key=lambda x: x.get("views", 0), reverse=True)
    return all_songs[:15]


def run():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    all_data = {}

    for city, queries in CITY_QUERIES.items():
        log.info(f"=== Scraping {city} ===")
        songs = fetch_city_songs(city, queries)
        all_data[city] = songs
        log.info(f"  → {len(songs)} songs collected for {city}")
        time.sleep(2)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    log.info(f"Saved to {OUTPUT_PATH}")
    return all_data


if __name__ == "__main__":
    run()
