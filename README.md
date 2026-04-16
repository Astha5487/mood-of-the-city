<div align="center">

# 🎵 Mood of the City
### Emotional Geography of Indian Music — Live

<img src="https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
<img src="https://img.shields.io/badge/HuggingFace-Transformers-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black"/>
<img src="https://img.shields.io/badge/Leaflet.js-Map-199900?style=for-the-badge&logo=leaflet&logoColor=white"/>
<img src="https://img.shields.io/badge/Chart.js-Visualizations-FF6384?style=for-the-badge&logo=chart.js&logoColor=white"/>

<br/>

> **"What is each Indian city feeling right now, based on what music it's listening to?"**

*A live emotional heatmap of India — built by scraping YouTube trending music + Genius.com lyrics, running NLP emotion detection, and rendering a living atlas of city moods.*

<br/>

**[🎥 Watch Demo Video](https://drive.google.com/file/d/1p89ay02Z_63w1mIZm6e9tVbHn7J7GglN/view?usp=drive_link)**

</div>

---

## 🧠 The Idea

Nobody has mapped the **emotional geography of India through music consumption** — until now.

Every week, cities across India tell different stories through what they listen to:

- 💔 **Mumbai** is binging breakup ballads at 3am
- 🔥 **Delhi** is rage-listening to Desi hip-hop
- 🌙 **Bangalore** is deep in nostalgic lo-fi indie
- 🎉 **Kolkata** is celebrating with Durga Puja anthems
- 🙏 **Chennai** is in devotional mode with classical + bhajan

This project scrapes real trending music data, runs emotion AI on the lyrics and comments, and renders it as a **live interactive map** that journalists, researchers, and curious people would actually want to look at.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🗺️ **Live Emotional Map** | Interactive India map with pulsing city markers colored by dominant mood |
| 🎭 **7-Emotion NLP** | HuggingFace model scores joy, sadness, anger, fear, disgust, surprise, neutral per song |
| 🎵 **Genre Classification** | Auto-tags songs as Bollywood, Indie, Rap/Hip-Hop, Classical, Folk, Regional, etc. |
| 📊 **Radar + Doughnut Charts** | Per-city emotion radar and genre breakdown via Chart.js |
| 🔄 **Live Refresh** | One-click pipeline trigger refreshes all 8 cities every 6 hours |
| 📱 **Song Cards** | Top trending songs per city with lyrics preview + top YouTube comments |
| ⚖️ **View-Count Weighting** | Viral songs (100M views) influence city mood more than obscure tracks |
| 🏙️ **8 Indian Cities** | Mumbai, Delhi, Bangalore, Kolkata, Chennai, Hyderabad, Pune, Jaipur |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA PIPELINE                                │
│                                                                     │
│  YouTube Search  →  yt-dlp metadata  →  Genius.com lyrics          │
│       ↓                                      ↓                     │
│  YT Comments API          Genre keyword detection                   │
│       ↓                                      ↓                     │
│          HuggingFace distilroberta-base emotion model               │
│          joy | sadness | anger | fear | disgust | surprise          │
│                              ↓                                      │
│          City Aggregator (log-weighted by view count)               │
│          → dominant mood + genre breakdown + insight                │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                    data/city_moods.json
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                        BACKEND (FastAPI)                            │
│                                                                     │
│  GET /api/mood-map     →  all 8 cities overview                     │
│  GET /api/city/{name}  →  full detail + song list                   │
│  GET /api/genres       →  genre totals                              │
│  POST /api/refresh     →  trigger pipeline in background            │
│  APScheduler           →  auto-refresh every 6 hours               │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                       FRONTEND                                      │
│                                                                     │
│  Leaflet.js map  →  pulsing city markers (colored by mood)          │
│  Side panel      →  Overview | Emotions | Songs | Genres tabs       │
│  Chart.js        →  Radar chart (emotions) + Doughnut (genres)      │
│  Song cards      →  thumbnail + lyrics preview + comments           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
mood-of-the-city/
│
├── scraper/
│   ├── youtube_scraper.py     # yt-dlp: city-specific trending song search
│   ├── genius_scraper.py      # BeautifulSoup: lyrics + genre keyword tagging
│   └── comment_scraper.py     # YouTube Data API v3: top comments per video
│
├── analyzer/
│   ├── emotion_engine.py      # HuggingFace pipeline: 7-class emotion scoring
│   └── city_aggregator.py     # View-weighted aggregation → city mood profiles
│
├── backend/
│   ├── app.py                 # FastAPI app: all API endpoints + static serving
│   └── scheduler.py           # APScheduler: runs full pipeline every 6h (IST)
│
├── frontend/
│   ├── index.html             # Leaflet.js map, tabs, legend, stats bar
│   ├── dashboard.js           # All interactivity: markers, charts, panels
│   └── demo_data.json         # Pre-loaded 8-city data (works offline)
│
├── data/                      # Auto-generated by pipeline (gitignored except demo)
│   ├── demo_data.json         # Bundled demo — app works without running pipeline
│   ├── youtube_raw.json       # Raw yt-dlp output
│   ├── songs_with_lyrics.json # + Genius lyrics + genre tags
│   ├── songs_enriched.json    # + YouTube comments
│   └── songs_with_emotions.json # + HuggingFace emotion scores
│
├── Dockerfile                 # Production Docker image (CPU torch, slim)
├── render.yaml                # Render deployment config
├── requirements.txt
└── runtime.txt

---

## 🚀 Quick Start

### Option A — Demo Mode (no install, 30 seconds)

```bash
git clone https://github.com/YOUR_USERNAME/mood-of-the-city.git
cd mood-of-the-city/frontend
python -m http.server 3000
```
Open **http://localhost:3000** — fully interactive map loads from `demo_data.json`.

---

### Option B — Full Live Scraping Mode

**1. Clone and install**
```bash
git clone https://github.com/YOUR_USERNAME/mood-of-the-city.git
cd mood-of-the-city
pip install -r requirements.txt
```

**2. Set your YouTube API key**
```bash
cp .env.example .env
# Edit .env and paste your key from https://console.cloud.google.com
export YOUTUBE_API_KEY="your_key_here"
```

**3. Run the pipeline (one-time)**
```bash
# Scrape trending songs per city (~2 min)
python -m scraper.youtube_scraper

# Get lyrics from Genius.com (~5 min)
python -m scraper.genius_scraper

# Fetch YouTube comments — needs API key (~3 min)
python -m scraper.comment_scraper

# Run emotion AI — downloads ~250MB model on first run (~10 min)
python -m analyzer.emotion_engine

# Aggregate into city mood profiles (~5 sec)
python -m analyzer.city_aggregator
```

**4. Start the server**
```bash
uvicorn backend.app:app --reload --port 8000
```

Open **http://localhost:8000** 🎉

**5. Auto-refresh every 6 hours** (optional)
```bash
# In a second terminal
python -m backend.scheduler
```

---

## Screenshots of Project

### Project Snapshot 1
![Screenshot 1](https://github.com/user-attachments/assets/aabacaca-201a-489b-bdfa-a30141aaf26f)

### Project Snapshot 2
![Screenshot 2](https://github.com/user-attachments/assets/e18a4928-053b-4ac3-9e33-11054afb85de)

### Project Snapshot 3
![Screenshot 3](https://github.com/user-attachments/assets/816f665c-431c-4a5c-a996-5a2382f931fe)

---


## 🎭 How Emotions Map to City Moods

The HuggingFace model (`j-hartmann/emotion-english-distilroberta-base`) outputs 7 raw emotion scores per song. These are combined with **genre signals** and **comment sentiment** to produce a city-level mood label:

| Raw Emotion Profile | City Mood Label | Color |
|---|---|---|
| High `sadness` | 💔 Heartbreak / Longing | 🟡 Amber |
| High `anger` + `surprise` | 🔥 Hype / Anger | 🔴 Red |
| High `joy` + `surprise` | 🎉 Joy / Celebration | 🟢 Green |
| High `neutral` + `sadness` | 🌙 Nostalgia / Calm | 🟣 Purple |
| High `joy` + `fear` | 🌸 Romance / Love | 🩷 Pink |
| High `fear` + `neutral` | 🙏 Devotion / Spiritual | 🟣 Indigo |

**Tiebreaker logic:** When the emotion model collapses (happens with Bollywood lyrics — they all score as "sad"), the system uses genre composition as a fallback:
- Rap/Hip-Hop city → Hype / Anger
- Folk-heavy city → Joy / Celebration  
- Classical-heavy → Devotion / Spiritual
- Indie-heavy → Nostalgia / Calm

---

## 🎸 Genre Classification

Songs are tagged by scanning title + artist + lyrics for genre keywords:

| Genre | Keywords Detected |
|---|---|
| 🎬 Bollywood | bollywood, hindi film, filmi |
| 🎤 Rap/Hip-Hop | rap, hip hop, cypher, desi hip hop, bars |
| 🎸 Indie | indie, independent, lo-fi, alternative |
| 🎻 Classical | raga, carnatic, hindustani, bhajan, kirtan |
| 🪘 Folk | folk, bhangra, garba, lavani, rajasthani |
| 🔊 Party/Dance | party, dj, remix, edm, club |
| 🌏 Regional | punjabi, tamil, telugu, kannada, bengali |
| 🌹 Romance | love, romantic, wedding, dulhan |
| ⭐ Pop | pop, chart, viral, trending |

---

## 📊 API Reference

| Endpoint | Method | Description | Response |
|---|---|---|---|
| `/` | GET | Serves the frontend | HTML |
| `/health` | GET | Server + data status | `{status, data_ready, last_updated}` |
| `/api/mood-map` | GET | All 8 cities overview | `{city: {dominant_mood, colors, insight, ...}}` |
| `/api/city/{name}` | GET | Full city detail + songs | `{songs[], emotion_breakdown, genre_breakdown, ...}` |
| `/api/genres` | GET | Genre totals across all cities | `{Bollywood: 42, Indie: 28, ...}` |
| `/api/trending` | GET | Top songs by view count | `[{title, artist, views, city, ...}]` |
| `/api/refresh` | POST | Trigger pipeline in background | `{status: "started"}` |

Interactive API docs: **`http://localhost:8000/docs`**

---

## 🐳 Docker

```bash
# Build
docker build -t mood-of-the-city .

# Run
docker run -p 8000:8000 -e YOUTUBE_API_KEY=your_key mood-of-the-city

# Open http://localhost:8000
```

---

## ☁️ Deploy to Railway (Free, 5 minutes)

1. Fork this repo
2. Go to **railway.app → New Project → Deploy from GitHub**
3. Select this repo — Railway detects `Dockerfile` + `railway.toml` automatically
4. Add env variable: `YOUTUBE_API_KEY` = your key
5. Click **Generate Domain** under Settings → Networking
6. Your app is live 🎉


---

## 🛠 Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Scraping** | yt-dlp, requests, BeautifulSoup, lxml | Reliable, handles YouTube's anti-scraping |
| **NLP** | HuggingFace Transformers, distilroberta-base | 7-class emotion, 250MB, CPU-friendly |
| **Backend** | FastAPI + Uvicorn | Async, auto-docs, production-ready |
| **Scheduling** | APScheduler | In-process 6h refresh without cron |
| **Frontend** | Leaflet.js + Chart.js | Lightweight, no framework needed |
| **Typography** | Syne (display) + DM Sans (body) | Distinctive, editorial feel |
| **Deploy** | Docker + Railway / Render | Free tier, auto-deploys from GitHub |
| **Data** | JSON files | No DB overhead for hackathon scale |

---

## 📝 Ethical Scraping

This project follows responsible scraping practices:

- ✅ **Public data only** — no logins, no bypassing paywalls
- ✅ **Respectful delays** — 1–2 second pause between every request
- ✅ **No personal data** — no emails, phone numbers, or private profiles collected
- ✅ **YouTube API within quota** — 10,000 free units/day; we use ~800/run
- ✅ **Graceful failures** — every scraper has try/catch; one failed song doesn't break the run
- ✅ **Read-only** — we never post, interact, or modify anything

---

## 🤔 Why This Project?

Most hackathon data projects: scrape → bar chart → done.

This project maps something **nobody has mapped before** — the emotional pulse of Indian cities through music, updated live. The insight that "Mumbai is heartbroken this week while Delhi is angry" is a story that:

- 📰 Journalists would cover
- 🎓 Researchers in music sociology would cite  
- 👥 Regular people would share

The technical stack is intentionally **full-pipeline**: scraping → NLP → API → interactive visualization, with real data that changes over time.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built for **Mindcase Hackathon 2025** · Made with 🎵 and Python

*If this made you curious about what your city is feeling — that's the whole point.*

</div>
