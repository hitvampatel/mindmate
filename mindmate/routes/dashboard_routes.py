"""
routes/dashboard_routes.py — Dashboard Data API

Aggregates all student wellness data into a single rich response
for the frontend dashboard.

Routes:
  GET /api/dashboard-data   → Full dashboard payload
  GET /api/dashboard-stats  → Quick stats summary
"""

from datetime import datetime, timezone, timedelta, date

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

from extensions import db
from models     import User, ChatMessage, MoodEntry, SentimentLog

dashboard_bp = Blueprint("dashboard", __name__)


# ══════════════════════════════════════════════════════════════
# GET /api/dashboard-data
# ══════════════════════════════════════════════════════════════
@dashboard_bp.route("/dashboard-data", methods=["GET"])
@jwt_required()
def dashboard_data():
    """
    Returns a comprehensive wellness dashboard payload.

    Sections returned:
      • user_summary         → basic profile stats
      • mood_chart           → last 14 days of mood scores (for line chart)
      • sentiment_chart      → last 14 days of sentiment polarity (for line chart)
      • mood_distribution    → count of each mood label (for pie/bar chart)
      • recent_messages      → last 5 chat messages
      • wellness_score       → composite wellness metric 0–100
      • streak               → consecutive check-in days
      • insights             → AI-generated text insights
    """
    user_id = int(get_jwt_identity())
    user    = User.query.get_or_404(user_id)

    # Date range: last 14 days
    today  = date.today()
    cutoff = today - timedelta(days=13)

    # ── 1. Mood chart data (last 14 days) ────────────────────────
    mood_entries = (
        MoodEntry.query
        .filter(
            MoodEntry.user_id == user_id,
            db.func.date(MoodEntry.timestamp) >= cutoff
        )
        .order_by(MoodEntry.timestamp.asc())
        .all()
    )

    mood_chart = [
        {
            "date":       e.timestamp.strftime("%b %d"),
            "mood_score": e.mood_score,
            "label":      e.mood_label,
        }
        for e in mood_entries
    ]

    # ── 2. Sentiment chart data (last 14 days) ───────────────────
    sentiment_logs = (
        SentimentLog.query
        .filter(
            SentimentLog.user_id == user_id,
            SentimentLog.date    >= cutoff
        )
        .order_by(SentimentLog.date.asc())
        .all()
    )

    sentiment_chart = [log.to_dict() for log in sentiment_logs]

    # ── 3. Mood label distribution ───────────────────────────────
    label_counts = (
        db.session.query(MoodEntry.mood_label, func.count(MoodEntry.id))
        .filter(MoodEntry.user_id == user_id, MoodEntry.mood_label.isnot(None))
        .group_by(MoodEntry.mood_label)
        .all()
    )
    mood_distribution = {label: count for label, count in label_counts}

    # ── 4. Recent chat messages ───────────────────────────────────
    recent_messages = (
        ChatMessage.query
        .filter_by(user_id=user_id)
        .order_by(ChatMessage.timestamp.desc())
        .limit(5)
        .all()
    )

    # ── 5. Composite wellness score (0–100) ──────────────────────
    wellness_score, wellness_breakdown = _calculate_wellness_score(
        user_id, mood_entries, sentiment_logs
    )

    # ── 6. Check-in streak ───────────────────────────────────────
    streak = _calculate_streak(user_id)

    # ── 7. AI text insights ──────────────────────────────────────
    insights = _generate_insights(mood_entries, sentiment_logs, streak)

    # ── 8. Overall stats ─────────────────────────────────────────
    total_messages = ChatMessage.query.filter_by(user_id=user_id).count()
    total_mood_logs = MoodEntry.query.filter_by(user_id=user_id).count()
    crisis_count = (
        ChatMessage.query
        .filter_by(user_id=user_id, crisis_detected=True)
        .count()
    )

    return jsonify({
        "success": True,
        "user_summary": {
            **user.to_dict(),
            "total_chat_messages": total_messages,
            "total_mood_logs":     total_mood_logs,
            "member_since":        user.created_at.strftime("%B %Y"),
        },
        "mood_chart":         mood_chart,
        "sentiment_chart":    sentiment_chart,
        "mood_distribution":  mood_distribution,
        "recent_messages":    [m.to_dict() for m in reversed(recent_messages)],
        "wellness_score":     wellness_score,
        "wellness_breakdown": wellness_breakdown,
        "streak":             streak,
        "insights":           insights,
    }), 200


