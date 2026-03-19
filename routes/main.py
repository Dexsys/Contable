import datetime as dt
import json
import os
import uuid
from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, jsonify, render_template, request, send_from_directory, url_for
from sqlalchemy import func
from werkzeug.utils import secure_filename

from extensions import db
from models import Account, AuditLog, LedgerEntry, TermDeposit, Voucher, VoucherLine
from routes.security import get_current_user, require_permission

main_bp = Blueprint("main", __name__)

ALLOWED_RECEIPT_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
MAIN_APPROVERS = ["kazat@colbun.cl", "lcorales@colbun.cl"]


def write_audit_log(action: str, entity: str | None = None, entity_id: int | None = None, detail: str | None = None):
    """Registra un evento en el log de auditoría."""
    user = get_current_user(required=False, auto_create=False)
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()[:45]
    log = AuditLog(
        user_email=user.email if user else None,
        action=action,
        entity=entity,
        entity_id=entity_id,
        detail=detail,
        ip_address=ip or None,
    )
    db.session.add(log)
    # No hacemos commit aquí; el commit lo realiza la transacción principal.


@main_bp.get("/")
def index():
    return render_template("dashboard.html")


@main_bp.get("/health")
def healthcheck():
    return jsonify({"status": "healthy"}), 200


def parse_date(value):
    if value in (None, ""):
        return None
    if isinstance(value, dt.date):
        return value

    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Fecha inválida: {value}")


def parse_amount(value, field_name="amount"):
    if value in (None, ""):
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        raw = str(value).strip().replace("$", "").replace(" ", "")
        if "," in raw and "." in raw:
            if raw.rfind(",") > raw.rfind("."):
                raw = raw.replace(".", "").replace(",", ".")
            else:
                raw = raw.replace(",", "")
        elif "," in raw:
            raw = raw.replace(".", "").replace(",", ".")
        return Decimal(raw)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Monto inválido para {field_name}") from exc


