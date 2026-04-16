"""
genius_scraper.py
Scrapes song lyrics from Genius.com using requests + BeautifulSoup.
Reads data/youtube_raw.json, adds lyrics, saves to data/songs_with_lyrics.json
"""

import requests
import json
import time
import os
import re
import logging
from urllib.parse import quote
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [GENIUS] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

INPUT_PATH  = os.path.join(os.path.dirname(__file__), "..", "data", "youtube_raw.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "songs_with_lyrics.json")

GENRE_KEYWORDS = {
    "Bollywood":   ["bollywood","hindi film","hindi movie","filmi"],
    "Indie":       ["indie","independent","lo-fi","lofi","alternative"],
    "Rap/Hip-Hop": ["rap","hip hop","hip-hop","freestyle","cypher","bars","desi hip hop"],
    "Classical":   ["classical","raga","carnatic","hindustani","classical fusion","devotional","bhajan","kirtan"],
    "Folk":        ["folk","lok geet","rajasthani","baul","lavani","bhangra","garba","dhol","tribal"],
    "Pop":         ["pop","chart","hit","trending","viral"],
    "Regional":    ["punjabi","tamil","telugu","kannada","bengali","marathi","gujarati","malayalam","odia"],
    "Romance":     ["love","romantic","dulhan","shaadi","wedding"],
    "Party/Dance": ["party","dance","club","dj","remix","electronic","edm","techno","beats"],
}


def clean_title(title: str) -> str:
    """Strip YouTube garbage from titles: (Official Video), ft., etc."""
    title = re.sub(r'\(.*?\)|\[.*?\]', '', title)
    title = re.sub(r'ft\..*|feat\..*|official.*|video.*|audio.*|lyric.*|full.*|song.*',
                   '', title, flags=re.IGNORECASE)
    return title.strip()


def extract_artist(title: str, uploader: str) -> tuple[str, str]:
    """Extract song name and artist from YT title."""
    # Pattern: "Artist - Song" or "Song - Artist"
    if ' - ' in title:
        parts = title.split(' - ', 1)
        return clean_title(parts[1]), parts[0].strip()
    return clean_title(title), uploader.replace("VEVO", "").replace("Records", "").strip()


def search_genius(song: str, artist: str) -> str | None:
    """Search Genius and return the lyrics page URL."""
    query = quote(f"{song} {artist}")
    url = f"https://genius.com/search?q={query}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        # Find first result link ending in -lyrics
        link = soup.find("a", href=re.compile(r"genius\.com/.+-lyrics"))
        if link:
            return link["href"]
    except Exception as e:
        log.warning(f"Search failed for '{song}': {e}")
    return None


def scrape_lyrics(genius_url: str) -> str:
    """Scrape lyrics text from a Genius lyrics page."""
    try:
        r = requests.get(genius_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        containers = soup.select('[data-lyrics-container="true"]')
        if not containers:
            return ""
        lines = []
        for c in containers:
            for br in c.find_all("br"):
                br.replace_with("\n")
            text = c.get_text("\n")
            lines.append(text)
        lyrics = "\n".join(lines)
        # Remove [Verse], [Chorus] markers but keep text
        lyrics = re.sub(r'\[.*?\]', '', lyrics)
        lyrics = re.sub(r'\n{3,}', '\n\n', lyrics)
        return lyrics.strip()[:3000]  # cap at 3000 chars
    except Exception as e:
        log.warning(f"Lyrics scrape failed: {e}")
        return ""


def detect_genre(title: str, artist: str, lyrics: str) -> list[str]:
    """Tag genres based on keyword matching across metadata + lyrics."""
    combined = f"{title} {artist} {lyrics}".lower()
    matched = []
    for genre, keywords in GENRE_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            matched.append(genre)
    if not matched:
        matched = ["Pop"]  # default
    return matched[:3]  # max 3 genres per song


def get_quote(lyrics: str) -> str:
    """Extract the most emotionally punchy line from lyrics."""
    if not lyrics:
        return ""
    lines = [l.strip() for l in lyrics.split('\n') if len(l.strip()) > 20]
    if not lines:
        return ""
    # Prefer lines with emotional keywords
    emotional_words = ['dil','pyar','tere','meri','raat','aankhon','yaad','judai',
                       'love','heart','pain','lost','miss','cry','tears','alone',
                       'broken','wait','gone','never','always','forever']
    for line in lines:
        if any(w in line.lower() for w in emotional_words):
            return line[:100]
    return lines[0][:100]


def run():
    if not os.path.exists(INPUT_PATH):
        log.error(f"Input not found: {INPUT_PATH}. Run youtube_scraper.py first.")
        return

    with open(INPUT_PATH, encoding="utf-8") as f:
        all_cities = json.load(f)

    result = {}
    total = sum(len(songs) for songs in all_cities.values())
    processed = 0

    for city, songs in all_cities.items():
        log.info(f"=== Processing {city} ({len(songs)} songs) ===")
        enriched = []

        for song in songs:
            processed += 1
            song_name, artist = extract_artist(song["title"], song["artist"])
            log.info(f"  [{processed}/{total}] '{song_name}' by {artist}")

            lyrics = ""
            genius_url = search_genius(song_name, artist)
            if genius_url:
                time.sleep(1.2)
                lyrics = scrape_lyrics(genius_url)
                log.info(f"    → {len(lyrics)} chars of lyrics")
            else:
                log.info(f"    → No Genius match")

            time.sleep(1.0)

            genres = detect_genre(song["title"], artist, lyrics)

            enriched.append({
                **song,
                "song_name":  song_name,
                "artist_name": artist,
                "lyrics":     lyrics,
                "lyrics_preview": get_quote(lyrics),
                "genres":     genres,
                "genius_url": genius_url,
            })

        result[city] = enriched

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    log.info(f"Saved enriched data → {OUTPUT_PATH}")
    return result


if __name__ == "__main__":
    run()
