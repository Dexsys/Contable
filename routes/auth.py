from flask import Blueprint, jsonify, request

from extensions import db
from models import AuditLog, ROLE_ADMIN, ROLE_OPTIONS, User, normalize_email
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


@auth_bp.post("/switch-user")
def switch_user():
    current = get_current_user(required=True, auto_create=False)
    if not current:
        return jsonify({"status": "error", "message": "No autenticado"}), 401

    if not current.has_any_role(ROLE_ADMIN):
        return jsonify({"status": "error", "message": "Solo administrador puede cambiar de usuario"}), 403

    payload = request.get_json(silent=True) or request.form.to_dict(flat=True)
    target_email = normalize_email(payload.get("target_email"))
    if not target_email:
        return jsonify({"status": "error", "message": "target_email es requerido"}), 400

    target = User.query.filter_by(email=target_email).one_or_none()
    if not target:
        return jsonify({"status": "error", "message": "Usuario destino no existe"}), 404
    if not target.is_active:
        return jsonify({"status": "error", "message": "Usuario destino inactivo"}), 403

    switched = login_session(target_email)
    _write_auth_log("switch_user", current.email, f"Cambio de sesión a {target_email}")
    return jsonify({"status": "ok", "user": switched.to_dict(), "roles": list(ROLE_OPTIONS)}), 200


@auth_bp.post("/change-password")
def change_password():
    current = get_current_user(required=True, auto_create=False)
    if not current:
        return jsonify({"status": "error", "message": "No autenticado"}), 401

    payload = request.get_json(silent=True) or request.form.to_dict(flat=True)
    current_password = payload.get("current_password") or ""
    new_password = payload.get("new_password") or ""
    confirm_password = payload.get("confirm_password") or ""

    if len(new_password.strip()) < 8:
        return jsonify({"status": "error", "message": "La nueva contraseña debe tener al menos 8 caracteres"}), 400
    if new_password != confirm_password:
        return jsonify({"status": "error", "message": "La confirmación no coincide"}), 400

    if current.password_hash and not current.check_password(current_password):
        return jsonify({"status": "error", "message": "Contraseña actual incorrecta"}), 401

    current.set_password(new_password)
    db.session.commit()
    _write_auth_log("password_changed", current.email)
    return jsonify({"status": "ok", "message": "Contraseña actualizada"}), 200
