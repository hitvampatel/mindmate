"""
services/sentiment_service.py — Sentiment Analysis Engine

Uses TextBlob to analyse emotional tone in text.

TextBlob returns two scores:
  • polarity     → -1.0 (very negative) to +1.0 (very positive)
  • subjectivity →  0.0 (objective fact) to  1.0 (personal opinion)

We map polarity to a human-readable label and an emoji for the UI.
"""

from textblob import TextBlob
from flask import current_app


def analyse_sentiment(text: str) -> dict:
    """
    Analyse the emotional tone of a piece of text.

    Args:
        text: The student's message or note.

    Returns:
        dict with polarity, subjectivity, label, emoji, and advice.
    """
    if not text or not text.strip():
        return _neutral_result()

    blob = TextBlob(text)
    polarity     = round(blob.sentiment.polarity, 4)
    subjectivity = round(blob.sentiment.subjectivity, 4)

    label, emoji, color = _classify_polarity(polarity)
    advice = _get_wellness_advice(label)

    return {
        "polarity":      polarity,
        "subjectivity":  subjectivity,
        "label":         label,
        "emoji":         emoji,
        "color":         color,
        "advice":        advice,
        "interpretation": _interpret(polarity, subjectivity),
    }


def detect_crisis(text: str) -> dict:
    """
    Scan text for crisis-related keywords.
    Returns a flag and, if triggered, a safe support message.

    IMPORTANT: This is NOT a clinical assessment.
    It is a keyword trigger that surfaces support resources.
    """
    if not text:
        return {"crisis_detected": False}

    text_lower = text.lower()
    crisis_keywords = current_app.config.get("CRISIS_KEYWORDS", [])

    triggered_words = [kw for kw in crisis_keywords if kw in text_lower]

    if triggered_words:
        return {
            "crisis_detected":  True,
            "triggered_words":  triggered_words,  # For internal logging only
            "safe_message":     _get_crisis_support_message(),
            "resources":        _get_crisis_resources(),
        }

    return {"crisis_detected": False}


def update_daily_sentiment_log(user_id: int, polarity: float,
                                subjectivity: float, label: str):
    """
    Update (or create) the daily sentiment aggregate row for a user.
    Called automatically after each chat message is saved.
    """
    from datetime import date, timezone
    from extensions import db
    from models import SentimentLog

    today = date.today()

    log = SentimentLog.query.filter_by(user_id=user_id, date=today).first()

    if log:
        # Rolling average update
        n = log.message_count
        log.avg_polarity     = round((log.avg_polarity * n + polarity) / (n + 1), 4)
        log.avg_subjectivity = round((log.avg_subjectivity * n + subjectivity) / (n + 1), 4)
        log.message_count    += 1
        log.dominant_emotion = label
    else:
        log = SentimentLog(
            user_id          = user_id,
            date             = today,
            avg_polarity     = polarity,
            avg_subjectivity = subjectivity,
            message_count    = 1,
            dominant_emotion = label,
        )
        db.session.add(log)

    db.session.commit()


# ── Private helpers ────────────────────────────────────────────

def _classify_polarity(polarity: float):
    """Map a polarity float to a label, emoji, and hex colour."""
    if   polarity >  0.5:  return "very_positive", "😊", "#22c55e"
    elif polarity >  0.1:  return "positive",       "🙂", "#84cc16"
    elif polarity > -0.1:  return "neutral",        "😐", "#94a3b8"
    elif polarity > -0.4:  return "negative",       "😟", "#f59e0b"
    else:                  return "very_negative",  "😢", "#ef4444"


def _interpret(polarity: float, subjectivity: float) -> str:
    """Generate a human-friendly interpretation sentence."""
    pol_text = (
        "very positive emotional tone"  if polarity >  0.5 else
        "generally positive tone"       if polarity >  0.1 else
        "neutral tone"                  if polarity > -0.1 else
        "some negative feelings"        if polarity > -0.4 else
        "strong negative emotional tone"
    )
    sub_text = (
        "highly personal and subjective"  if subjectivity > 0.7 else
        "moderately personal"             if subjectivity > 0.4 else
        "relatively factual"
    )
    return f"Your message carries a {pol_text} and feels {sub_text}."


def _get_wellness_advice(label: str) -> str:
    """Return a brief, ethical wellness suggestion based on sentiment label."""
    advice_map = {
        "very_positive": "You seem to be in a great space! Keep nurturing those positive moments. 🌟",
        "positive":      "You're doing well. Taking a moment to appreciate the good things can help sustain this energy.",
        "neutral":       "A balanced state can be a good foundation. A short mindfulness pause might help centre you further.",
        "negative":      "It sounds like things feel a bit heavy right now. Remember — it's okay to not be okay. Taking one small step can help.",
        "very_negative": "I can sense this is a really tough moment. Please be gentle with yourself. Reaching out to someone you trust can make a real difference.",
    }
    return advice_map.get(label, "Keep taking care of yourself, one moment at a time.")


def _get_crisis_support_message() -> str:
    return (
        "I'm really glad you felt safe enough to share this with me. "
        "What you're feeling matters deeply. You don't have to face this alone — "
        "please consider reaching out to a trusted person or a helpline right now. "
        "MindMate is here to support you, but a real person can help even more. 💙"
    )


def _get_crisis_resources() -> list:
    return [
        {"name": "iCall (India)",              "contact": "9152987821",    "type": "phone"},
        {"name": "Vandrevala Foundation",       "contact": "1860-2662-345", "type": "phone"},
        {"name": "Crisis Text Line (US/Global)","contact": "Text HOME to 741741", "type": "text"},
        {"name": "AASRA (India)",               "contact": "9820466627",    "type": "phone"},
        {"name": "International Assoc for Suicide Prevention",
         "contact": "https://www.iasp.info/resources/Crisis_Centres/", "type": "web"},
    ]


def _neutral_result() -> dict:
    return {
        "polarity":       0.0,
        "subjectivity":   0.0,
        "label":          "neutral",
        "emoji":          "😐",
        "color":          "#94a3b8",
        "advice":         "Share what's on your mind — I'm here to listen.",
        "interpretation": "No text provided for analysis.",
    }
