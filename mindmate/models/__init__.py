"""
models/__init__.py — Database Models

Defines the shape of every table in the SQLite database.
Each class = one table. Each attribute = one column.

Tables:
  ┌──────────────────────────────────────────────┐
  │  User          → Registered students         │
  │  ChatMessage   → Conversation history        │
  │  MoodEntry     → Daily mood check-ins        │
  │  SentimentLog  → Per-message sentiment data  │
  └──────────────────────────────────────────────┘
"""

from datetime import datetime, timezone
from extensions import db


# ══════════════════════════════════════════════════════════════
# MODEL 1 — User
# ══════════════════════════════════════════════════════════════
class User(db.Model):
    """
    Represents a registered student.
    Passwords are NEVER stored in plain text — only bcrypt hashes.
    """
    __tablename__ = "users"

    id           = db.Column(db.Integer, primary_key=True)
    username     = db.Column(db.String(80),  unique=True, nullable=False)
    email        = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    # Account metadata
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login   = db.Column(db.DateTime, nullable=True)
    is_active    = db.Column(db.Boolean,  default=True)

    # Relationships — one user → many messages / moods
    messages     = db.relationship("ChatMessage", backref="user", lazy=True,
                                   cascade="all, delete-orphan")
    mood_entries = db.relationship("MoodEntry",   backref="user", lazy=True,
                                   cascade="all, delete-orphan")

    def to_dict(self):
        """Return a safe dict (NO password hash) for API responses."""
        return {
            "id":         self.id,
            "username":   self.username,
            "email":      self.email,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

    def __repr__(self):
        return f"<User {self.username}>"


# ══════════════════════════════════════════════════════════════
# MODEL 2 — ChatMessage
# ══════════════════════════════════════════════════════════════
class ChatMessage(db.Model):
    """
    Stores every message in a conversation.
    'role' = 'user' for student messages, 'assistant' for AI replies.
    """
    __tablename__ = "chat_messages"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    role         = db.Column(db.String(20),  nullable=False)   # 'user' | 'assistant'
    content      = db.Column(db.Text,        nullable=False)
    timestamp    = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))

    # Sentiment scores attached to this message
    sentiment_polarity    = db.Column(db.Float,   nullable=True)   # -1.0 to +1.0
    sentiment_subjectivity = db.Column(db.Float,  nullable=True)   # 0.0 to 1.0
    sentiment_label       = db.Column(db.String(20), nullable=True) # 'positive' etc.

    # Crisis flag — True if crisis keywords were detected
    crisis_detected = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id":                    self.id,
            "role":                  self.role,
            "content":               self.content,
            "timestamp":             self.timestamp.isoformat(),
            "sentiment_polarity":    self.sentiment_polarity,
            "sentiment_subjectivity": self.sentiment_subjectivity,
            "sentiment_label":       self.sentiment_label,
            "crisis_detected":       self.crisis_detected,
        }

    def __repr__(self):
        return f"<ChatMessage [{self.role}] user={self.user_id}>"


# ══════════════════════════════════════════════════════════════
# MODEL 3 — MoodEntry
# ══════════════════════════════════════════════════════════════
class MoodEntry(db.Model):
    """
    Daily emotional check-in submitted by the student.
    Mood scale: 1 (very bad) → 10 (excellent)
    """
    __tablename__ = "mood_entries"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    mood_score = db.Column(db.Integer,  nullable=False)       # 1–10
    mood_label = db.Column(db.String(30), nullable=True)      # 'happy', 'anxious', etc.
    note       = db.Column(db.Text,     nullable=True)        # Optional free-text note
    energy     = db.Column(db.Integer,  nullable=True)        # 1–5 energy level
    sleep_hrs  = db.Column(db.Float,    nullable=True)        # Hours of sleep

    timestamp  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id":         self.id,
            "mood_score": self.mood_score,
            "mood_label": self.mood_label,
            "note":       self.note,
            "energy":     self.energy,
            "sleep_hrs":  self.sleep_hrs,
            "timestamp":  self.timestamp.isoformat(),
        }

    def __repr__(self):
        return f"<MoodEntry score={self.mood_score} user={self.user_id}>"


# ══════════════════════════════════════════════════════════════
# MODEL 4 — SentimentLog  (aggregate per day)
# ══════════════════════════════════════════════════════════════
class SentimentLog(db.Model):
    """
    Daily aggregate sentiment scores — used to power the dashboard chart.
    Created/updated automatically after each chat message.
    """
    __tablename__ = "sentiment_logs"

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    date             = db.Column(db.Date, nullable=False)   # One row per day per user
    avg_polarity     = db.Column(db.Float, default=0.0)
    avg_subjectivity = db.Column(db.Float, default=0.0)
    message_count    = db.Column(db.Integer, default=0)
    dominant_emotion = db.Column(db.String(30), nullable=True)

    def to_dict(self):
        return {
            "date":             self.date.isoformat(),
            "avg_polarity":     round(self.avg_polarity, 3),
            "avg_subjectivity": round(self.avg_subjectivity, 3),
            "message_count":    self.message_count,
            "dominant_emotion": self.dominant_emotion,
        }

    def __repr__(self):
        return f"<SentimentLog {self.date} user={self.user_id}>"
