/**
 * dashboard.js — Mood of the City (Light Theme Enhanced)
 */

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000' : '';

// ─── Color mappings ───────────────────────────────────────────────────────────
const MOOD_COLORS = {
  'Heartbreak / Longing': { dot: '#C96B10', badge_bg: 'rgba(201,107,16,.1)', badge_text: '#8A4200', badge_border: 'rgba(201,107,16,.25)' },
  'Hype / Anger':         { dot: '#B54166', badge_bg: 'rgba(181,65,102,.1)',  badge_text: '#7B1D41', badge_border: 'rgba(181,65,102,.25)' },
  'Joy / Celebration':    { dot: '#177A62', badge_bg: 'rgba(23,122,98,.1)',   badge_text: '#0A4D3A', badge_border: 'rgba(23,122,98,.25)'  },
  'Nostalgia / Calm':     { dot: '#5748B8', badge_bg: 'rgba(87,72,184,.1)',   badge_text: '#2E218A', badge_border: 'rgba(87,72,184,.25)'  },
  'Romance / Love':       { dot: '#C94F7A', badge_bg: 'rgba(201,79,122,.1)',  badge_text: '#8A1D47', badge_border: 'rgba(201,79,122,.25)' },
  'Devotion / Spiritual': { dot: '#8A5BAD', badge_bg: 'rgba(138,91,173,.1)',  badge_text: '#512579', badge_border: 'rgba(138,91,173,.25)' },
};

const EMOTION_COLORS = {
  joy:      '#177A62',
  sadness:  '#5748B8',
  anger:    '#B54166',
  fear:     '#8A5BAD',
  surprise: '#C96B10',
  disgust:  '#96805F',
  neutral:  '#7A8FA6',
};

const GENRE_COLORS = {
  'Bollywood':   '#C94F4F',
  'Indie':       '#1E8A8A',
  'Rap/Hip-Hop': '#A87E10',
  'Classical':   '#2D6E8C',
  'Folk':        '#A05C1A',
  'Pop':         '#B07E12',
  'Regional':    '#1A7A5A',
  'Romance':     '#B54166',
  'Party/Dance': '#8848B8',
};

const GENRE_EMOJI = {
  'Bollywood':   '🎬',
  'Indie':       '🎸',
  'Rap/Hip-Hop': '🎤',
  'Classical':   '🎻',
  'Folk':        '🪘',
  'Pop':         '⭐',
  'Regional':    '🌏',
  'Romance':     '🌹',
  'Party/Dance': '🔊',
};

const MOOD_EMOJIS = {
  'Heartbreak / Longing': '💔',
  'Hype / Anger':         '🔥',
  'Joy / Celebration':    '🎉',
  'Nostalgia / Calm':     '🌙',
  'Romance / Love':       '🌸',
  'Devotion / Spiritual': '🙏',
};

function fmtViews(n) {
  if (!n) return '';
  if (n >= 1e8) return (n / 1e7).toFixed(0) + 'Cr views';
  if (n >= 1e7) return (n / 1e7).toFixed(1) + 'Cr views';
  if (n >= 1e6) return (n / 1e5).toFixed(1) + 'L views';
  if (n >= 1e3) return (n / 1e3).toFixed(0) + 'K views';
  return n + ' views';
}

// ─── State ────────────────────────────────────────────────────────────────────
let cityData   = {};
let activeCity = null;
let activeTab  = 'overview';
let moodFilter = null;
let radarChart = null;
let genreChart = null;
let map        = null;
let markers    = {};

// ─── Init ─────────────────────────────────────────────────────────────────────
async function init() {
  initMap();
  await loadData();
  renderCitySwitcher();
  updateStats();
}

// ─── Map ──────────────────────────────────────────────────────────────────────
function initMap() {
  map = L.map('map', {
    center: [20.5937, 78.9629],
    zoom: 5,
    zoomControl: false,
    attributionControl: false,
  });

  // Warm light tile layer
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    opacity: 0.7,
  }).addTo(map);

  L.control.zoom({ position: 'bottomright' }).addTo(map);

  // Attribution small
  L.control.attribution({ position: 'bottomleft', prefix: false })
    .addAttribution('© OpenStreetMap contributors').addTo(map);
}

