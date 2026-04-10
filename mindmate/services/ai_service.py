"""
services/ai_service.py — AI Response Engine

Generates empathetic, ethically-safe AI responses for the chat.

Design principles:
  ✅ Supportive and warm — never cold or clinical
  ✅ Uses validated wellness techniques (CBT prompts, mindfulness)
  ✅ NEVER diagnoses, prescribes, or makes medical claims
  ✅ Always redirects to professionals when appropriate
  ✅ Crisis detection triggers a special safe response

The AI uses a rule-based + pattern-matching system layered on
top of TextBlob sentiment. In a production build, this layer
can be swapped for an LLM (e.g. OpenAI GPT-4) with the same
interface.
"""

import random
from services.sentiment_service import analyse_sentiment, detect_crisis


# ── Response banks by emotional state ─────────────────────────

RESPONSES = {
    "very_positive": [
        "That's wonderful to hear! 🌟 What's been the highlight of your day?",
        "It sounds like things are going really well. I'd love to hear more — what's been contributing to this positive energy?",
        "You're radiating good vibes! Remember to celebrate these moments — they matter. What are you most grateful for today?",
        "That's genuinely great to read. How can we make sure more days feel like this one?",
    ],
    "positive": [
        "I'm glad to hear you're doing okay! Small wins add up. Is there anything on your mind you'd like to talk through?",
        "Sounds like things are manageable — that's a good sign. What's been helping you stay grounded lately?",
        "Good to hear! Even on okay days, checking in with yourself is a great habit. Anything you'd like to reflect on?",
    ],
    "neutral": [
        "I hear you. Sometimes 'okay' is exactly where we need to be. How has your energy been lately — sleep, study, social life?",
        "Thanks for sharing. Even when things feel ordinary, it's worth pausing to notice how you're really feeling underneath. What's been on your mind?",
        "I'm here to listen, no matter what kind of day it's been. Would you like to do a quick emotional check-in together?",
        "Neutral days are valid too. Is there anything quietly weighing on you that you haven't had a chance to express?",
    ],
    "negative": [
        "I'm sorry you're going through a tough time right now. 💙 What's been the hardest part of today for you?",
        "Thank you for trusting me with this. Feeling this way makes sense — life can be really challenging. Can you tell me more about what's happening?",
        "I hear the weight in what you're sharing. You don't have to carry this alone. Let's break it down — what feels most overwhelming right now?",
        "It takes courage to acknowledge when things aren't great. I'm here with you. What's one small thing that might help you feel a bit lighter today?",
    ],
    "very_negative": [
        "I can feel how much pain you're carrying right now, and I want you to know — your feelings are completely valid. 💙 I'm here, and I'm listening. What's happening?",
        "This sounds really, really hard. Thank you for sharing it with me. You deserve support right now — not just from me, but from people in your life too. Is there someone you trust nearby?",
        "I hear you, and I care about how you're feeling. Please don't go through this alone. Would it help to talk through some gentle coping techniques together, or would you like me to share some support resources?",
    ],
    "study_stress": [
        "Exam pressure is one of the hardest parts of student life. Let's try a quick technique: close your eyes, take 3 slow deep breaths, and name one thing you CAN control about your study situation.",
        "Study stress is real and it compounds fast. Have you tried the Pomodoro method? 25 minutes of focused work, 5 min break — it can reduce the overwhelm significantly.",
        "When everything feels urgent, nothing feels manageable. Try writing down your 3 most important tasks for today only. The rest can wait.",
    ],
    "loneliness": [
        "Feeling lonely on campus is more common than you'd think — you're definitely not alone in this, even when it feels that way. What kind of connection are you missing most right now?",
        "Loneliness can be really painful. One small step: is there one person — a classmate, family member, or old friend — you could send a simple message to today?",
    ],
    "default": [
        "I'm here and I'm listening. Tell me more about how you're feeling.",
        "Thank you for sharing that with me. Can you help me understand a little more about what's going on?",
        "You came here, and that already takes some courage. I'm right here with you — what's on your mind?",
        "Every feeling you have is valid. I'm here to support you, not to judge. What would feel most helpful to talk about right now?",
    ],
}

# Wellness techniques to suggest contextually
WELLNESS_TIPS = {
    "breathing":    "🌬️  Try box breathing: inhale 4 counts, hold 4, exhale 4, hold 4. Repeat 3 times.",
    "grounding":    "🌱  5-4-3-2-1 grounding: Name 5 things you see, 4 you can touch, 3 you hear, 2 you smell, 1 you taste.",
    "journalling":  "📓  Writing down your thoughts — even 3 sentences — can significantly reduce mental clutter.",
    "movement":     "🚶  Even a 10-minute walk can shift your mood. Your body and mind are connected.",
    "sleep":        "😴  Consistent sleep is one of the most powerful mental wellness tools. Try a fixed bedtime for 7 days.",
    "connection":   "🤝  Reaching out to one person today — even a brief text — can ease feelings of isolation.",
}