def allowed_receipt(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_RECEIPT_EXTENSIONS


def save_receipt_file(file_storage):
    if not file_storage or not file_storage.filename:
        return None

    filename = secure_filename(file_storage.filename)
    if not allowed_receipt(filename):
        raise ValueError("Formato de imagen no permitido. Usa png, jpg, jpeg, webp o gif")

    ext = filename.rsplit(".", 1)[1].lower()
    unique_name = f"entry_{dt.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"

    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    full_path = os.path.join(folder, unique_name)
    file_storage.save(full_path)
    return unique_name


def normalize_email(value):
    return (value or "").strip().lower()


def allowed_approvers_for_presenter(presenter_email):
    presenter = normalize_email(presenter_email)
    if presenter in MAIN_APPROVERS:
        return [email for email in MAIN_APPROVERS if email != presenter]
    return list(MAIN_APPROVERS)


def validate_assigned_approver(presenter_email, assigned_approver_email):
    allowed = allowed_approvers_for_presenter(presenter_email)
    assigned = normalize_email(assigned_approver_email)
    if assigned not in allowed:
        raise ValueError("Aprobador no permitido para este presentador")
    return assigned


def next_voucher_number():
    prefix = dt.date.today().strftime("CMP-%Y%m-")
    latest = (
        Voucher.query.filter(Voucher.voucher_number.like(f"{prefix}%"))
        .order_by(Voucher.voucher_number.desc())
        .first()
    )
    if not latest:
        return f"{prefix}0001"
    last = latest.voucher_number.replace(prefix, "")
    try:
        sequence = int(last) + 1
    except ValueError:
        sequence = 1
    return f"{prefix}{sequence:04d}"


def find_account(account_code=None, account_name=None):
    if account_code:
        code = str(account_code).strip().replace(" ", "")
        account = Account.query.filter_by(code=code).one_or_none()
        if account:
            return account
    if account_name:
        return Account.query.filter(func.lower(Account.name) == str(account_name).strip().lower()).one_or_none()
    return None


def build_ledger_entry(payload, movement_type="general", term_deposit_id=None, receipt_image_path=None):
    entry_date = parse_date(payload.get("entry_date") or payload.get("date") or dt.date.today().isoformat())
    bank_effective_date = parse_date(payload.get("bank_effective_date") or entry_date.isoformat())
    description = (payload.get("description") or "").strip()
    if not description:
        raise ValueError("description es requerido")

    kind = (payload.get("kind") or "").strip().lower()
    debit = parse_amount(payload.get("debit"), "debit")
    credit = parse_amount(payload.get("credit"), "credit")
    amount = parse_amount(payload.get("amount"), "amount")

    if amount > 0 and debit == 0 and credit == 0:
        if kind in ("expense", "egreso", "gasto", "term_deposit_open"):
            debit = amount
        elif kind in ("income", "ingreso", "term_deposit_rescue"):
            credit = amount

    if debit == 0 and credit == 0:
        raise ValueError("debit/credit o amount debe ser mayor que cero")

    account = find_account(payload.get("account_code"), payload.get("account_name"))
    raw_code = payload.get("account_code")
    raw_name = payload.get("account_name")

    return LedgerEntry(
        entry_date=entry_date,
        bank_effective_date=bank_effective_date,
        description=description,
        reference=(payload.get("reference") or "").strip() or None,
        debit=debit,
        credit=credit,
        account=account,
        raw_account_code=str(raw_code).strip().replace(" ", "") if raw_code else None,
        raw_account_name=str(raw_name).strip() if raw_name else None,
        note=(payload.get("note") or "").strip() or None,
        movement_type=movement_type,
        term_deposit_id=term_deposit_id,
        receipt_image_path=receipt_image_path,
    )


def parse_voucher_payload():
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        lines = payload.get("lines") or []
    else:
        payload = request.form.to_dict(flat=True)
        lines_raw = request.form.get("lines", "[]")
        try:
            lines = json.loads(lines_raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Formato inválido en lines") from exc

    if not isinstance(lines, list) or len(lines) == 0:
        raise ValueError("Debes enviar al menos una línea de comprobante")

    return payload, lines


def parse_voucher_lines(lines):
    parsed = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")

    for idx, line in enumerate(lines, start=1):
        description = (line.get("description") or "").strip()
        if not description:
            raise ValueError(f"La línea {idx} requiere descripción")

        account_code = (line.get("account_code") or "").strip().replace(" ", "") or None
        account_name = (line.get("account_name") or "").strip() or None
        debit = parse_amount(line.get("debit"), f"linea {idx} debit")
        credit = parse_amount(line.get("credit"), f"linea {idx} credit")

        amount = parse_amount(line.get("amount"), f"linea {idx} amount")
        kind = (line.get("kind") or "").strip().lower()
        if amount > 0 and debit == 0 and credit == 0:
            if kind in ("egreso", "gasto", "expense"):
                debit = amount
            elif kind in ("ingreso", "income"):
                credit = amount

        if debit == 0 and credit == 0:
            raise ValueError(f"La línea {idx} debe tener debit o credit")

        total_debit += debit
        total_credit += credit

        parsed.append(
            {
                "line_number": idx,
                "account_code": account_code,
                "account_name": account_name,
                "description": description,
                "debit": debit,
                "credit": credit,
                "note": (line.get("note") or "").strip() or None,
            }
        )

    if total_debit <= 0 and total_credit <= 0:
        raise ValueError("Comprobante inválido: sin montos")

    return parsed, total_debit, total_credit


def apply_voucher_to_ledger(voucher):
    for line in voucher.lines.order_by(VoucherLine.line_number.asc()).all():
        account = find_account(line.account_code, line.account_name)
        entry = LedgerEntry(
            entry_date=voucher.voucher_date,
            bank_effective_date=voucher.voucher_date,
            description=line.description,
            reference=voucher.voucher_number,
            debit=line.debit,
            credit=line.credit,
            account=account,
            raw_account_code=line.account_code,
            raw_account_name=line.account_name,
            note=line.note or voucher.request_note,
            movement_type="voucher_approved",
            receipt_image_path=voucher.receipt_image_path,
        )
        db.session.add(entry)


def get_period_filters():
    start = parse_date(request.args.get("start_date")) if request.args.get("start_date") else None
    end = parse_date(request.args.get("end_date")) if request.args.get("end_date") else None
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)
    return start, end, month, year


def resolve_period_bounds():
    start, end, month, year = get_period_filters()

    if start:
        period_start = start
    elif year and month:
        period_start = dt.date(year, month, 1)
    elif year:
        period_start = dt.date(year, 1, 1)
    else:
        period_start = None

    if end:
        period_end = end
    elif year and month:
        if month == 12:
            period_end = dt.date(year, 12, 31)
        else:
            period_end = dt.date(year, month + 1, 1) - dt.timedelta(days=1)
    elif year:
        period_end = dt.date(year, 12, 31)
    else:
        period_end = None

    return period_start, period_end


def apply_period_filters(query):
    start, end, month, year = get_period_filters()

    effective_date = func.coalesce(LedgerEntry.bank_effective_date, LedgerEntry.entry_date)

    if year:
        query = query.filter(func.extract("year", effective_date) == year)
    if month:
        query = query.filter(func.extract("month", effective_date) == month)
    if start:
        query = query.filter(effective_date >= start)
    if end:
        query = query.filter(effective_date <= end)

    return query


def build_pending_voucher_summary_items():
    start, end, month, year = get_period_filters()

    query = Voucher.query.filter(Voucher.status == "pending_approval")
    if year:
        query = query.filter(func.extract("year", Voucher.voucher_date) == year)
    if month:
        query = query.filter(func.extract("month", Voucher.voucher_date) == month)
    if start:
        query = query.filter(Voucher.voucher_date >= start)
    if end:
        query = query.filter(Voucher.voucher_date <= end)

    items = []
    for voucher in query.order_by(Voucher.voucher_date.desc(), Voucher.id.desc()).all():
        for line in voucher.lines.order_by(VoucherLine.line_number.asc()).all():
            items.append(
                {
                    "id": f"pending-voucher-{voucher.id}-line-{line.id}",
                    "entry_date": voucher.voucher_date.isoformat(),
                    "bank_effective_date": voucher.voucher_date.isoformat(),
                    "description": line.description,
                    "reference": voucher.voucher_number,
                    "account_code": line.account_code,
                    "account_name": line.account_name,
                    "note": line.note or voucher.request_note,
                    "debit": float(line.debit),
                    "credit": float(line.credit),
                    "movement_type": "voucher_pending",
                    "receipt_image_url": (
                        url_for("main.get_uploaded_file", filename=voucher.receipt_image_path)
                        if voucher.receipt_image_path
                        else None
                    ),
                    "pending": True,
                    "voucher_id": voucher.id,
                    "presenter_email": voucher.presenter_email,
                    "assigned_approver_email": voucher.assigned_approver_email,
                }
            )

    return items


def ensure_tree_node(nodes, code, name):
    if code not in nodes:
        nodes[code] = {
            "code": code,
            "name": name,
            "level": code.count(".") + 1 if code else 0,
            "debit": Decimal("0"),
            "credit": Decimal("0"),
            "balance": Decimal("0"),
            "entry_count": 0,
            "children": [],
            "entries": [],
        }
    return nodes[code]


def account_names_map():
    data = {}
    for acc in Account.query.all():
        data[acc.code] = acc.name
    return data


def summarize_entries(entries, include_entries=False):
    names = account_names_map()
    nodes = {}

    def add_to_node(node, entry):
        node["debit"] += Decimal(entry.debit or 0)
        node["credit"] += Decimal(entry.credit or 0)
        node["balance"] = node["credit"] - node["debit"]
        node["entry_count"] += 1
        if include_entries:
            account_code = entry.account.code if entry.account else entry.raw_account_code
            account_name = entry.account.name if entry.account else entry.raw_account_name
            node["entries"].append(
                {
                    "id": entry.id,
                    "entry_date": entry.entry_date.isoformat(),
                    "bank_effective_date": entry.bank_effective_date.isoformat() if entry.bank_effective_date else None,
                    "description": entry.description,
                    "reference": entry.reference,
                    "account_code": account_code,
                    "account_name": account_name,
                    "note": entry.note,
                    "debit": float(entry.debit),
                    "credit": float(entry.credit),
                    "movement_type": entry.movement_type,
                    "receipt_image_url": (
                        url_for("main.get_uploaded_file", filename=entry.receipt_image_path)
                        if entry.receipt_image_path
                        else None
                    ),
                }
            )

    for entry in entries:
        code = None
        if entry.account and entry.account.code:
            code = entry.account.code
        elif entry.raw_account_code:
            code = entry.raw_account_code
        else:
            code = "sin_cuenta"

        if code == "sin_cuenta":
            node = ensure_tree_node(nodes, code, "Sin cuenta asignada")
            add_to_node(node, entry)
            continue

        parts = code.split(".")
        for idx in range(len(parts)):
            partial = ".".join(parts[: idx + 1])
            fallback_name = names.get(partial) or (entry.raw_account_name if partial == code else f"Nivel {idx + 1}")
            node = ensure_tree_node(nodes, partial, fallback_name)
            add_to_node(node, entry)

    for code, node in nodes.items():
        if code == "sin_cuenta":
            continue
        parent_code = ".".join(code.split(".")[:-1]) if "." in code else None
        if parent_code and parent_code in nodes:
            nodes[parent_code]["children"].append(node)

    roots = [node for code, node in nodes.items() if code == "sin_cuenta" or "." not in code]

    def order_nodes(data):
        data.sort(key=lambda x: x["code"])
        for item in data:
            order_nodes(item["children"])
            item["debit"] = float(item["debit"])
            item["credit"] = float(item["credit"])
            item["balance"] = float(item["balance"])
            if not include_entries:
                item.pop("entries", None)

    order_nodes(roots)
    return roots


@main_bp.post("/api/entries")
@require_permission("create_entries")
def create_entry():
    payload = request.get_json(silent=True) if request.is_json else request.form.to_dict(flat=True)
    payload = payload or {}
    try:
        receipt_image_path = save_receipt_file(request.files.get("receipt_image"))
        entry = build_ledger_entry(payload, receipt_image_path=receipt_image_path)
        db.session.add(entry)
        db.session.flush()
        write_audit_log("entry_created", "ledger_entry", entry.id, entry.description[:200])
        db.session.commit()
        return jsonify(
            {
                "status": "ok",
                "entry_id": entry.id,
                "receipt_image_url": (
                    url_for("main.get_uploaded_file", filename=entry.receipt_image_path)
                    if entry.receipt_image_path
                    else None
                ),
            }
        ), 201
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400


@main_bp.patch("/api/entries/<int:entry_id>")
@require_permission("create_entries")
def update_entry(entry_id):
    payload = request.get_json(silent=True) or request.form.to_dict(flat=True)
    payload = payload or {}

    entry = LedgerEntry.query.filter_by(id=entry_id).one_or_none()
    if not entry:
        return jsonify({"status": "error", "message": "Movimiento no encontrado"}), 404

    try:
        entry_date = parse_date(payload.get("entry_date") or payload.get("date") or entry.entry_date)
        bank_effective_date = parse_date(payload.get("bank_effective_date") or entry.bank_effective_date or entry_date)
        description = (payload.get("description") or entry.description or "").strip()
        if not description:
            raise ValueError("description es requerido")

        debit = parse_amount(payload.get("debit", entry.debit), "debit")
        credit = parse_amount(payload.get("credit", entry.credit), "credit")
        if debit == 0 and credit == 0:
            raise ValueError("debit o credit debe ser mayor que cero")

        account_code = payload.get("account_code")
        account_name = payload.get("account_name")
        if account_code is None:
            account_code = entry.account.code if entry.account else entry.raw_account_code
        if account_name is None:
            account_name = entry.account.name if entry.account else entry.raw_account_name

        account_code = str(account_code).strip().replace(" ", "") if account_code else None
        account_name = str(account_name).strip() if account_name else None
        account = find_account(account_code, account_name)

        entry.entry_date = entry_date
        entry.bank_effective_date = bank_effective_date
        entry.description = description
        entry.reference = (payload.get("reference") or entry.reference or "").strip() or None
        entry.debit = debit
        entry.credit = credit
        entry.account = account
        entry.raw_account_code = account_code
        entry.raw_account_name = account_name
        entry.note = (payload.get("note") or entry.note or "").strip() or None

        write_audit_log("entry_updated", "ledger_entry", entry.id, entry.description[:200])
        db.session.commit()
        return jsonify({"status": "ok", "entry_id": entry.id}), 200
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400


@main_bp.delete("/api/entries/<int:entry_id>")
@require_permission("create_entries")
def delete_entry(entry_id):
    entry = LedgerEntry.query.filter_by(id=entry_id).one_or_none()
    if not entry:
        return jsonify({"status": "error", "message": "Movimiento no encontrado"}), 404

    write_audit_log("entry_deleted", "ledger_entry", entry.id, entry.description[:200])
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"status": "ok", "entry_id": entry_id}), 200