function addCityMarkers() {
  Object.values(markers).forEach(m => m.remove());
  markers = {};

  Object.entries(cityData).forEach(([cityName, data]) => {
    const moodCol = MOOD_COLORS[data.dominant_mood] || { dot: '#C96B10' };
    const color   = moodCol.dot;

    const html = `
      <div class="city-marker-wrap">
        <div class="city-pulse-ring" style="background:${color}40"></div>
        <div class="city-dot-shell" style="background:${color};box-shadow:0 0 0 4px ${color}28">
          <div class="city-dot-core"></div>
        </div>
        <div class="city-float-label">${cityName}</div>
      </div>`;

    const icon = L.divIcon({ html, className: '', iconSize: [44, 60], iconAnchor: [22, 22] });

    const marker = L.marker([data.lat, data.lng], { icon })
      .addTo(map)
      .on('click', () => selectCity(cityName));

    marker.bindTooltip(`
      <div style="font-family:'DM Sans',sans-serif;padding:4px 2px;min-width:160px">
        <strong style="font-family:'Playfair Display',serif;font-size:14px;color:#1C1208">${cityName}</strong><br>
        <span style="font-size:12px;color:#5A4530;font-weight:600">${data.dominant_mood}</span><br>
        <span style="font-size:11px;color:#96805F;font-style:italic">${data.insight || ''}</span>
      </div>`, {
      direction: 'top',
      offset: [0, -14],
      className: 'city-tt',
    });

    markers[cityName] = marker;
  });
}

// ─── Data ─────────────────────────────────────────────────────────────────────
async function loadData() {
  try {
    let res = await fetch(`${API_BASE}/api/mood-map`).catch(() => null);
    if (res && res.ok) {
      const slim = await res.json();
      const details = await Promise.all(
        Object.keys(slim).map(city =>
          fetch(`${API_BASE}/api/city/${encodeURIComponent(city)}`)
            .then(r => r.ok ? r.json() : null).catch(() => null)
        )
      );
      Object.keys(slim).forEach((city, i) => { if (details[i]) cityData[city] = details[i]; });
    } else {
      res = await fetch('./demo_data.json').catch(() => null);
      if (!res || !res.ok) res = await fetch('../data/demo_data.json');
      cityData = await res.json();
    }

    document.getElementById('last-updated').textContent =
      new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

    addCityMarkers();
    const firstCity = Object.keys(cityData)[0];
    if (firstCity) selectCity(firstCity);
  } catch (err) {
    console.error('Data load failed:', err);
    document.getElementById('last-updated').textContent = 'Demo mode';
  }
}

