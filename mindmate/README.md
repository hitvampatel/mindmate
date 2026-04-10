# 🧠 MindMate — AI Mental Health Companion for Students
### Complete Flask Backend · Production-Ready · Hackathon Edition

---

## 📁 Project Structure

```
mindmate/
├── app.py                         ← Entry point — run this
├── config.py                      ← All configuration settings
├── extensions.py                  ← Shared Flask extensions (db, bcrypt, jwt)
├── requirements.txt               ← Python dependencies
├── mindmate.db                    ← SQLite database (auto-created on first run)
│
├── models/
│   └── __init__.py                ← Database models (User, ChatMessage, MoodEntry, SentimentLog)
│
├── routes/
│   ├── auth_routes.py             ← /api/auth/* — signup, login, logout, profile
│   ├── chat_routes.py             ← /api/chat, /api/sentiment-score
│   ├── mood_routes.py             ← /api/mood-submit, /api/mood-history
│   └── dashboard_routes.py        ← /api/dashboard-data, /api/dashboard-stats
│
├── services/
│   ├── sentiment_service.py       ← TextBlob sentiment analysis + crisis detection
│   └── ai_service.py              ← AI response generation engine
│
└── utils/
    └── validators.py              ← Input validation helpers
```

---

## ⚡ Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
python -m textblob.download_corpora   # Download TextBlob NLP data
```

### 2. Run the server
```bash
python app.py
# 🚀 MindMate backend running at http://localhost:5000
```

### 3. Test it
```bash
curl http://localhost:5000/
# {"app": "MindMate API", "status": "ok", "version": "1.0.0"}
```

---

## 🔌 Complete API Reference

### BASE URL: `http://localhost:5000/api`

All protected routes require the header:
```
Authorization: Bearer <access_token>
```

---

### 🔐 Authentication

#### POST /auth/signup
Register a new student account.
```json
// Request
{
  "username": "rahul_dev",
  "email": "rahul@college.edu",
  "password": "securepass123"
}

// Response 201
{
  "success": true,
  "message": "Welcome to MindMate, rahul_dev! 🎉",
  "user": { "id": 1, "username": "rahul_dev", "email": "rahul@college.edu" },
  "access_token": "eyJ...",
  "refresh_token": "eyJ..."
}
```

#### POST /auth/login
```json
// Request (use email OR username)
{ "email": "rahul@college.edu", "password": "securepass123" }

// Response 200
{
  "success": true,
  "message": "Welcome back, rahul_dev! 💙",
  "user": { ... },
  "access_token": "eyJ...",
  "refresh_token": "eyJ..."
}
```

#### POST /auth/logout  *(Protected)*
```json
// Response 200
{ "success": true, "message": "You've been logged out. Take care! 🌟" }
```

#### GET /auth/me  *(Protected)*
Returns current user's profile.

---

### 💬 Chat

#### POST /chat  *(Protected)*
Send a message to the AI companion.
```json
// Request
{ "message": "I've been feeling really overwhelmed with exams lately..." }

// Response 200
{
  "success": true,
  "user_message": {
    "id": 1, "role": "user", "content": "...",
    "sentiment_polarity": -0.3, "sentiment_label": "negative",
    "crisis_detected": false, "timestamp": "2025-01-01T10:30:00"
  },
  "ai_response": {
    "id": 2, "role": "assistant",
    "content": "I'm sorry you're going through a tough time...",
    "wellness_tip": "🌬️ Try box breathing: inhale 4 counts...",
    "follow_up": "On a scale of 1–10, how heavy does this feel right now?",
    "show_resources": false
  },
  "sentiment": {
    "polarity": -0.3, "subjectivity": 0.7,
    "label": "negative", "emoji": "😟", "color": "#f59e0b",
    "advice": "It sounds like things feel a bit heavy...",
    "interpretation": "Your message carries some negative feelings..."
  },
  "crisis_info": { "crisis_detected": false }
}
```