@main_bp.post("/api/term-deposits/open")
@require_permission("manage_term_deposits")
def open_term_deposit():
    payload = request.get_json(silent=True) or {}
    try:
        code = (payload.get("code") or "").strip()
        if not code:
            raise ValueError("code es requerido")

        opened_at = parse_date(payload.get("opened_at") or dt.date.today().isoformat())
        maturity_at = parse_date(payload.get("maturity_at")) if payload.get("maturity_at") else None
        principal = parse_amount(payload.get("principal_amount"), "principal_amount")
        if principal <= 0:
            raise ValueError("principal_amount debe ser mayor que cero")

        deposit = TermDeposit(
            code=code,
            opened_at=opened_at,
            maturity_at=maturity_at,
            principal_amount=principal,
            status="open",
            institution=(payload.get("institution") or "").strip() or None,
            note=(payload.get("note") or "").strip() or None,
        )
        db.session.add(deposit)
        db.session.flush()

        entry_payload = {
            "entry_date": opened_at.isoformat(),
            "bank_effective_date": opened_at.isoformat(),
            "description": payload.get("description") or f"Apertura deposito a plazo {code}",
            "amount": str(principal),
            "kind": "term_deposit_open",
            "account_code": payload.get("account_code") or "3.01.01",
            "account_name": payload.get("account_name") or "Depositos a Plazo",
            "reference": payload.get("reference"),
            "note": payload.get("note"),
        }
        entry = build_ledger_entry(entry_payload, movement_type="term_deposit_open", term_deposit_id=deposit.id)
        db.session.add(entry)
        write_audit_log("term_deposit_opened", "term_deposit", deposit.id, f"Codigo: {deposit.code}")
        db.session.commit()

        return jsonify({"status": "ok", "term_deposit_id": deposit.id, "entry_id": entry.id}), 201
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400