// ─── City selection ───────────────────────────────────────────────────────────
function selectCity(cityName) {
  activeCity = cityName;
  const data = cityData[cityName];
  if (!data) return;

  document.querySelectorAll('.city-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.city === cityName));

  map.flyTo([data.lat, data.lng], 7, { duration: 1 });

  Object.entries(markers).forEach(([name, marker]) => {
    const shell = marker.getElement()?.querySelector('.city-dot-shell');
    if (shell) {
      shell.style.transform = name === cityName ? 'scale(1.4)' : 'scale(1)';
      shell.style.opacity   = name === cityName ? '1' : '0.6';
    }
  });

  renderPanel(data);
}

// ─── Panel ────────────────────────────────────────────────────────────────────
function renderPanel(data) {
  renderOverview(data);
  renderEmotions(data);
  renderSongs(data);
  renderGenres(data);
}

function renderOverview(data) {
  const mc = MOOD_COLORS[data.dominant_mood] || { dot: '#C96B10', badge_bg: '#FFF0E0', badge_text: '#8A4200', badge_border: 'rgba(201,107,16,.25)' };
  const color = mc.dot;

  document.getElementById('empty-overview').style.display = 'none';
  document.getElementById('city-overview').style.display  = 'block';

  document.getElementById('ov-city-name').innerHTML = data.city.replace(/(\w+)/, '<em>$1</em>');
  document.getElementById('ov-tagline').textContent  = data.insight || '';

  // Header background gradient using mood color
  const hdrPanel = document.getElementById('city-header-panel');
  hdrPanel.style.background = `linear-gradient(160deg, ${color}10 0%, #FFFFFF 70%)`;
  hdrPanel.style.borderBottom = `1px solid ${color}22`;

  document.getElementById('hdr-bg').style.background =
    `radial-gradient(ellipse at 80% 30%, ${color}18 0%, transparent 65%)`;
  document.getElementById('hdr-ornament').style.color = color;

  const badge = document.getElementById('ov-mood-badge');
  badge.textContent = (MOOD_EMOJIS[data.dominant_mood] || '🎵') + ' ' + data.dominant_mood;
  badge.style.background   = mc.badge_bg;
  badge.style.color        = mc.badge_text;
  badge.style.borderColor  = mc.badge_border;

  // Mood distribution
  const dist   = data.mood_distribution || {};
  const distEl = document.getElementById('ov-mood-dist');
  distEl.innerHTML = Object.entries(dist)
    .sort((a, b) => b[1] - a[1])
    .map(([mood, pct]) => {
      const c = (MOOD_COLORS[mood] || { dot: '#96805F' }).dot;
      return `<div class="mood-dist-item">
        <div class="mood-dist-head">
          <div class="mood-dist-name">${MOOD_EMOJIS[mood] || ''} ${mood}</div>
          <div class="mood-dist-pct">${pct}%</div>
        </div>
        <div class="mood-dist-track">
          <div class="mood-dist-fill" style="width:0%;background:${c}" data-w="${pct}"></div>
        </div>
      </div>`;
    }).join('');

  // Animate bars on next tick
  requestAnimationFrame(() => {
    distEl.querySelectorAll('.mood-dist-fill').forEach(el =>
      el.style.width = el.dataset.w + '%'
    );
  });

  document.getElementById('ov-song-count').textContent =
    data.song_count || data.songs?.length || 0;
}

function renderEmotions(data) {
  document.getElementById('empty-emotions').style.display   = 'none';
  document.getElementById('emotions-content').style.display = 'block';

  const emotions = data.emotion_breakdown || {};
  const sorted   = Object.entries(emotions).sort((a, b) => b[1] - a[1]);

  document.getElementById('emotion-bars').innerHTML = sorted.map(([emo, val]) => `
    <div class="ebar">
      <div class="ebar-label">${emo}</div>
      <div class="ebar-track">
        <div class="ebar-fill" style="width:0%;background:${EMOTION_COLORS[emo]||'#96805F'}" data-w="${val}"></div>
      </div>
      <div class="ebar-val">${val}%</div>
    </div>`).join('');

  requestAnimationFrame(() => {
    document.querySelectorAll('#emotion-bars .ebar-fill').forEach(el =>
      el.style.width = el.dataset.w + '%'
    );
  });

  // Radar chart
  if (radarChart) { radarChart.destroy(); radarChart = null; }
  const labels = sorted.map(([k]) => k.charAt(0).toUpperCase() + k.slice(1));
  const values = sorted.map(([, v]) => v);
  const colors = sorted.map(([k]) => EMOTION_COLORS[k] || '#96805F');
  const mc     = MOOD_COLORS[data.dominant_mood] || { dot: '#C96B10' };

  const ctx = document.getElementById('emotion-radar').getContext('2d');
  radarChart = new Chart(ctx, {
    type: 'radar',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: mc.dot + '18',
        borderColor:     mc.dot,
        borderWidth:     2,
        pointBackgroundColor: colors,
        pointRadius: 4,
        pointHoverRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        r: {
          min: 0, max: 100,
          ticks: { display: false },
          grid:  { color: 'rgba(60,35,10,.08)' },
          pointLabels: {
            color: '#5A4530',
            font: { family: "'JetBrains Mono', monospace", size: 10 }
          },
          angleLines: { color: 'rgba(60,35,10,.06)' },
        }
      }
    }
  });
}