# Keywords that help detect conversation context
CONTEXT_PATTERNS = {
    "study_stress": ["exam", "assignment", "deadline", "marks", "fail", "grade", "study", "test", "result", "submit"],
    "loneliness":   ["lonely", "alone", "no friends", "isolated", "nobody cares", "left out", "excluded"],
    "anxiety":      ["anxious", "anxiety", "panic", "nervous", "scared", "fear", "worried", "overthinking"],
    "sleep":        ["can't sleep", "insomnia", "tired", "exhausted", "sleep", "3am", "awake all night"],
    "motivation":   ["unmotivated", "lazy", "can't start", "procrastinating", "no energy", "pointless"],
}


def generate_ai_response(user_message: str, conversation_history: list = None) -> dict:
    """
    Generate a contextually appropriate, ethically safe AI response.

    Args:
        user_message:         The student's latest message.
        conversation_history: List of prior messages for context (optional).

    Returns:
        dict with: reply, sentiment, crisis_info, wellness_tip, follow_up_question
    """
    if not user_message or not user_message.strip():
        return {
            "reply": "I'm here whenever you're ready to share. Take your time. 💙",
            "sentiment": None,
            "crisis_info": {"crisis_detected": False},
            "wellness_tip": None,
        }

    # Step 1: Check for crisis keywords FIRST — highest priority
    crisis_info = detect_crisis(user_message)
    if crisis_info["crisis_detected"]:
        return {
            "reply":         crisis_info["safe_message"],
            "sentiment":     analyse_sentiment(user_message),
            "crisis_info":   crisis_info,
            "wellness_tip":  WELLNESS_TIPS["breathing"],
            "follow_up":     "Are you in a safe place right now? I'm here with you.",
            "show_resources": True,
        }

    # Step 2: Analyse sentiment
    sentiment = analyse_sentiment(user_message)
    label     = sentiment["label"]

    # Step 3: Detect conversation context (study stress, loneliness, etc.)
    context    = _detect_context(user_message)
    tip_key    = _pick_wellness_tip(context, label)
    wellness_tip = WELLNESS_TIPS.get(tip_key)

    # Step 4: Pick response bank
    if context and context in RESPONSES:
        response_bank = RESPONSES[context]
    elif label in RESPONSES:
        response_bank = RESPONSES[label]
    else:
        response_bank = RESPONSES["default"]

    reply = random.choice(response_bank)

    # Step 5: Optionally append a professional referral nudge for very negative
    if label == "very_negative":
        reply += (
            "\n\n💬 *MindMate is here to support you, but speaking with a campus counsellor "
            "or trusted adult can make a real difference. You deserve that support.*"
        )

    return {
        "reply":        reply,
        "sentiment":    sentiment,
        "crisis_info":  crisis_info,
        "wellness_tip": wellness_tip,
        "follow_up":    _generate_follow_up(label, context),
        "show_resources": label in ("very_negative",),
    }


# ── Private helpers ────────────────────────────────────────────

def _detect_context(text: str) -> str | None:
    """
    Check if the message matches any known emotional context (e.g. study stress).
    Returns the first match, or None.
    """
    text_lower = text.lower()
    for context, keywords in CONTEXT_PATTERNS.items():
        if any(kw in text_lower for kw in keywords):
            return context
    return None


def _pick_wellness_tip(context: str | None, label: str) -> str:
    """Select the most relevant wellness technique key."""
    context_tip_map = {
        "study_stress": "breathing",
        "loneliness":   "connection",
        "anxiety":      "grounding",
        "sleep":        "sleep",
        "motivation":   "movement",
    }
    if context and context in context_tip_map:
        return context_tip_map[context]
    if label in ("negative", "very_negative"):
        return random.choice(["breathing", "grounding", "journalling"])
    return None


def _generate_follow_up(label: str, context: str | None) -> str:
    """Generate a gentle follow-up question to deepen the conversation."""
    if context == "study_stress":
        return "When is your next deadline, and how prepared do you feel right now?"
    if context == "loneliness":
        return "Is there a particular place or situation where you feel most alone?"
    if label == "very_positive":
        return "What's one thing you'd like to carry forward from today?"
    if label in ("negative", "very_negative"):
        return "On a scale of 1–10, how heavy does this feel right now?"
    return "What would feel most helpful to focus on in our chat today?"