@main_bp.post("/api/term-deposits/<string:code>/rescue")
@require_permission("manage_term_deposits")
def rescue_term_deposit(code):
    payload = request.get_json(silent=True) or {}
    deposit = TermDeposit.query.filter_by(code=code).one_or_none()
    if not deposit:
        return jsonify({"status": "error", "message": "Deposito no encontrado"}), 404

    try:
        rescue_date = parse_date(payload.get("rescued_at") or dt.date.today().isoformat())
        rescue_amount = parse_amount(payload.get("rescue_amount"), "rescue_amount")
        if rescue_amount <= 0:
            raise ValueError("rescue_amount debe ser mayor que cero")

        deposit.rescued_at = rescue_date
        deposit.rescue_amount = rescue_amount
        deposit.status = "rescued"

        entry_payload = {
            "entry_date": rescue_date.isoformat(),
            "bank_effective_date": rescue_date.isoformat(),
            "description": payload.get("description") or f"Rescate deposito a plazo {deposit.code}",
            "amount": str(rescue_amount),
            "kind": "term_deposit_rescue",
            "account_code": payload.get("account_code") or "3.01.03",
            "account_name": payload.get("account_name") or "Rescate Deposito a Plazo",
            "reference": payload.get("reference"),
            "note": payload.get("note"),
        }
        entry = build_ledger_entry(entry_payload, movement_type="term_deposit_rescue", term_deposit_id=deposit.id)
        db.session.add(entry)
        write_audit_log("term_deposit_rescued", "term_deposit", deposit.id, f"Codigo: {deposit.code}")
        db.session.commit()

        return jsonify({"status": "ok", "term_deposit_id": deposit.id, "entry_id": entry.id}), 200
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400


