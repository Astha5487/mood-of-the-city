"""
emotion_engine.py
Runs HuggingFace emotion classification on song lyrics + comments.
Model: j-hartmann/emotion-english-distilroberta-base
Outputs: joy, sadness, anger, fear, disgust, surprise, neutral

Also maps raw emotions → higher-level moods:
  joy + surprise      → Hype/Celebration
  sadness             → Heartbreak/Longing
  anger               → Rage/Defiance
  joy (low energy)    → Romance/Love
  sadness + neutral   → Nostalgia/Melancholy
  neutral + fear      → Devotion/Calm
"""

import os
import json
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [EMOTION] %(message)s")
log = logging.getLogger(__name__)

# ─── Lazy-load the model to avoid import penalty ──────────────────────────────
_pipe = None

def get_pipe():
    global _pipe
    if _pipe is None:
        from transformers import pipeline
        log.info("Loading emotion model (first run downloads ~250MB)...")
        _pipe = pipeline(
            "text-classification",
            model="j-hartmann/emotion-english-distilroberta-base",
            top_k=None,
            device=-1,   # CPU; set to 0 for GPU
        )
        log.info("Model loaded.")
    return _pipe


# ─── Emotion → Mood mapping ───────────────────────────────────────────────────
MOOD_MAP = {
    "Heartbreak / Longing": {
        "primary": "sadness",
        "secondary": ["neutral"],
        "color": "#F2A623",
        "gradient": ["#F2A623", "#E24B4A"],
        "emoji": "💔",
    },
    "Hype / Anger": {
        "primary": "anger",
        "secondary": ["surprise"],
        "color": "#E24B4A",
        "gradient": ["#E24B4A", "#FF6B35"],
        "emoji": "🔥",
    },
    "Joy / Celebration": {
        "primary": "joy",
        "secondary": ["surprise"],
        "color": "#1D9E75",
        "gradient": ["#1D9E75", "#F2A623"],
        "emoji": "🎉",
    },
    "Nostalgia / Calm": {
        "primary": "neutral",
        "secondary": ["sadness"],
        "color": "#7F77DD",
        "gradient": ["#7F77DD", "#1D9E75"],
        "emoji": "🌙",
    },
    "Romance / Love": {
        "primary": "joy",
        "secondary": ["fear"],
        "color": "#D4537E",
        "gradient": ["#D4537E", "#7F77DD"],
        "emoji": "🌸",
    },
    "Devotion / Spiritual": {
        "primary": "fear",
        "secondary": ["neutral"],
        "color": "#9B59B6",
        "gradient": ["#9B59B6", "#D4537E"],
        "emoji": "🙏",
    },
}