function renderSongs(data) {
  document.getElementById('empty-songs').style.display = 'none';
  const container = document.getElementById('songs-content');
  container.style.display = 'block';

  const songs = data.songs || [];
  if (!songs.length) {
    container.innerHTML = '<div class="empty-state"><p>No song data yet</p></div>';
    return;
  }

  container.innerHTML = songs.map((song, i) => {
    const mc   = song.mood_color || '#C96B10';
    const mc2  = (() => {
      const g = song.genres?.[0];
      return GENRE_COLORS[g] || '#B54166';
    })();

    const genreTags = (song.genres || []).map(g => {
      const col = GENRE_COLORS[g] || '#96805F';
      return `<span class="song-genre-tag" style="color:${col};border-color:${col}33;background:${col}0E">${GENRE_EMOJI[g]||''} ${g}</span>`;
    }).join('');

    const comments = (song.top_comments || []).slice(0, 2).map(c =>
      `<div class="comment-chip">${c}</div>`).join('');

    const thumb = song.thumbnail
      ? `<img class="song-thumb" src="${song.thumbnail}" alt="" loading="lazy"/>`
      : `<div class="song-thumb-ph">${GENRE_EMOJI[song.genres?.[0]] || '🎵'}</div>`;

    const ytLink = song.url
      ? `<a class="song-yt" href="${song.url}" target="_blank" rel="noopener">↗ YT</a>`
      : '';

    return `<div class="song-card" style="--card-c:${mc};--card-c2:${mc2};animation-delay:${i * 0.05}s">
      <div class="song-top">
        ${thumb}
        <div class="song-info">
          <div class="song-title">${song.title}</div>
          <div class="song-artist">${song.artist}${ytLink}</div>
          <div class="song-views">${fmtViews(song.views)}</div>
        </div>
      </div>
      ${genreTags ? `<div class="song-genres">${genreTags}</div>` : ''}
      ${song.lyrics_preview ? `<div class="song-quote" style="border-color:${mc}">${song.lyrics_preview}</div>` : ''}
      ${comments ? `<div class="song-comments">${comments}</div>` : ''}
    </div>`;
  }).join('');
}

function renderGenres(data) {
  document.getElementById('empty-genres').style.display   = 'none';
  document.getElementById('genres-content').style.display = 'block';

  const genres  = data.genre_breakdown || {};
  const entries = Object.entries(genres).sort((a, b) => b[1].count - a[1].count);

  document.getElementById('genre-pills').innerHTML = entries.map(([g, info]) => {
    const col = GENRE_COLORS[g] || info.color || '#96805F';
    return `<div class="genre-pill" style="color:${col};border-color:${col}44;background:${col}0D">
      ${GENRE_EMOJI[g] || ''} ${g} <span style="opacity:.55;font-weight:400">${info.count}</span>
    </div>`;
  }).join('');

  if (genreChart) { genreChart.destroy(); genreChart = null; }
  const ctx = document.getElementById('genre-chart').getContext('2d');
  genreChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: entries.map(([g]) => g),
      datasets: [{
        data:            entries.map(([, v]) => v.count),
        backgroundColor: entries.map(([g]) => (GENRE_COLORS[g] || '#96805F') + 'CC'),
        borderColor:     entries.map(([g]) => GENRE_COLORS[g] || '#96805F'),
        borderWidth: 2,
        hoverOffset: 8,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '62%',
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: '#5A4530',
            font:  { family: "'JetBrains Mono', monospace", size: 10 },
            boxWidth: 10,
            padding: 8,
          }
        }
      }
    }
  });
}