#### GET /chat/history  *(Protected)*
```
GET /chat/history?page=1&limit=20
```

#### DELETE /chat/history  *(Protected)*
```json
{ "confirm": true }
```

---

### 📊 Mood Tracking

#### POST /mood-submit  *(Protected)*
```json
// Request
{
  "mood_score": 4,           // Required: 1–10
  "mood_label": "anxious",   // Optional
  "note": "Feeling pressure from upcoming exams",
  "energy": 2,               // Optional: 1–5
  "sleep_hrs": 5.5           // Optional
}

// Response 201
{
  "success": true,
  "message": "I hear you — tough days are real. Be gentle with yourself today. 🌱",
  "entry": { "id": 1, "mood_score": 4, "mood_label": "anxious", ... }
}
```

Valid mood labels: `happy, calm, neutral, anxious, sad, angry, stressed,
excited, grateful, lonely, overwhelmed, hopeful, tired, motivated, confused`

#### GET /mood-history  *(Protected)*
```
GET /mood-history?days=14&limit=30
```
Returns entries + stats (avg, min, max, trend).

#### GET /mood-today  *(Protected)*
Returns today's check-in status.

---

### 🔍 Sentiment Score

#### POST /sentiment-score  *(Protected)*
Analyse any text's emotional tone.
```json
// Request
{ "text": "I feel so stressed about tomorrow's presentation" }

// Response 200
{
  "success": true,
  "sentiment": {
    "polarity": -0.4, "subjectivity": 0.8,
    "label": "negative", "emoji": "😟",
    "advice": "...", "interpretation": "..."
  }
}
```

---

### 📈 Dashboard

#### GET /dashboard-data  *(Protected)*
Full analytics payload including:
- Mood chart (last 14 days)
- Sentiment chart (last 14 days)
- Mood label distribution
- Wellness score (0–100)
- Check-in streak
- AI-generated insights

#### GET /dashboard-stats  *(Protected)*
Quick KPI summary (avg mood, streak, message count).

---

## 🗄️ Database Schema

```
users
  id, username, email, password_hash, created_at, last_login, is_active

chat_messages
  id, user_id, role, content, timestamp,
  sentiment_polarity, sentiment_subjectivity, sentiment_label, crisis_detected

mood_entries
  id, user_id, mood_score, mood_label, note, energy, sleep_hrs, timestamp

sentiment_logs
  id, user_id, date, avg_polarity, avg_subjectivity, message_count, dominant_emotion
```

---

## ⚙️ Tech Stack

| Layer              | Technology          | Why                              |
|--------------------|---------------------|----------------------------------|
| Web Framework      | Flask 3.0           | Lightweight, fast, Pythonic      |
| Database           | SQLite + SQLAlchemy | Zero-config, great for hackathon |
| Auth               | Flask-JWT-Extended  | Stateless, scalable JWT tokens   |
| Password Hashing   | Flask-Bcrypt        | Industry-standard security       |
| Sentiment Analysis | TextBlob            | Simple, accurate, no API needed  |
| CORS               | Flask-CORS          | Enables React/Vue frontend       |

---

## 🛡️ Ethical AI Principles

- ✅ **No diagnosis** — MindMate never claims to diagnose conditions
- ✅ **Crisis safety** — keyword detection surfaces real helpline resources
- ✅ **Privacy first** — triggered crisis keywords are logged internally only
- ✅ **Professional referral** — always nudges toward real human support
- ✅ **No data selling** — architecture designed for user data sovereignty

---

## 🚀 Production Checklist

- [ ] Replace `SECRET_KEY` with env variable
- [ ] Switch SQLite → PostgreSQL for scale
- [ ] Add Redis for JWT blocklist (logout invalidation)
- [ ] Add rate limiting (Flask-Limiter)
- [ ] Add HTTPS (nginx/gunicorn)
- [ ] Swap rule-based AI → OpenAI GPT-4 via same `generate_ai_response()` interface