INPUT_PATH  = os.path.join(os.path.dirname(__file__), "..", "data", "songs_enriched.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "songs_with_emotions.json")


def chunk_text(text: str, max_chars: int = 400) -> list[str]:
    """Split text into model-digestible chunks."""
    words = text.split()
    chunks, current = [], []
    for word in words:
        current.append(word)
        if len(" ".join(current)) >= max_chars:
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks[:6]  # max 6 chunks = 2400 chars


def analyze_text(text: str) -> dict[str, float]:
    """Run emotion model on text, return averaged scores per emotion."""
    if not text or len(text.strip()) < 20:
        return {"neutral": 1.0}

    pipe = get_pipe()
    chunks = chunk_text(text)
    aggregated: dict[str, float] = {}

    for chunk in chunks:
        try:
            results = pipe(chunk)[0]
            for item in results:
                label = item["label"]
                score = item["score"]
                aggregated[label] = aggregated.get(label, 0.0) + score
        except Exception as e:
            log.warning(f"Chunk analysis failed: {e}")

    n = len(chunks)
    if n == 0:
        return {"neutral": 1.0}

    averaged = {k: round(v / n, 4) for k, v in aggregated.items()}
    return dict(sorted(averaged.items(), key=lambda x: -x[1]))


def emotions_to_mood(emotions: dict[str, float], genres: list = None, comment_signals: dict = None) -> dict:
    """
    Map raw emotion scores → human-readable mood label.
    Uses genre and comment signals as tiebreakers to ensure variety.
    """
    if not emotions:
        return {"label": "Nostalgia / Calm", **MOOD_MAP["Nostalgia / Calm"]}

    genres = genres or []
    comment_signals = comment_signals or {}

    sorted_emotions = sorted(emotions.items(), key=lambda x: -x[1])
    top_emotion, top_score = sorted_emotions[0]
    second_emotion = sorted_emotions[1][0] if len(sorted_emotions) > 1 else None

    joy      = emotions.get("joy", 0)
    sadness  = emotions.get("sadness", 0)
    anger    = emotions.get("anger", 0)
    fear     = emotions.get("fear", 0)
    surprise = emotions.get("surprise", 0)
    neutral  = emotions.get("neutral", 0)
    disgust  = emotions.get("disgust", 0)

    # ── Genre boosts: adjust effective scores based on genre ──────────────────
    genre_str = " ".join(genres).lower()
    if any(g in genre_str for g in ["rap", "hip-hop", "hip hop"]):
        anger += 0.15; surprise += 0.10
    if any(g in genre_str for g in ["folk", "classical", "devotion"]):
        fear += 0.12; neutral += 0.10
    if any(g in genre_str for g in ["party", "dance"]):
        joy += 0.15; surprise += 0.12
    if "indie" in genre_str:
        neutral += 0.12; sadness += 0.08
    if "romance" in genre_str:
        joy += 0.10; fear += 0.08

    # ── Comment signal boosts ─────────────────────────────────────────────────
    if comment_signals.get("hype_comments", 0) > 2:
        anger += 0.10; surprise += 0.08
    if comment_signals.get("heartbreak_comments", 0) > 2:
        sadness += 0.10
    if comment_signals.get("nostalgia_comments", 0) > 1:
        neutral += 0.08; sadness += 0.05
    if comment_signals.get("love_comments", 0) > 2:
        joy += 0.08; fear += 0.05

    # ── Re-rank after boosts ──────────────────────────────────────────────────
    boosted = {"joy": joy, "sadness": sadness, "anger": anger,
               "fear": fear, "surprise": surprise, "neutral": neutral}
    top_boosted = max(boosted, key=boosted.get)

    # ── Map to mood ───────────────────────────────────────────────────────────
    if top_boosted == "anger" or (top_boosted == "surprise" and anger > 0.25):
        label = "Hype / Anger"

    elif top_boosted == "joy":
        if surprise > 0.25 or anger > 0.20:
            label = "Hype / Anger"
        elif fear > 0.20 or sadness > 0.18:
            label = "Romance / Love"
        else:
            label = "Joy / Celebration"

    elif top_boosted == "sadness":
        if anger > 0.25:
            label = "Hype / Anger"
        elif neutral > sadness * 0.8:
            label = "Nostalgia / Calm"
        else:
            label = "Heartbreak / Longing"

    elif top_boosted == "fear":
        if joy > 0.20:
            label = "Romance / Love"
        else:
            label = "Devotion / Spiritual"

    elif top_boosted == "neutral":
        if sadness > 0.20:
            label = "Nostalgia / Calm"
        elif joy > 0.22:
            label = "Romance / Love"
        elif anger > 0.20:
            label = "Hype / Anger"
        else:
            label = "Nostalgia / Calm"

    elif top_boosted == "surprise":
        label = "Hype / Anger"

    else:
        label = "Nostalgia / Calm"

    return {"label": label, **MOOD_MAP[label], "confidence": round(top_score, 3)}


def analyze_song(song: dict) -> dict:
    """Analyze a single song's lyrics + comments, using genre/comment signals as tiebreakers."""
    lyrics   = song.get("lyrics", "")
    comments = " ".join(song.get("comments", [])[:20])
    corpus   = f"{lyrics}\n{comments}"

    emotions = analyze_text(corpus)

    # Pass genre + comment mood signals for better variety
    genres          = song.get("genres", [])
    comment_signals = song.get("comment_mood_signals", {})
    mood = emotions_to_mood(emotions, genres=genres, comment_signals=comment_signals)

    return {
        **song,
        "raw_emotions":  emotions,
        "mood":          mood,
        "emotion_scores": {
            k: round(v * 100) for k, v in emotions.items()
        },
    }


def run():
    if not os.path.exists(INPUT_PATH):
        log.error(f"Input not found: {INPUT_PATH}. Run comment_scraper.py first.")
        return

    with open(INPUT_PATH, encoding="utf-8") as f:
        all_cities = json.load(f)

    result = {}
    total = sum(len(s) for s in all_cities.values())
    processed = 0

    for city, songs in all_cities.items():
        log.info(f"=== Analyzing {city} ({len(songs)} songs) ===")
        enriched = []
        for song in songs:
            processed += 1
            log.info(f"  [{processed}/{total}] {song.get('song_name', song.get('title'))}")
            enriched.append(analyze_song(song))
        result[city] = enriched

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    log.info(f"Saved → {OUTPUT_PATH}")
    return result


if __name__ == "__main__":
    run()
