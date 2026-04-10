"""
routes/auth_routes.py — Authentication Routes

Handles user registration, login, logout, and profile.

Routes:
  POST  /api/auth/signup       → Register new student account
  POST  /api/auth/login        → Login and receive JWT token
  POST  /api/auth/logout       → Logout (client-side token removal)
  GET   /api/auth/me           → Get current user profile
  PUT   /api/auth/me           → Update profile
"""

from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)

from extensions import db, bcrypt
from models     import User
from utils.validators import validate_signup, validate_login

auth_bp = Blueprint("auth", __name__)


# ══════════════════════════════════════════════════════════════
# POST /api/auth/signup
# ══════════════════════════════════════════════════════════════
@auth_bp.route("/signup", methods=["POST"])
def signup():
    """
    Register a new student account.

    Expected JSON body:
      { "username": "...", "email": "...", "password": "..." }

    Returns:
      201 + user data + JWT tokens on success.
      400 + error message on validation failure.
    """
    data = request.get_json()

    # Validate input fields
    errors = validate_signup(data)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    username = data["username"].strip().lower()
    email    = data["email"].strip().lower()
    password = data["password"]

    # Check if username or email already exists
    if User.query.filter_by(username=username).first():
        return jsonify({"success": False, "message": "Username already taken."}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email already registered."}), 409

    # Hash the password using bcrypt (never store plain text!)
    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    # Create and save the new user
    new_user = User(
        username      = username,
        email         = email,
        password_hash = password_hash,
    )
    db.session.add(new_user)
    db.session.commit()

    # Generate JWT tokens for immediate login after signup
    access_token  = create_access_token(identity=str(new_user.id))
    refresh_token = create_refresh_token(identity=str(new_user.id))

    return jsonify({
        "success":       True,
        "message":       f"Welcome to MindMate, {new_user.username}! 🎉",
        "user":          new_user.to_dict(),
        "access_token":  access_token,
        "refresh_token": refresh_token,
    }), 201


# ══════════════════════════════════════════════════════════════
# POST /api/auth/login
# ══════════════════════════════════════════════════════════════
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Log in an existing student.

    Expected JSON body:
      { "email": "...", "password": "..." }
      OR
      { "username": "...", "password": "..." }
    """
    data = request.get_json()

    errors = validate_login(data)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    password = data.get("password")

    # Support login by email OR username
    if "email" in data:
        user = User.query.filter_by(email=data["email"].strip().lower()).first()
    else:
        user = User.query.filter_by(username=data["username"].strip().lower()).first()

    # Verify user exists and password is correct
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({
            "success": False,
            "message": "Invalid credentials. Please check your email/username and password."
        }), 401

    if not user.is_active:
        return jsonify({"success": False, "message": "Account is deactivated."}), 403

    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)
    db.session.commit()

    # Issue tokens
    access_token  = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "success":       True,
        "message":       f"Welcome back, {user.username}! 💙",
        "user":          user.to_dict(),
        "access_token":  access_token,
        "refresh_token": refresh_token,
    }), 200


# ══════════════════════════════════════════════════════════════
# POST /api/auth/logout
# ══════════════════════════════════════════════════════════════
@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """
    Log out the current user.

    JWT tokens are stateless — the client deletes the token.
    For production, implement a token blocklist (Redis) here.
    """
    user_id = get_jwt_identity()
    # In production: add token JTI to a Redis blocklist here

    return jsonify({
        "success": True,
        "message": "You've been logged out. Take care! 🌟"
    }), 200


# ══════════════════════════════════════════════════════════════
# GET /api/auth/me
# ══════════════════════════════════════════════════════════════
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_profile():
    """Return the current authenticated user's profile."""
    user_id = int(get_jwt_identity())
    user    = User.query.get_or_404(user_id)

    return jsonify({"success": True, "user": user.to_dict()}), 200


# ══════════════════════════════════════════════════════════════
# PUT /api/auth/me
# ══════════════════════════════════════════════════════════════
@auth_bp.route("/me", methods=["PUT"])
@jwt_required()
def update_profile():
    """Update the current user's username (email changes require verification — future scope)."""
    user_id = int(get_jwt_identity())
    user    = User.query.get_or_404(user_id)
    data    = request.get_json()

    if "username" in data:
        new_username = data["username"].strip().lower()
        existing = User.query.filter_by(username=new_username).first()
        if existing and existing.id != user.id:
            return jsonify({"success": False, "message": "Username already taken."}), 409
        user.username = new_username

    db.session.commit()
    return jsonify({"success": True, "user": user.to_dict()}), 200
