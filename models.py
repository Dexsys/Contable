from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db

ROLE_ADMIN = "admin"
ROLE_TESORERO = "tesorero"
ROLE_USUARIO = "usuario"
ROLE_VISITA = "visita"

ROLE_OPTIONS = (ROLE_ADMIN, ROLE_TESORERO, ROLE_USUARIO, ROLE_VISITA)

PRIVILEGED_EMAIL_ROLE = {
    "lcorales@colbun.cl": ROLE_TESORERO,
    "dexsys@gmail.com": ROLE_ADMIN,
}


def normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_VISITA, index=True)
    password_hash = db.Column(db.String(256), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def normalized_email(self) -> str:
        return normalize_email(self.email)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return True  # sin password configurado: acceso libre (compatibilidad hacia atras)
        return check_password_hash(self.password_hash, password)

    def effective_role(self) -> str:
        forced_role = PRIVILEGED_EMAIL_ROLE.get(self.normalized_email())
        if forced_role:
            return forced_role
        return self.role or ROLE_VISITA

    def has_any_role(self, *roles: str) -> bool:
        return self.effective_role() in roles

    def can(self, permission: str) -> bool:
        role = self.effective_role()
        role_permissions = {
            ROLE_ADMIN: {
                "view_reports",
                "create_entries",
                "manage_term_deposits",
                "create_vouchers",
                "approve_vouchers",
                "manage_users",
            },
            ROLE_TESORERO: {
                "view_reports",
                "create_entries",
                "manage_term_deposits",
                "create_vouchers",
                "approve_vouchers",
                "manage_users",
            },
            ROLE_USUARIO: {
                "view_reports",
                "create_entries",
                "create_vouchers",
            },
            ROLE_VISITA: {
                "view_reports",
            },
        }
        return permission in role_permissions.get(role, set())

    def to_dict(self) -> dict:
        role = self.effective_role()
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "effective_role": role,
            "is_active": self.is_active,
            "has_password": self.password_hash is not None,
            "permissions": {
                "view_reports": self.can("view_reports"),
                "create_entries": self.can("create_entries"),
                "manage_term_deposits": self.can("manage_term_deposits"),
                "create_vouchers": self.can("create_vouchers"),
                "approve_vouchers": self.can("approve_vouchers"),
                "manage_users": self.can("manage_users"),
            },
        }

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=True, index=True)
    level = db.Column(db.Integer, nullable=False, default=1)
    parent_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=True, index=True)
    is_postable = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    parent = db.relationship("Account", remote_side=[id], backref=db.backref("children", lazy="dynamic"))

    def __repr__(self) -> str:
        return f"<Account {self.code} {self.name}>"


class LedgerEntry(db.Model):
    __tablename__ = "ledger_entries"

    id = db.Column(db.Integer, primary_key=True)
    entry_date = db.Column(db.Date, nullable=False, index=True)
    description = db.Column(db.String(500), nullable=False)
    reference = db.Column(db.String(120), nullable=True, index=True)
    debit = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    credit = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=True, index=True)
    raw_account_code = db.Column(db.String(50), nullable=True, index=True)
    raw_account_name = db.Column(db.String(255), nullable=True)
    note = db.Column(db.String(500), nullable=True)
    source_sheet = db.Column(db.String(120), nullable=True)
    source_row = db.Column(db.Integer, nullable=True)
    movement_type = db.Column(db.String(40), nullable=False, default="general", index=True)
    bank_effective_date = db.Column(db.Date, nullable=True, index=True)
    term_deposit_id = db.Column(db.Integer, db.ForeignKey("term_deposits.id"), nullable=True, index=True)
    receipt_image_path = db.Column(db.String(255), nullable=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    account = db.relationship("Account", backref=db.backref("entries", lazy="dynamic"))

    def __repr__(self) -> str:
        return f"<LedgerEntry {self.entry_date} {self.description[:30]}>"


class TermDeposit(db.Model):
    __tablename__ = "term_deposits"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(60), unique=True, nullable=False, index=True)
    opened_at = db.Column(db.Date, nullable=False, index=True)
    maturity_at = db.Column(db.Date, nullable=True, index=True)
    rescued_at = db.Column(db.Date, nullable=True, index=True)
    principal_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    rescue_amount = db.Column(db.Numeric(14, 2), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="open", index=True)
    institution = db.Column(db.String(120), nullable=True)
    note = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    entries = db.relationship("LedgerEntry", backref="term_deposit", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<TermDeposit {self.code} {self.status}>"


class Voucher(db.Model):
    __tablename__ = "vouchers"

    id = db.Column(db.Integer, primary_key=True)
    voucher_number = db.Column(db.String(40), unique=True, nullable=False, index=True)
    voucher_date = db.Column(db.Date, nullable=False, index=True)
    presenter_name = db.Column(db.String(120), nullable=True)
    presenter_email = db.Column(db.String(255), nullable=False, index=True)
    assigned_approver_email = db.Column(db.String(255), nullable=False, index=True)
    approved_by_email = db.Column(db.String(255), nullable=True, index=True)
    status = db.Column(db.String(30), nullable=False, default="pending_approval", index=True)
    description = db.Column(db.String(500), nullable=True)
    request_note = db.Column(db.String(500), nullable=True)
    receipt_image_path = db.Column(db.String(255), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejected_by_email = db.Column(db.String(255), nullable=True, index=True)
    rejected_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    lines = db.relationship(
        "VoucherLine",
        backref="voucher",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Voucher {self.voucher_number} {self.status}>"


class AuditLog(db.Model):
    """Registro de auditoría del sistema."""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    user_email = db.Column(db.String(255), nullable=True, index=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    entity = db.Column(db.String(80), nullable=True, index=True)
    entity_id = db.Column(db.Integer, nullable=True)
    detail = db.Column(db.String(1000), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)

    def __repr__(self) -> str:
        return f"<AuditLog {self.timestamp} {self.action} {self.user_email}>"


class VoucherLine(db.Model):
    __tablename__ = "voucher_lines"

    id = db.Column(db.Integer, primary_key=True)
    voucher_id = db.Column(db.Integer, db.ForeignKey("vouchers.id"), nullable=False, index=True)
    line_number = db.Column(db.Integer, nullable=False)
    account_code = db.Column(db.String(50), nullable=True, index=True)
    account_name = db.Column(db.String(255), nullable=True)
    description = db.Column(db.String(500), nullable=False)
    debit = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    credit = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    note = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<VoucherLine {self.voucher_id}#{self.line_number}>"


class BankStatement(db.Model):
    """Cartolas bancarias mensuales (PDF/Excel)."""

    __tablename__ = "bank_statements"

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    month = db.Column(db.Integer, nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)  # 'pdf' o 'xlsx'
    file_size_bytes = db.Column(db.Integer, nullable=False)
    uploaded_by_email = db.Column(db.String(255), nullable=False, index=True)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    description = db.Column(db.String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<BankStatement {self.year}-{self.month:02d} ({self.file_type})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "year": self.year,
            "month": self.month,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_type": self.file_type,
            "file_size_bytes": self.file_size_bytes,
            "uploaded_by_email": self.uploaded_by_email,
            "uploaded_at": self.uploaded_at.isoformat(),
            "description": self.description,
        }