# ══════════════════════════════════════════════════════════════
# GET /api/dashboard-stats
# ══════════════════════════════════════════════════════════════
@dashboard_bp.route("/dashboard-stats", methods=["GET"])
@jwt_required()
def dashboard_stats():
    """
    Lightweight stats endpoint — for quick KPI cards on the dashboard.
    Returns just the key numbers without chart data.
    """
    user_id = int(get_jwt_identity())
    today   = date.today()
    week_ago = today - timedelta(days=7)

    # Mood this week
    mood_this_week = (
        MoodEntry.query
        .filter(
            MoodEntry.user_id == user_id,
            db.func.date(MoodEntry.timestamp) >= week_ago
        )
        .all()
    )
    avg_mood_week = (
        round(sum(e.mood_score for e in mood_this_week) / len(mood_this_week), 1)
        if mood_this_week else None
    )

    # Sentiment this week
    sentiment_this_week = (
        SentimentLog.query
        .filter(
            SentimentLog.user_id == user_id,
            SentimentLog.date    >= week_ago
        )
        .all()
    )
    avg_sentiment = (
        round(sum(s.avg_polarity for s in sentiment_this_week) / len(sentiment_this_week), 3)
        if sentiment_this_week else None
    )

    return jsonify({
        "success":         True,
        "avg_mood_week":   avg_mood_week,
        "avg_sentiment":   avg_sentiment,
        "mood_logs_week":  len(mood_this_week),
        "streak":          _calculate_streak(user_id),
        "total_messages":  ChatMessage.query.filter_by(user_id=user_id).count(),
    }), 200


# ── Private helpers ────────────────────────────────────────────

def _calculate_wellness_score(user_id, mood_entries, sentiment_logs) -> tuple:
    """
    Compute a composite wellness score (0–100) from:
      • Average mood score (40% weight)
      • Average sentiment polarity (30% weight)
      • Check-in consistency (30% weight)
    """
    breakdown = {
        "mood_component":        0,
        "sentiment_component":   0,
        "consistency_component": 0,
    }

    # Component 1: Mood (40%) — normalise 1–10 to 0–100
    if mood_entries:
        avg_mood = sum(e.mood_score for e in mood_entries) / len(mood_entries)
        breakdown["mood_component"] = round((avg_mood / 10) * 100 * 0.40, 1)

    # Component 2: Sentiment (30%) — normalise -1/+1 to 0–100
    if sentiment_logs:
        avg_pol = sum(s.avg_polarity for s in sentiment_logs) / len(sentiment_logs)
        normalised = (avg_pol + 1) / 2   # convert -1…+1 to 0…1
        breakdown["sentiment_component"] = round(normalised * 100 * 0.30, 1)

    # Component 3: Consistency (30%) — based on check-in streak (max 14 days)
    streak = _calculate_streak(user_id)
    consistency = min(streak / 14, 1.0)
    breakdown["consistency_component"] = round(consistency * 100 * 0.30, 1)

    total = round(sum(breakdown.values()), 1)
    return total, breakdown


def _calculate_streak(user_id: int) -> int:
    """
    Count consecutive days the user has submitted a mood check-in,
    going backwards from today.
    """
    today = date.today()
    streak = 0

    for i in range(60):   # check up to 60 days back
        check_date = today - timedelta(days=i)
        has_entry  = MoodEntry.query.filter(
            MoodEntry.user_id == user_id,
            db.func.date(MoodEntry.timestamp) == check_date
        ).first()

        if has_entry:
            streak += 1
        elif i > 0:   # don't break on today (they might not have logged yet)
            break

    return streak


def _generate_insights(mood_entries, sentiment_logs, streak) -> list:
    """
    Generate 2–4 human-readable insight strings for the dashboard.
    These are pattern-based observations, NOT medical advice.
    """
    insights = []

    if not mood_entries:
        insights.append("🌱 Start your first mood check-in to unlock personalised insights!")
        return insights

    scores = [e.mood_score for e in mood_entries]
    avg    = sum(scores) / len(scores)

    # Mood trend
    if len(scores) >= 4:
        recent  = sum(scores[:len(scores)//2]) / (len(scores)//2)
        earlier = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
        if recent > earlier + 0.5:
            insights.append("📈 Your mood has been trending upward recently — that's a great sign!")
        elif recent < earlier - 0.5:
            insights.append("📉 Your mood appears to have dipped lately. Remember, it's okay to ask for support.")

    # Average mood message
    if avg >= 7:
        insights.append(f"😊 Your average mood this period is {avg:.1f}/10 — you're doing well!")
    elif avg >= 5:
        insights.append(f"💙 Your average mood is {avg:.1f}/10. There's room to grow — small daily habits can help.")
    else:
        insights.append(f"🌱 Your average mood is {avg:.1f}/10. Please consider reaching out to campus wellness support.")

    # Streak insight
    if streak >= 7:
        insights.append(f"🔥 You're on a {streak}-day check-in streak — consistency is a superpower!")
    elif streak >= 3:
        insights.append(f"✅ {streak}-day streak! Keep checking in daily for richer insights.")
    else:
        insights.append("💡 Daily check-ins unlock much more accurate mood trends. Try making it a morning habit!")

    # Sentiment insight
    if sentiment_logs:
        avg_pol = sum(s.avg_polarity for s in sentiment_logs) / len(sentiment_logs)
        if avg_pol > 0.2:
            insights.append("🗣️ Your chat conversations have been leaning emotionally positive lately.")
        elif avg_pol < -0.2:
            insights.append("💬 Your conversations suggest some emotional weight. Talking to someone — even briefly — can help lift it.")

    return insights[:4]   # cap at 4 insights
