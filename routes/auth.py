from flask import Blueprint, jsonify, request

from extensions import db
from models import AuditLog, ROLE_OPTIONS, User, normalize_email
from routes.security import get_current_user, login_session, logout_session

auth_bp = Blueprint("auth", __name__)


def _write_auth_log(action: str, email: str, detail: str | None = None):
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()[:45]
    log = AuditLog(
        user_email=email or None,
        action=action,
        entity="user",
        detail=detail,
        ip_address=ip or None,
    )
    db.session.add(log)
    db.session.commit()


@auth_bp.get("/ping")
def ping_auth():
    return jsonify({"module": "auth", "status": "ok"}), 200


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or request.form.to_dict(flat=True)
    email = normalize_email(payload.get("email"))
    name = (payload.get("name") or "").strip() or None
    password = payload.get("password") or ""

    if not email:
        return jsonify({"status": "error", "message": "email es requerido"}), 400

    # Validar password si el usuario ya existe y tiene uno configurado
    existing = User.query.filter_by(email=email).one_or_none()
    if existing and existing.password_hash and not existing.check_password(password):
        _write_auth_log("login_failed", email, "Credenciales incorrectas")
        return jsonify({"status": "error", "message": "Credenciales incorrectas"}), 401

    user = login_session(email, name=name)
    _write_auth_log("login", user.email)
    return jsonify({"status": "ok", "user": user.to_dict(), "roles": list(ROLE_OPTIONS)}), 200


@auth_bp.post("/logout")
def logout():
    user = get_current_user(required=False, auto_create=False)
    if user:
        _write_auth_log("logout", user.email)
    logout_session()
    return jsonify({"status": "ok"}), 200


@auth_bp.get("/me")
def me():
    user = get_current_user(required=False, auto_create=False)
    return jsonify({"status": "ok", "user": user.to_dict() if user else None, "roles": list(ROLE_OPTIONS)}), 200