@main_bp.get("/api/term-deposits")
@require_permission("view_reports")
def list_term_deposits():
    status = request.args.get("status")
    query = TermDeposit.query
    if status:
        query = query.filter_by(status=status)
    rows = query.order_by(TermDeposit.opened_at.desc()).all()

    return jsonify(
        {
            "items": [
                {
                    "id": row.id,
                    "code": row.code,
                    "opened_at": row.opened_at.isoformat(),
                    "maturity_at": row.maturity_at.isoformat() if row.maturity_at else None,
                    "rescued_at": row.rescued_at.isoformat() if row.rescued_at else None,
                    "principal_amount": float(row.principal_amount),
                    "rescue_amount": float(row.rescue_amount) if row.rescue_amount is not None else None,
                    "status": row.status,
                    "institution": row.institution,
                    "note": row.note,
                }
                for row in rows
            ]
        }
    )


@main_bp.get("/api/reports/bank-summary")
@require_permission("view_reports")
def bank_summary_report():
    include_entries = request.args.get("include_entries", "0") in ("1", "true", "yes")
    period_start, period_end = resolve_period_bounds()
    effective_date = func.coalesce(LedgerEntry.bank_effective_date, LedgerEntry.entry_date)

    query = LedgerEntry.query.order_by(LedgerEntry.entry_date.asc(), LedgerEntry.id.asc())
    query = apply_period_filters(query)
    entries = query.all()

    total_debit = sum((Decimal(e.debit or 0) for e in entries), Decimal("0"))
    total_credit = sum((Decimal(e.credit or 0) for e in entries), Decimal("0"))
    period_balance = total_credit - total_debit

    previous_balance = Decimal("0")
    if period_start:
        previous_query = LedgerEntry.query.filter(effective_date < period_start)
        previous_entries = previous_query.all()
        previous_debit = sum((Decimal(e.debit or 0) for e in previous_entries), Decimal("0"))
        previous_credit = sum((Decimal(e.credit or 0) for e in previous_entries), Decimal("0"))
        previous_balance = previous_credit - previous_debit

    accumulated_final_balance = previous_balance + period_balance
    pending_items = build_pending_voucher_summary_items() if include_entries else []

    return jsonify(
        {
            "filters": {
                "year": request.args.get("year"),
                "month": request.args.get("month"),
                "start_date": request.args.get("start_date"),
                "end_date": request.args.get("end_date"),
                "period_start": period_start.isoformat() if period_start else None,
                "period_end": period_end.isoformat() if period_end else None,
            },
            "totals": {
                "debit": float(total_debit),
                "credit": float(total_credit),
                "balance": float(period_balance),
                "previous_balance": float(previous_balance),
                "period_balance": float(period_balance),
                "accumulated_final_balance": float(accumulated_final_balance),
                "entries": len(entries),
            },
            "tree": summarize_entries(entries, include_entries=include_entries),
            "pending_items": pending_items,
        }
    )


