"""
config.py — Application Configuration
All settings in one place. Change values here, not scattered across files.
"""

import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # ── Security ────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "mindmate-dev-secret-change-in-prod-2025")

    # JWT (JSON Web Token) — used for stateless authentication
    JWT_SECRET_KEY       = os.environ.get("JWT_SECRET_KEY", "mindmate-jwt-secret-2025")
    JWT_ACCESS_TOKEN_EXPIRES  = timedelta(hours=8)   # Token valid for 8 hours
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)   # Refresh token valid 30 days

    # ── Database ─────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI     = f"sqlite:///{os.path.join(BASE_DIR, 'mindmate.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False   # Suppress SQLAlchemy warning

    # ── AI / Chat Settings ───────────────────────────────────────
    # Crisis keywords — triggers a gentle escalation response
    CRISIS_KEYWORDS = [
        "suicide", "suicidal", "kill myself", "end my life", "want to die",
        "hurt myself", "self harm", "self-harm", "no reason to live",
        "can't go on", "can't take it anymore", "worthless", "hopeless",
        "cutting myself", "overdose", "not worth living"
    ]

    # Sentiment thresholds for emotional classification
    SENTIMENT_THRESHOLDS = {
        "very_positive":  0.5,
        "positive":       0.1,
        "neutral":        -0.1,
        "negative":       -0.4,
        "very_negative":  -1.0,
    }

    # ── Pagination ───────────────────────────────────────────────
    MESSAGES_PER_PAGE = 20
    MOODS_PER_PAGE    = 30
