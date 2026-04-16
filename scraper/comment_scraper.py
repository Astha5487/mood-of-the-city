"""
comment_scraper.py
Fetches top YouTube comments per song using the YouTube Data API v3.
Reads data/songs_with_lyrics.json, adds comments, saves to data/songs_enriched.json

Get your free API key: https://console.cloud.google.com/apis/library/youtube.googleapis.com
Free quota: 10,000 units/day. Each comment fetch = ~1 unit.
"""

import os
import json
import time
import logging
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [COMMENTS] %(message)s")
log = logging.getLogger(__name__)

# ─── CONFIG ──────────────────────────────────────────────────────────────────
YT_API_KEY    = os.environ.get("YOUTUBE_API_KEY", "YOUR_API_KEY_HERE")
MAX_COMMENTS  = 40       # per video — keeps quota usage low
INPUT_PATH    = os.path.join(os.path.dirname(__file__), "..", "data", "songs_with_lyrics.json")
OUTPUT_PATH   = os.path.join(os.path.dirname(__file__), "..", "data", "songs_enriched.json")
# ─────────────────────────────────────────────────────────────────────────────


def fetch_comments(video_id: str, max_results: int = MAX_COMMENTS) -> list[str]:
    """
    Fetch top comments for a YouTube video.
    Returns list of comment text strings.
    Falls back to empty list on quota exceeded or error.
    """
    url = "https://www.googleapis.com/youtube/v3/commentThreads"
    params = {
        "part":       "snippet",
        "videoId":    video_id,
        "maxResults": max_results,
        "order":      "relevance",
        "key":        YT_API_KEY,
        "textFormat": "plainText",
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 403:
            data = r.json()
            reason = data.get("error", {}).get("errors", [{}])[0].get("reason", "")
            if reason == "commentsDisabled":
                log.info(f"  Comments disabled for {video_id}")
                return []
            if reason == "quotaExceeded":
                log.warning("YouTube API quota exceeded!")
                return []
        r.raise_for_status()
        items = r.json().get("items", [])
        comments = []
        for item in items:
            text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            # Filter out emojis-only or very short comments
            clean = text.strip()
            if len(clean) > 10:
                comments.append(clean[:300])  # cap length
        return comments
    except Exception as e:
        log.error(f"Comment fetch error for {video_id}: {e}")
        return []


def aggregate_comment_mood(comments: list[str]) -> dict:
    """
    Simple keyword-based pre-analysis of comments for mood signals.
    Returns a dict of mood signals found in comments.
    """
    text = " ".join(comments).lower()
    signals = {
        "heartbreak_comments": sum(1 for w in ["cry","tears","miss","sad","broken","pain","hurt"] if w in text),
        "hype_comments":       sum(1 for w in ["fire","🔥","banger","lit","goat","harddd","yoooo"] if w in text),
        "nostalgia_comments":  sum(1 for w in ["childhood","memories","old days","throwback","90s","2000s","miss those"] if w in text),
        "love_comments":       sum(1 for w in ["love","romantic","beautiful","heart","sweetheart","couple"] if w in text),
        "anger_comments":      sum(1 for w in ["angry","rage","hate","worst","boring","trash","skip"] if w in text),
    }
    return signals


def run():
    if not os.path.exists(INPUT_PATH):
        log.error(f"Input not found: {INPUT_PATH}. Run genius_scraper.py first.")
        return

    with open(INPUT_PATH, encoding="utf-8") as f:
        all_cities = json.load(f)

    result = {}
    total = sum(len(songs) for songs in all_cities.values())
    processed = 0

    for city, songs in all_cities.items():
        log.info(f"=== Fetching comments for {city} ({len(songs)} songs) ===")
        enriched = []

        for song in songs:
            processed += 1
            video_id = song.get("id")
            log.info(f"  [{processed}/{total}] {song.get('song_name', song.get('title'))} — {video_id}")

            comments = []
            if video_id and YT_API_KEY != "YOUR_API_KEY_HERE":
                comments = fetch_comments(video_id)
                log.info(f"    → {len(comments)} comments fetched")
                time.sleep(0.3)  # stay within quota
            else:
                log.info(f"    → Skipping (no API key configured)")

            mood_signals = aggregate_comment_mood(comments)

            enriched.append({
                **song,
                "comments":     comments,
                "comment_count": len(comments),
                "comment_mood_signals": mood_signals,
            })

        result[city] = enriched

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    log.info(f"Saved enriched data → {OUTPUT_PATH}")
    return result


if __name__ == "__main__":
    run()