@main_bp.get("/api/reports/available-periods")
@require_permission("view_reports")
def available_periods_report():
    rows = LedgerEntry.query.order_by(LedgerEntry.entry_date.asc(), LedgerEntry.id.asc()).all()

    years = set()
    months_by_year = {}
    latest_date = None

    for row in rows:
        effective_date = row.bank_effective_date or row.entry_date
        if not effective_date:
            continue

        year = effective_date.year
        month = effective_date.month
        years.add(year)
        months_by_year.setdefault(str(year), set()).add(month)
        if latest_date is None or effective_date > latest_date:
            latest_date = effective_date

    ordered_years = sorted(years)
    return jsonify(
        {
            "years": ordered_years,
            "months_by_year": {
                year: sorted(list(months))
                for year, months in months_by_year.items()
            },
            "latest": {
                "year": latest_date.year if latest_date else None,
                "month": latest_date.month if latest_date else None,
            },
        }
    )


@main_bp.get("/api/accounts")
@require_permission("view_reports")
def list_accounts():
    accounts = Account.query.order_by(Account.code.asc()).all()
    return jsonify(
        {
            "items": [
                {
                    "id": acc.id,
                    "code": acc.code,
                    "name": acc.name,
                    "level": acc.level,
                    "category": acc.category,
                }
                for acc in accounts
            ]
        }
    )


