from __future__ import annotations

from functools import wraps

from flask import g, jsonify, request, session

from extensions import db
from models import PRIVILEGED_EMAIL_ROLE, ROLE_VISITA, User, normalize_email


AUTH_EMAIL_HEADER = "X-User-Email"


def _default_name(email: str) -> str:
    local = email.split("@", 1)[0]
    return local.replace(".", " ").replace("_", " ").strip().title() or "Usuario"


def get_request_email() -> str:
    email = normalize_email(session.get("user_email"))
    if email:
        return email

    email = normalize_email(request.headers.get(AUTH_EMAIL_HEADER))
    if email:
        return email

    email = normalize_email(request.args.get("user_email"))
    if email:
        return email

    payload = request.get_json(silent=True) if request.is_json else request.form
    if payload:
        return normalize_email(payload.get("user_email"))

    return ""


def ensure_user(email: str, name: str | None = None, auto_create: bool = True) -> User | None:
    normalized = normalize_email(email)
    if not normalized:
        return None

    user = User.query.filter_by(email=normalized).one_or_none()
    if user:
        if not user.role:
            user.role = PRIVILEGED_EMAIL_ROLE.get(normalized, ROLE_VISITA)
            db.session.commit()
        return user

    if not auto_create:
        return None

    user = User(
        email=normalized,
        name=(name or _default_name(normalized)).strip() or _default_name(normalized),
        role=PRIVILEGED_EMAIL_ROLE.get(normalized, ROLE_VISITA),
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    return user


def get_current_user(required: bool = True, auto_create: bool = True) -> User | None:
    if hasattr(g, "current_user"):
        return g.current_user

    email = get_request_email()
    user = ensure_user(email, auto_create=auto_create) if email else None

    g.current_user = user
    if required and not user:
        return None
    return user


def require_permission(permission: str):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            user = get_current_user(required=True, auto_create=True)
            if not user:
                return jsonify({"status": "error", "message": "No autenticado"}), 401
            if not user.is_active:
                return jsonify({"status": "error", "message": "Usuario inactivo"}), 403
            if not user.can(permission):
                return jsonify({"status": "error", "message": "No autorizado"}), 403
            return view_func(*args, **kwargs)

        return wrapper

    return decorator


def login_session(email: str, name: str | None = None) -> User:
    user = ensure_user(email, name=name, auto_create=True)
    session["user_email"] = user.email
    return user


def logout_session() -> None:
    session.pop("user_email", None)
