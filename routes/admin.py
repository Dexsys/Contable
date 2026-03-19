from flask import Blueprint, jsonify, request

from extensions import db
from models import AuditLog, PRIVILEGED_EMAIL_ROLE, ROLE_OPTIONS, User, normalize_email
from routes.security import get_current_user, require_permission

admin_bp = Blueprint("admin", __name__)


def _write_admin_log(action: str, entity: str | None, entity_id: int | None, detail: str | None = None):
    import flask
    user = get_current_user(required=False, auto_create=False)
    ip = flask.request.headers.get("X-Forwarded-For", flask.request.remote_addr or "").split(",")[0].strip()[:45]
    log = AuditLog(
        user_email=user.email if user else None,
        action=action,
        entity=entity,
        entity_id=entity_id,
        detail=detail,
        ip_address=ip or None,
    )
    db.session.add(log)


@admin_bp.get("/ping")
def ping_admin():
    return jsonify({"module": "admin", "status": "ok"}), 200


@admin_bp.get("/users")
@require_permission("manage_users")
def list_users():
    rows = User.query.order_by(User.email.asc()).all()
    return jsonify({"items": [row.to_dict() for row in rows], "roles": list(ROLE_OPTIONS)})


@admin_bp.get("/users/<int:user_id>/audit")
@require_permission("manage_users")
def user_audit(user_id):
    user = User.query.filter_by(id=user_id).one_or_none()
    if not user:
        return jsonify({"status": "error", "message": "Usuario no encontrado"}), 404
    logs = (
        AuditLog.query.filter_by(user_email=user.email)
        .order_by(AuditLog.timestamp.desc())
        .limit(200)
        .all()
    )
    return jsonify({"items": [_log_to_dict(l) for l in logs]})


@admin_bp.get("/audit-logs")
@require_permission("manage_users")
def list_audit_logs():
    action = request.args.get("action", "").strip()
    entity = request.args.get("entity", "").strip()
    user_email = request.args.get("user_email", "").strip().lower()
    limit = min(int(request.args.get("limit", 200)), 1000)

    query = AuditLog.query
    if action:
        query = query.filter(AuditLog.action == action)
    if entity:
        query = query.filter(AuditLog.entity == entity)
    if user_email:
        query = query.filter(AuditLog.user_email == user_email)

    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return jsonify({"items": [_log_to_dict(l) for l in logs]})


def _log_to_dict(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        "user_email": log.user_email,
        "action": log.action,
        "entity": log.entity,
        "entity_id": log.entity_id,
        "detail": log.detail,
        "ip_address": log.ip_address,
    }


@admin_bp.patch("/users/<int:user_id>/role")
@require_permission("manage_users")
def update_user_role(user_id):
    payload = request.get_json(silent=True) or request.form.to_dict(flat=True)
    role = (payload.get("role") or "").strip().lower()
    if role not in ROLE_OPTIONS:
        return jsonify({"status": "error", "message": "Rol inválido"}), 400

    user = User.query.filter_by(id=user_id).one_or_none()
    if not user:
        return jsonify({"status": "error", "message": "Usuario no encontrado"}), 404

    # Los correos privilegiados mantienen su rol elevado por politica.
    if normalize_email(user.email) in PRIVILEGED_EMAIL_ROLE:
        user.role = PRIVILEGED_EMAIL_ROLE[normalize_email(user.email)]
        _write_admin_log("user_role_change_blocked", "user", user.id, f"{user.email} es privilegiado")
        db.session.commit()
        return (
            jsonify(
                {
                    "status": "ok",
                    "message": "Usuario privilegiado: rol administrado por politica",
                    "user": user.to_dict(),
                }
            ),
            200,
        )

    old_role = user.role
    user.role = role
    _write_admin_log("user_role_changed", "user", user.id, f"{user.email}: {old_role} → {role}")
    db.session.commit()
    return jsonify({"status": "ok", "user": user.to_dict()}), 200