@main_bp.get("/api/entries/recent")
@require_permission("view_reports")
def recent_entries():
    limit = request.args.get("limit", type=int, default=25)
    limit = min(max(limit, 1), 200)

    query = LedgerEntry.query
    query = apply_period_filters(query)
    rows = (
        query.order_by(LedgerEntry.entry_date.desc(), LedgerEntry.id.desc())
        .limit(limit)
        .all()
    )

    return jsonify(
        {
            "items": [
                {
                    "id": row.id,
                    "entry_date": row.entry_date.isoformat(),
                    "description": row.description,
                    "reference": row.reference,
                    "debit": float(row.debit),
                    "credit": float(row.credit),
                    "movement_type": row.movement_type,
                    "account_code": row.account.code if row.account else row.raw_account_code,
                    "account_name": row.account.name if row.account else row.raw_account_name,
                    "receipt_image_url": (
                        url_for("main.get_uploaded_file", filename=row.receipt_image_path)
                        if row.receipt_image_path
                        else None
                    ),
                }
                for row in rows
            ]
        }
    )


@main_bp.get("/uploads/<path:filename>")
@require_permission("view_reports")
def get_uploaded_file(filename):
    safe_name = secure_filename(filename)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], safe_name)


@main_bp.post("/api/vouchers")
@require_permission("create_vouchers")
def create_voucher():
    try:
        current_user = get_current_user(required=True, auto_create=True)
        payload, lines = parse_voucher_payload()

        presenter_email = normalize_email(payload.get("presenter_email"))
        if not presenter_email and current_user:
            presenter_email = current_user.normalized_email()
        if not presenter_email:
            raise ValueError("presenter_email es requerido")

        # Roles no administrativos solo pueden registrar comprobantes propios.
        if not current_user.can("approve_vouchers") and presenter_email != current_user.normalized_email():
            raise ValueError("No puedes registrar comprobantes para otro usuario")

        requested_approver = normalize_email(payload.get("assigned_approver_email"))
        if not requested_approver:
            requested_approver = allowed_approvers_for_presenter(presenter_email)[0]

        assigned_approver = validate_assigned_approver(presenter_email, requested_approver)
        parsed_lines, total_debit, total_credit = parse_voucher_lines(lines)

        voucher_date = parse_date(payload.get("voucher_date") or payload.get("date") or dt.date.today().isoformat())
        voucher_number = payload.get("voucher_number") or next_voucher_number()
        voucher_number = str(voucher_number).strip().upper()

        image_path = save_receipt_file(request.files.get("receipt_image"))

        voucher = Voucher(
            voucher_number=voucher_number,
            voucher_date=voucher_date,
            presenter_name=(payload.get("presenter_name") or "").strip() or None,
            presenter_email=presenter_email,
            assigned_approver_email=assigned_approver,
            status="pending_approval",
            description=(payload.get("description") or "").strip() or None,
            request_note=(payload.get("request_note") or "").strip() or None,
            receipt_image_path=image_path,
        )
        db.session.add(voucher)
        db.session.flush()

        for line in parsed_lines:
            db.session.add(
                VoucherLine(
                    voucher_id=voucher.id,
                    line_number=line["line_number"],
                    account_code=line["account_code"],
                    account_name=line["account_name"],
                    description=line["description"],
                    debit=line["debit"],
                    credit=line["credit"],
                    note=line["note"],
                )
            )

        write_audit_log("voucher_created", "voucher", voucher.id, f"Nro: {voucher.voucher_number} | Presentador: {voucher.presenter_email}")
        db.session.commit()
        return (
            jsonify(
                {
                    "status": "ok",
                    "voucher_id": voucher.id,
                    "voucher_number": voucher.voucher_number,
                    "assigned_approver_email": voucher.assigned_approver_email,
                    "totals": {"debit": float(total_debit), "credit": float(total_credit)},
                }
            ),
            201,
        )
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400


