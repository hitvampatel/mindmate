"""
routes/chat_routes.py — Chat API Routes

Handles the AI conversation system.

Routes:
  POST /api/chat            → Send a message, get AI response
  GET  /api/chat/history    → Get conversation history
  GET  /api/sentiment-score → Analyse a piece of text
  DELETE /api/chat/history  → Clear chat history
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models     import ChatMessage, User
from services.ai_service        import generate_ai_response
from services.sentiment_service import analyse_sentiment, update_daily_sentiment_log
from config import Config

chat_bp = Blueprint("chat", __name__)


# ══════════════════════════════════════════════════════════════
# POST /api/chat
# ══════════════════════════════════════════════════════════════
@chat_bp.route("/chat", methods=["POST"])
@jwt_required()
def chat():
    """
    Core chat endpoint — the heart of MindMate.

    The student sends a message → we:
      1. Save the user's message to DB
      2. Detect any crisis signals
      3. Analyse sentiment
      4. Generate AI response
      5. Save AI response to DB
      6. Update daily sentiment log
      7. Return everything to the frontend

    Expected JSON body:
      { "message": "I've been feeling really anxious about exams..." }
    """
    user_id = int(get_jwt_identity())
    data    = request.get_json()

    message_text = data.get("message", "").strip()
    if not message_text:
        return jsonify({"success": False, "message": "Message cannot be empty."}), 400

    if len(message_text) > 2000:
        return jsonify({"success": False, "message": "Message too long (max 2000 chars)."}), 400

    # ── Step 1: Retrieve recent conversation history for context ─
    history = (
        ChatMessage.query
        .filter_by(user_id=user_id)
        .order_by(ChatMessage.timestamp.desc())
        .limit(10)
        .all()
    )
    history_dicts = [m.to_dict() for m in reversed(history)]

    # ── Step 2: Generate AI response ────────────────────────────
    ai_result = generate_ai_response(message_text, history_dicts)

    sentiment   = ai_result["sentiment"]
    crisis_info = ai_result["crisis_info"]

    # ── Step 3: Save the student's message to DB ─────────────────
    user_msg = ChatMessage(
        user_id             = user_id,
        role                = "user",
        content             = message_text,
        sentiment_polarity  = sentiment["polarity"]     if sentiment else None,
        sentiment_subjectivity = sentiment["subjectivity"] if sentiment else None,
        sentiment_label     = sentiment["label"]         if sentiment else None,
        crisis_detected     = crisis_info["crisis_detected"],
    )
    db.session.add(user_msg)

    # ── Step 4: Save AI's reply to DB ────────────────────────────
    ai_msg = ChatMessage(
        user_id  = user_id,
        role     = "assistant",
        content  = ai_result["reply"],
    )
    db.session.add(ai_msg)
    db.session.commit()

    # ── Step 5: Update daily sentiment aggregate ─────────────────
    if sentiment:
        update_daily_sentiment_log(
            user_id      = user_id,
            polarity     = sentiment["polarity"],
            subjectivity = sentiment["subjectivity"],
            label        = sentiment["label"],
        )

    # ── Step 6: Build and return response ────────────────────────
    response = {
        "success":      True,
        "user_message": user_msg.to_dict(),
        "ai_response":  {
            **ai_msg.to_dict(),
            "wellness_tip":   ai_result.get("wellness_tip"),
            "follow_up":      ai_result.get("follow_up"),
            "show_resources": ai_result.get("show_resources", False),
        },
        "sentiment":     sentiment,
        "crisis_info":   {
            "crisis_detected": crisis_info["crisis_detected"],
            # Only expose safe_message and resources, NOT triggered_words
            "safe_message":    crisis_info.get("safe_message"),
            "resources":       crisis_info.get("resources") if crisis_info["crisis_detected"] else None,
        },
    }

    # Set HTTP 200 normally, but 200 with a crisis flag so frontend can render it specially
    return jsonify(response), 200


# ══════════════════════════════════════════════════════════════
# GET /api/chat/history
# ══════════════════════════════════════════════════════════════
@chat_bp.route("/chat/history", methods=["GET"])
@jwt_required()
def chat_history():
    """
    Returns the student's conversation history, newest-last.

    Query params:
      page  (int, default 1)
      limit (int, default 20, max 100)
    """
    user_id = int(get_jwt_identity())
    page    = request.args.get("page",  1,  type=int)
    limit   = min(request.args.get("limit", 20, type=int), 100)

    messages = (
        ChatMessage.query
        .filter_by(user_id=user_id)
        .order_by(ChatMessage.timestamp.asc())
        .paginate(page=page, per_page=limit, error_out=False)
    )

    return jsonify({
        "success":      True,
        "messages":     [m.to_dict() for m in messages.items],
        "total":        messages.total,
        "page":         messages.page,
        "pages":        messages.pages,
        "has_next":     messages.has_next,
    }), 200


# ══════════════════════════════════════════════════════════════
# GET /api/sentiment-score
# ══════════════════════════════════════════════════════════════
@chat_bp.route("/sentiment-score", methods=["GET", "POST"])
@jwt_required()
def sentiment_score():
    """
    Analyse the sentiment of any provided text.
    Useful for the frontend to display real-time sentiment as the user types.

    GET  → ?text=I+feel+anxious+today
    POST → { "text": "I feel anxious today" }
    """
    if request.method == "POST":
        data = request.get_json()
        text = data.get("text", "")
    else:
        text = request.args.get("text", "")

    if not text.strip():
        return jsonify({"success": False, "message": "No text provided."}), 400

    result = analyse_sentiment(text)

    return jsonify({
        "success":   True,
        "text":      text[:200],   # echo back first 200 chars only
        "sentiment": result,
    }), 200


# ══════════════════════════════════════════════════════════════
# DELETE /api/chat/history
# ══════════════════════════════════════════════════════════════
@chat_bp.route("/chat/history", methods=["DELETE"])
@jwt_required()
def clear_history():
    """
    Permanently delete all chat messages for the current user.
    Requires confirmation in request body: { "confirm": true }
    """
    user_id = int(get_jwt_identity())
    data    = request.get_json()

    if not data or not data.get("confirm"):
        return jsonify({
            "success": False,
            "message": "Please confirm deletion by sending { \"confirm\": true }"
        }), 400

    deleted = ChatMessage.query.filter_by(user_id=user_id).delete()
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Cleared {deleted} messages from your history.",
    }), 200
