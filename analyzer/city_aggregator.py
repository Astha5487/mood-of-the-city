"""
city_aggregator.py
Aggregates per-song emotion scores into city-level mood profiles.
Applies view-count weighting so viral songs influence the mood more.
Uses genre + comment signals as tiebreakers when emotion model collapses.
Outputs data/city_moods.json — consumed by the FastAPI backend.
"""

import os
import json
import math
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [AGG] %(message)s")
log = logging.getLogger(__name__)

INPUT_PATH  = os.path.join(os.path.dirname(__file__), "..", "data", "songs_with_emotions.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "city_moods.json")

CITY_COORDS = {
    "Mumbai":    [19.0760, 72.8777],
    "Delhi":     [28.6139, 77.2090],
    "Bangalore": [12.9716, 77.5946],
    "Kolkata":   [22.5726, 88.3639],
    "Chennai":   [13.0827, 80.2707],
    "Hyderabad": [17.3850, 78.4867],
    "Pune":      [18.5204, 73.8567],
    "Jaipur":    [26.9124, 75.7873],
}

MOOD_COLORS = {
    "Heartbreak / Longing":  {"primary": "#F2A623", "secondary": "#E24B4A", "glow": "rgba(242,166,35,0.4)"},
    "Hype / Anger":          {"primary": "#E24B4A", "secondary": "#FF6B35", "glow": "rgba(226,75,74,0.4)"},
    "Joy / Celebration":     {"primary": "#1D9E75", "secondary": "#F2A623", "glow": "rgba(29,158,117,0.4)"},
    "Nostalgia / Calm":      {"primary": "#7F77DD", "secondary": "#4A90D9", "glow": "rgba(127,119,221,0.4)"},
    "Romance / Love":        {"primary": "#D4537E", "secondary": "#7F77DD", "glow": "rgba(212,83,126,0.4)"},
    "Devotion / Spiritual":  {"primary": "#9B59B6", "secondary": "#D4537E", "glow": "rgba(155,89,182,0.4)"},
}

GENRE_COLORS = {
    "Bollywood":   "#FF6B6B",
    "Indie":       "#4ECDC4",
    "Rap/Hip-Hop": "#FFE66D",
    "Classical":   "#A8DADC",
    "Folk":        "#F4A261",
    "Pop":         "#E9C46A",
    "Regional":    "#2A9D8F",
    "Romance":     "#E76F51",
    "Party/Dance": "#F72585",
}

# When emotion model collapses everything to same label,
# use top genre to pick a more meaningful mood
GENRE_MOOD_OVERRIDE = {
    "Rap/Hip-Hop": "Hype / Anger",
    "Party/Dance": "Joy / Celebration",
    "Folk":        "Joy / Celebration",
    "Classical":   "Devotion / Spiritual",
    "Indie":       "Nostalgia / Calm",
    "Romance":     "Romance / Love",
}


def view_weight(views: int) -> float:
    """Log-scaled weight so 100M views doesn't drown out 1M views."""
    if not views or views <= 0:
        return 1.0
    return math.log10(max(views, 1000)) / 6.0


def aggregate_city(songs: list) -> dict:
    """Compute weighted emotion scores + dominant mood for a city."""

    emotion_totals = defaultdict(float)
    weight_total = 0.0
    mood_votes = defaultdict(float)
    genre_counts = defaultdict(int)
    comment_signal_totals = defaultdict(int)
    song_cards = []

    for song in songs:
        w = view_weight(song.get("views", 0))
        raw = song.get("raw_emotions", {})
        mood_label = song.get("mood", {}).get("label", "Nostalgia / Calm")

        for emotion, score in raw.items():
            emotion_totals[emotion] += score * w
        mood_votes[mood_label] += w
        weight_total += w

        for genre in song.get("genres", ["Pop"]):
            genre_counts[genre] += 1

        for k, v in song.get("comment_mood_signals", {}).items():
            comment_signal_totals[k] += v

        song_cards.append({
            "id":            song.get("id"),
            "title":         song.get("song_name", song.get("title", "Unknown")),
            "artist":        song.get("artist_name", song.get("artist", "Unknown")),
            "url":           song.get("url"),
            "thumbnail":     song.get("thumbnail"),
            "views":         song.get("views", 0),
            "genres":        song.get("genres", ["Pop"]),
            "mood_label":    mood_label,
            "mood_color":    MOOD_COLORS.get(mood_label, MOOD_COLORS["Nostalgia / Calm"])["primary"],
            "lyrics_preview":song.get("lyrics_preview", ""),
            "emotion_scores":song.get("emotion_scores", {}),
            "top_comments":  song.get("comments", [])[:3],
        })

    if weight_total == 0:
        weight_total = 1

    averaged_emotions = {
        k: round((v / weight_total) * 100)
        for k, v in emotion_totals.items()
    }

    # ── Dominant mood with tiebreakers ────────────────────────────────────
    top_genre = max(genre_counts, key=genre_counts.get) if genre_counts else "Pop"
    dominant_mood = max(mood_votes, key=mood_votes.get) if mood_votes else "Nostalgia / Calm"

    # If all songs collapsed to same label, use genre override
    unique_moods = len([v for v in mood_votes.values() if v > 0])
    if unique_moods <= 1 and top_genre in GENRE_MOOD_OVERRIDE:
        dominant_mood = GENRE_MOOD_OVERRIDE[top_genre]

    # Comment signal override
    hype_sig = comment_signal_totals.get("hype_comments", 0)
    sad_sig  = comment_signal_totals.get("heartbreak_comments", 0)
    love_sig = comment_signal_totals.get("love_comments", 0)
    nost_sig = comment_signal_totals.get("nostalgia_comments", 0)
    sig_map  = {
        "Hype / Anger":        hype_sig,
        "Heartbreak / Longing": sad_sig,
        "Romance / Love":      love_sig,
        "Nostalgia / Calm":    nost_sig,
    }
    top_sig_mood = max(sig_map, key=sig_map.get)
    if sig_map[top_sig_mood] >= 3:
        dominant_mood = top_sig_mood

    mood_distribution = {
        k: round((v / weight_total) * 100)
        for k, v in mood_votes.items()
    }

    genre_breakdown = {
        k: {"count": v, "color": GENRE_COLORS.get(k, "#888")}
        for k, v in sorted(genre_counts.items(), key=lambda x: -x[1])
    }

    insight_templates = {
        "Heartbreak / Longing": "Binging breakup anthems — sadness 3x above average",
        "Hype / Anger":         "Rage & hype dominate — rap and defiance songs surging",
        "Joy / Celebration":    "Pure celebration mode — wedding and party tracks trending",
        "Nostalgia / Calm":     "Deep in nostalgia — indie & lo-fi taking over the playlists",
        "Romance / Love":       "Love is in the air — romantic ballads rule the charts",
        "Devotion / Spiritual": "Spiritual mood — classical and bhajan trending",
    }

    song_cards.sort(key=lambda x: x.get("views", 0), reverse=True)

    return {
        "dominant_mood":     dominant_mood,
        "mood_colors":       MOOD_COLORS.get(dominant_mood, MOOD_COLORS["Nostalgia / Calm"]),
        "mood_distribution": mood_distribution,
        "emotion_breakdown": averaged_emotions,
        "genre_breakdown":   genre_breakdown,
        "top_genre":         top_genre,
        "insight":           insight_templates.get(dominant_mood, "Unique mood blend this week"),
        "song_count":        len(songs),
        "songs":             song_cards[:12],
    }


def run():
    if not os.path.exists(INPUT_PATH):
        log.error(f"Input not found: {INPUT_PATH}. Run emotion_engine.py first.")
        return

    with open(INPUT_PATH, encoding="utf-8") as f:
        all_cities = json.load(f)

    city_moods = {}
    for city, songs in all_cities.items():
        log.info(f"Aggregating {city} ({len(songs)} songs)...")
        if not songs:
            continue
        coords = CITY_COORDS.get(city, [20.0, 78.0])
        agg = aggregate_city(songs)
        city_moods[city] = {
            "city": city,
            "lat":  coords[0],
            "lng":  coords[1],
            **agg,
        }
        log.info(f"  -> Dominant mood: {agg['dominant_mood']}")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(city_moods, f, ensure_ascii=False, indent=2)

    log.info(f"City moods saved -> {OUTPUT_PATH}")
    return city_moods


if __name__ == "__main__":
    run()