@main_bp.get("/api/vouchers")
@require_permission("view_reports")
def list_vouchers():
    current_user = get_current_user(required=True, auto_create=True)
    status = (request.args.get("status") or "").strip()
    presenter_email = normalize_email(request.args.get("presenter_email"))

    query = Voucher.query
    if status:
        query = query.filter(Voucher.status == status)
    if current_user.can("approve_vouchers"):
        if presenter_email:
            query = query.filter(Voucher.presenter_email == presenter_email)
    else:
        query = query.filter(Voucher.presenter_email == current_user.normalized_email())

    rows = query.order_by(Voucher.created_at.desc()).limit(300).all()
    return jsonify(
        {
            "items": [
                {
                    "id": row.id,
                    "voucher_number": row.voucher_number,
                    "voucher_date": row.voucher_date.isoformat(),
                    "presenter_name": row.presenter_name,
                    "presenter_email": row.presenter_email,
                    "assigned_approver_email": row.assigned_approver_email,
                    "approved_by_email": row.approved_by_email,
                    "rejected_by_email": row.rejected_by_email,
                    "rejection_reason": row.rejection_reason,
                    "status": row.status,
                    "description": row.description,
                    "request_note": row.request_note,
                    "line_count": row.lines.count(),
                    "receipt_image_url": (
                        url_for("main.get_uploaded_file", filename=row.receipt_image_path)
                        if row.receipt_image_path
                        else None
                    ),
                }
                for row in rows
            ]
        }
    )


@main_bp.post("/api/vouchers/<int:voucher_id>/approve")
@require_permission("approve_vouchers")
def approve_voucher(voucher_id):
    payload = request.get_json(silent=True) or request.form.to_dict(flat=True)
    approver_email = normalize_email(payload.get("approver_email"))
    if not approver_email:
        return jsonify({"status": "error", "message": "approver_email es requerido"}), 400

    voucher = Voucher.query.filter_by(id=voucher_id).one_or_none()
    if not voucher:
        return jsonify({"status": "error", "message": "Comprobante no encontrado"}), 404

    if voucher.status != "pending_approval":
        return jsonify({"status": "error", "message": "Comprobante ya procesado"}), 400

    try:
        validate_assigned_approver(voucher.presenter_email, approver_email)

        voucher.status = "approved"
        voucher.approved_by_email = approver_email
        voucher.approved_at = dt.datetime.utcnow()

        apply_voucher_to_ledger(voucher)
        write_audit_log("voucher_approved", "voucher", voucher.id, f"Nro: {voucher.voucher_number} | Aprobador: {approver_email}")
        db.session.commit()

        return jsonify({"status": "ok", "voucher_id": voucher.id, "voucher_number": voucher.voucher_number})
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400


@main_bp.post("/api/vouchers/<int:voucher_id>/reject")
@require_permission("approve_vouchers")
def reject_voucher(voucher_id):
    payload = request.get_json(silent=True) or request.form.to_dict(flat=True)
    rejector_email = normalize_email(payload.get("rejector_email"))
    rejection_reason = (payload.get("rejection_reason") or "").strip()

    if not rejector_email:
        return jsonify({"status": "error", "message": "rejector_email es requerido"}), 400
    if not rejection_reason:
        return jsonify({"status": "error", "message": "rejection_reason es requerido"}), 400

    voucher = Voucher.query.filter_by(id=voucher_id).one_or_none()
    if not voucher:
        return jsonify({"status": "error", "message": "Comprobante no encontrado"}), 404

    if voucher.status != "pending_approval":
        return jsonify({"status": "error", "message": "Comprobante ya procesado"}), 400

    try:
        validate_assigned_approver(voucher.presenter_email, rejector_email)

        voucher.status = "rejected"
        voucher.rejected_by_email = rejector_email
        voucher.rejected_at = dt.datetime.utcnow()
        voucher.rejection_reason = rejection_reason

        write_audit_log(
            "voucher_rejected",
            "voucher",
            voucher.id,
            f"Nro: {voucher.voucher_number} | Rechazador: {rejector_email} | Motivo: {rejection_reason[:200]}",
        )
        db.session.commit()

        return jsonify({"status": "ok", "voucher_id": voucher.id, "voucher_number": voucher.voucher_number})
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
