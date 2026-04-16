# 🎵 Mood of the City — Emotional Geography of Indian Music

> *"What is each Indian city feeling right now, based on what music it's listening to?"*

A live emotional heatmap of India built by scraping YouTube trending music + Genius lyrics,
running NLP emotion detection, and rendering a living atlas of city moods.

---

## 📁 Project Structure

```
mood-of-the-city/
├── scraper/
│   ├── youtube_scraper.py    # yt-dlp: trending songs per city
│   ├── genius_scraper.py     # BeautifulSoup: lyrics + genre detection
│   └── comment_scraper.py    # YouTube API v3: top comments per song
├── analyzer/
│   ├── emotion_engine.py     # HuggingFace: joy/sadness/anger/fear scores
│   └── city_aggregator.py    # Weighted aggregation → city mood profiles
├── backend/
│   ├── app.py                # FastAPI: /api/mood-map, /api/city/{name}
│   └── scheduler.py          # APScheduler: reruns pipeline every 6h
├── frontend/
│   ├── index.html            # Leaflet.js map + full UI
│   ├── dashboard.js          # Chart.js + all interactive logic
│   └── demo_data.json        # Pre-loaded data (works without backend)
├── data/                     # Pipeline outputs (auto-generated)
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start (Demo Mode — no scraping needed)

Open the frontend directly:
```bash
cd frontend
python -m http.server 3000
# Open http://localhost:3000
```

The app loads `demo_data.json` automatically and works fully without the backend.

---

## 🔧 Full Setup (Live Scraping)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Get a YouTube Data API v3 key (free)
- Go to https://console.cloud.google.com/apis/library/youtube.googleapis.com
- Enable the API → Create credentials → API Key
- Set it:
```bash
export YOUTUBE_API_KEY="your_key_here"
```

### 3. Run the pipeline manually
```bash
# Step 1: Scrape trending songs from YouTube
python -m scraper.youtube_scraper

# Step 2: Get lyrics from Genius.com
python -m scraper.genius_scraper

# Step 3: Fetch YouTube comments (needs API key)
python -m scraper.comment_scraper

# Step 4: Run emotion analysis (downloads ~250MB model on first run)
python -m analyzer.emotion_engine

# Step 5: Aggregate city mood profiles
python -m analyzer.city_aggregator
```

### 4. Start the backend
```bash
uvicorn backend.app:app --reload --port 8000
```

### 5. Open the app
```
http://localhost:8000
```

---

## 🔄 Automated Refresh (every 6 hours)

Run the scheduler in a separate terminal:
```bash
python -m backend.scheduler
```

Or use the **↻ Refresh data** button in the UI to trigger a manual pipeline run.

---

## 📊 API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/mood-map` | All 8 cities, slim overview data |
| `GET /api/city/{name}` | Full city detail + song list |
| `GET /api/genres` | Genre totals across all cities |
| `GET /api/trending` | Top songs by view count |
| `POST /api/refresh` | Trigger background pipeline run |
| `GET /health` | Server + data status |

---

## 🧠 How It Works

```
YouTube trending search
        ↓
  yt-dlp extracts metadata (title, artist, views, video_id)
        ↓
  Genius.com scraper finds lyrics
        ↓
  YouTube API fetches top 40 comments per song
        ↓
  HuggingFace emotion model (distilroberta-base)
  → joy, sadness, anger, fear, disgust, surprise, neutral
        ↓
  City aggregator: view-count weighted average
  → dominant mood, genre breakdown, insight headline
        ↓
  FastAPI serves /api/mood-map
        ↓
  Leaflet.js renders the emotional atlas
```

### Emotion → Mood mapping

| Raw emotions | Mood label |
|---|---|
| High sadness | 💔 Heartbreak / Longing |
| High anger + surprise | 🔥 Hype / Anger |
| High joy + surprise | 🎉 Joy / Celebration |
| High neutral + sadness | 🌙 Nostalgia / Calm |
| High joy + fear | 🌸 Romance / Love |
| High fear + neutral | 🙏 Devotion / Spiritual |

### Genre detection
Lyrics + artist name are scanned for keywords mapping to:
Bollywood, Indie, Rap/Hip-Hop, Classical, Folk, Pop, Regional, Romance, Party/Dance

---

## 🎯 Why This Stands Out

- **Nobody has done emotional cartography of India through music** — this is a story journalists will actually write about
- Real scraping pipeline — no fake data when running live
- View-count weighted aggregation — viral songs influence the mood more
- Genre classification reveals cultural geography (Folk in Jaipur, Classical in Chennai, Rap in Delhi)
- Live refresh — the map changes as India's music taste changes

---

## 📝 Ethical Notes

- Only scrapes **public** data — no logins, no private data
- Respectful delays between requests (1-2s)
- No personal data collected (no emails, phone numbers)
- YouTube API used within free quota limits
- Genius.com scraped with standard delays

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Scraping | yt-dlp, requests, BeautifulSoup, lxml |
| NLP | HuggingFace Transformers, distilroberta-base |
| Backend | FastAPI, APScheduler, Uvicorn |
| Frontend | Leaflet.js, Chart.js, Syne + DM Sans fonts |
| Data | JSON files (no DB needed for hackathon) |
