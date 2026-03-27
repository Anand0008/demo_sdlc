"""
Authentication blueprint — login, logout, and account management.
Integrates rate limiting (IN-1) and session management (IN-2).
"""
from flask import Blueprint, request, jsonify
from api_design_standards.rate_limiter import (
    record_failed_attempt, is_locked_out,
    remaining_lockout_seconds, reset_attempts,
)
from api_design_standards.session_manager import create_session_token

auth_bp = Blueprint("auth", __name__)

# Placeholder user store (replace with DB in production)
_users = {
    "demo@telomere.com": "hashed_password_here",
}


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").lower().strip()
    password = data.get("password", "")

    if is_locked_out(email):
        remaining = remaining_lockout_seconds(email)
        return jsonify({
            "error": "account_locked",
            "message": f"Account locked. Try again in {remaining // 60} minutes.",
        }), 423  # HTTP 423 Locked

    stored = _users.get(email)
    if stored is None or stored != password:  # TODO: real bcrypt check
        locked = record_failed_attempt(email)
        if locked:
            return jsonify({
                "error": "account_locked",
                "message": "Too many failed attempts. Account locked for 15 minutes.",
            }), 423
        return jsonify({"error": "invalid_credentials"}), 401

    reset_attempts(email)
    token = create_session_token(user_id=email, email=email)
    return jsonify({"token": token}), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    # Token invalidation would be handled by a token blacklist in production
    return jsonify({"message": "Logged out successfully"}), 200
