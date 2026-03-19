"""voucher rejection fields and audit log table

Revision ID: 202603190008
Revises: 202603190007
Create Date: 2026-03-19 14:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202603190008"
down_revision = "202603190007"
branch_labels = None
depends_on = None


def upgrade():
    # Campos de rechazo en vouchers
    op.add_column("vouchers", sa.Column("rejected_by_email", sa.String(length=255), nullable=True))
    op.add_column("vouchers", sa.Column("rejected_at", sa.DateTime(), nullable=True))
    op.add_column("vouchers", sa.Column("rejection_reason", sa.String(length=500), nullable=True))
    op.create_index("ix_vouchers_rejected_by_email", "vouchers", ["rejected_by_email"])

    # Tabla de auditoría
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("user_email", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("detail", sa.String(length=1000), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])
    op.create_index("ix_audit_logs_user_email", "audit_logs", ["user_email"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity"])


def downgrade():
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_email", table_name="audit_logs")
    op.drop_index("ix_audit_logs_timestamp", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_vouchers_rejected_by_email", table_name="vouchers")
    op.drop_column("vouchers", "rejection_reason")
    op.drop_column("vouchers", "rejected_at")
    op.drop_column("vouchers", "rejected_by_email")
