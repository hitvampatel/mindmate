"""
routes/mood_routes.py — Mood Tracking API

Handles daily emotional check-ins and mood history.

Routes:
  POST /api/mood-submit      → Submit a mood check-in
  GET  /api/mood-history     → Get mood entries over time
  GET  /api/mood-today       → Get today's mood entry (if any)
  DELETE /api/mood/<id>      → Delete a specific mood entry
"""

from datetime import datetime, timezone, date

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models     import MoodEntry

mood_bp = Blueprint("mood", __name__)

# Valid mood labels accepted from frontend
VALID_MOOD_LABELS = [
    "happy", "calm", "neutral", "anxious", "sad",
    "angry", "stressed", "excited", "grateful", "lonely",
    "overwhelmed", "hopeful", "tired", "motivated", "confused"
]


# ══════════════════════════════════════════════════════════════
# POST /api/mood-submit
# ══════════════════════════════════════════════════════════════
@mood_bp.route("/mood-submit", methods=["POST"])
@jwt_required()
def submit_mood():
    """
    Submit a mood check-in for today.

    Expected JSON body:
    {
        "mood_score": 7,            ← required: integer 1–10
        "mood_label": "anxious",    ← optional: from VALID_MOOD_LABELS
        "note":       "Felt...",    ← optional: free text, max 500 chars
        "energy":     3,            ← optional: integer 1–5
        "sleep_hrs":  6.5           ← optional: float
    }
    """
    user_id = int(get_jwt_identity())
    data    = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "No data provided."}), 400

    # ── Validate mood_score ──────────────────────────────────────
    mood_score = data.get("mood_score")
    if mood_score is None:
        return jsonify({"success": False, "message": "mood_score is required."}), 400

    try:
        mood_score = int(mood_score)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "mood_score must be an integer."}), 400

    if not (1 <= mood_score <= 10):
        return jsonify({"success": False, "message": "mood_score must be between 1 and 10."}), 400

    # ── Validate optional fields ─────────────────────────────────
    mood_label = data.get("mood_label", "").lower().strip() or None
    if mood_label and mood_label not in VALID_MOOD_LABELS:
        return jsonify({
            "success": False,
            "message": f"Invalid mood_label. Choose from: {', '.join(VALID_MOOD_LABELS)}"
        }), 400

    note = data.get("note", "").strip() or None
    if note and len(note) > 500:
        return jsonify({"success": False, "message": "Note must be ≤ 500 characters."}), 400

    energy = data.get("energy")
    if energy is not None:
        try:
            energy = int(energy)
            if not (1 <= energy <= 5):
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "energy must be an integer 1–5."}), 400

    sleep_hrs = data.get("sleep_hrs")
    if sleep_hrs is not None:
        try:
            sleep_hrs = float(sleep_hrs)
            if not (0 <= sleep_hrs <= 24):
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "sleep_hrs must be a number 0–24."}), 400

    # ── Save mood entry ──────────────────────────────────────────
    entry = MoodEntry(
        user_id    = user_id,
        mood_score = mood_score,
        mood_label = mood_label,
        note       = note,
        energy     = energy,
        sleep_hrs  = sleep_hrs,
    )
    db.session.add(entry)
    db.session.commit()

    # ── Build a friendly wellness message ────────────────────────
    message = _mood_response_message(mood_score, mood_label)

    return jsonify({
        "success":  True,
        "message":  message,
        "entry":    entry.to_dict(),
    }), 201


# ══════════════════════════════════════════════════════════════
# GET /api/mood-history
# ══════════════════════════════════════════════════════════════
@mood_bp.route("/mood-history", methods=["GET"])
@jwt_required()
def mood_history():
    """
    Return the student's mood entries, newest first.

    Query params:
      days  (int)  → filter to last N days (default: all)
      limit (int)  → max entries (default 30, max 100)
    """
    user_id = int(get_jwt_identity())
    limit   = min(request.args.get("limit", 30, type=int), 100)
    days    = request.args.get("days", None, type=int)

    query = MoodEntry.query.filter_by(user_id=user_id)

    if days:
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query  = query.filter(MoodEntry.timestamp >= cutoff)

    entries = (
        query
        .order_by(MoodEntry.timestamp.desc())
        .limit(limit)
        .all()
    )

    # ── Compute basic statistics ─────────────────────────────────
    scores = [e.mood_score for e in entries]
    stats  = {}
    if scores:
        stats = {
            "avg_mood":   round(sum(scores) / len(scores), 2),
            "max_mood":   max(scores),
            "min_mood":   min(scores),
            "total_logs": len(scores),
            "trend":      _calculate_trend(scores),
        }

    return jsonify({
        "success": True,
        "entries": [e.to_dict() for e in entries],
        "stats":   stats,
    }), 200


# ══════════════════════════════════════════════════════════════
# GET /api/mood-today
# ══════════════════════════════════════════════════════════════
@mood_bp.route("/mood-today", methods=["GET"])
@jwt_required()
def mood_today():
    """Return today's mood entry for the current user (most recent)."""
    user_id = int(get_jwt_identity())
    today   = date.today()

    entry = (
        MoodEntry.query
        .filter(
            MoodEntry.user_id == user_id,
            db.func.date(MoodEntry.timestamp) == today
        )
        .order_by(MoodEntry.timestamp.desc())
        .first()
    )

    return jsonify({
        "success":       True,
        "checked_in":    entry is not None,
        "entry":         entry.to_dict() if entry else None,
        "date":          today.isoformat(),
    }), 200


# ══════════════════════════════════════════════════════════════
# DELETE /api/mood/<int:entry_id>
# ══════════════════════════════════════════════════════════════
@mood_bp.route("/mood/<int:entry_id>", methods=["DELETE"])
@jwt_required()
def delete_mood(entry_id):
    """Delete a specific mood entry (only the owner can delete their own entries)."""
    user_id = int(get_jwt_identity())
    entry   = MoodEntry.query.get_or_404(entry_id)

    # Security: ensure the user owns this entry
    if entry.user_id != user_id:
        return jsonify({"success": False, "message": "Access denied."}), 403

    db.session.delete(entry)
    db.session.commit()

    return jsonify({"success": True, "message": "Mood entry deleted."}), 200


# ── Private helpers ────────────────────────────────────────────

def _mood_response_message(score: int, label: str | None) -> str:
    """Return a warm, supportive response to the mood submission."""
    if score >= 8:
        return "That's wonderful — you're doing great! Keep riding this positive wave. 🌟"
    elif score >= 6:
        return "Glad to hear things are going reasonably well. Every good day counts! 😊"
    elif score >= 4:
        return "Thanks for checking in. It sounds like a mixed day — that's completely normal. 💙"
    elif score >= 2:
        return "I hear you — tough days are real. You're doing the right thing by acknowledging it. Be gentle with yourself today. 🌱"
    else:
        return "It sounds like a really difficult day. Thank you for sharing that with me. Please don't go through this alone — reach out to someone you trust. 💙"


def _calculate_trend(scores: list) -> str:
    """Simple trend: compare first half avg vs second half avg."""
    if len(scores) < 4:
        return "insufficient_data"
    mid = len(scores) // 2
    # scores are newest-first, so second half is older
    recent_avg = sum(scores[:mid]) / mid
    older_avg  = sum(scores[mid:]) / (len(scores) - mid)
    diff = recent_avg - older_avg
    if diff > 0.5:   return "improving"
    if diff < -0.5:  return "declining"
    return "stable"