// ─── Tab switching ────────────────────────────────────────────────────────────
function switchTab(tab) {
  activeTab = tab;
  document.querySelectorAll('.tab-view').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(el => el.classList.toggle('active', el.dataset.tab === tab));
  document.getElementById(`tab-${tab}`).classList.add('active');
}

// ─── City switcher ────────────────────────────────────────────────────────────
function renderCitySwitcher() {
  const container = document.getElementById('city-switcher');
  const label = container.querySelector('.cs-label');
  container.innerHTML = '';
  if (label) container.appendChild(label);
  Object.keys(cityData).forEach(city => {
    const btn = document.createElement('button');
    btn.className = 'city-btn';
    btn.dataset.city = city;
    btn.textContent = city;
    btn.onclick = () => selectCity(city);
    container.appendChild(btn);
  });
}

// ─── Stats ────────────────────────────────────────────────────────────────────
function updateStats() {
  const cities      = Object.values(cityData);
  const totalSongs  = cities.reduce((s, c) => s + (c.song_count || c.songs?.length || 0), 0);
  const moodCounts  = {};
  const genreCounts = {};

  cities.forEach(c => {
    const m = c.dominant_mood;
    if (m) moodCounts[m] = (moodCounts[m] || 0) + 1;
    Object.keys(c.genre_breakdown || {}).forEach(g => {
      genreCounts[g] = (genreCounts[g] || 0) + (c.genre_breakdown[g].count || 0);
    });
  });

  const topMood  = Object.entries(moodCounts).sort((a, b) => b[1] - a[1])[0];
  const topGenre = Object.entries(genreCounts).sort((a, b) => b[1] - a[1])[0];

  document.getElementById('stat-songs').textContent     = totalSongs || '—';
  document.getElementById('stat-top-mood').textContent  = topMood  ? topMood[0].split('/')[0].trim()  : '—';
  document.getElementById('stat-top-genre').textContent = topGenre ? topGenre[0] : '—';
}

// ─── Mood filter ──────────────────────────────────────────────────────────────
function filterByMood(mood) {
  moodFilter = mood;
  Object.entries(markers).forEach(([cityName, marker]) => {
    const data = cityData[cityName];
    const show = !mood || data?.dominant_mood === mood;
    const el   = marker.getElement();
    if (el) el.style.opacity = show ? '1' : '0.15';
  });
}

// ─── Refresh ──────────────────────────────────────────────────────────────────
async function triggerRefresh() {
  const btn = document.querySelector('.refresh-btn');
  btn.textContent = '⟳ Running…';
  btn.disabled = true;
  try {
    const res = await fetch(`${API_BASE}/api/refresh`, { method: 'POST' });
    if (res.ok) {
      btn.textContent = '✓ Started';
      setTimeout(() => { btn.textContent = '↻ Refresh'; btn.disabled = false; loadData(); }, 8000);
    } else throw new Error();
  } catch {
    btn.textContent = '↻ Refresh';
    btn.disabled = false;
    alert('Could not reach API. Make sure the backend is running on localhost:8000');
  }
}

// ─── Tooltip style ────────────────────────────────────────────────────────────
const ttStyle = document.createElement('style');
ttStyle.textContent = `
  .city-tt {
    background: rgba(255,255,255,.97) !important;
    border: 1px solid rgba(60,35,10,.15) !important;
    color: #1C1208 !important;
    border-radius: 10px !important;
    padding: 9px 13px !important;
    box-shadow: 0 4px 20px rgba(0,0,0,.12) !important;
    font-size: 12px !important;
    backdrop-filter: blur(10px) !important;
  }
  .city-tt::before { display: none !important; }
  .leaflet-attribution-flag { display: none !important; }
  .leaflet-control-attribution {
    font-size: 9px !important;
    background: rgba(255,255,255,.7) !important;
    border-radius: 4px !important;
    padding: 2px 6px !important;
    color: #96805F !important;
  }
`;
document.head.appendChild(ttStyle);

// ─── Boot ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
