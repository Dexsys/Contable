"""voucher workflow

Revision ID: 202603180005
Revises: 202603180004
Create Date: 2026-03-18 22:30:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202603180005"
down_revision = "202603180004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vouchers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("voucher_number", sa.String(length=40), nullable=False),
        sa.Column("voucher_date", sa.Date(), nullable=False),
        sa.Column("presenter_name", sa.String(length=120), nullable=True),
        sa.Column("presenter_email", sa.String(length=255), nullable=False),
        sa.Column("assigned_approver_email", sa.String(length=255), nullable=False),
        sa.Column("approved_by_email", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("request_note", sa.String(length=500), nullable=True),
        sa.Column("receipt_image_path", sa.String(length=255), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("voucher_number"),
    )
    op.create_index(op.f("ix_vouchers_approved_by_email"), "vouchers", ["approved_by_email"], unique=False)
    op.create_index(op.f("ix_vouchers_assigned_approver_email"), "vouchers", ["assigned_approver_email"], unique=False)
    op.create_index(op.f("ix_vouchers_presenter_email"), "vouchers", ["presenter_email"], unique=False)
    op.create_index(op.f("ix_vouchers_status"), "vouchers", ["status"], unique=False)
    op.create_index(op.f("ix_vouchers_voucher_date"), "vouchers", ["voucher_date"], unique=False)
    op.create_index(op.f("ix_vouchers_voucher_number"), "vouchers", ["voucher_number"], unique=True)

    op.create_table(
        "voucher_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("voucher_id", sa.Integer(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("account_code", sa.String(length=50), nullable=True),
        sa.Column("account_name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("debit", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("credit", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["voucher_id"], ["vouchers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_voucher_lines_account_code"), "voucher_lines", ["account_code"], unique=False)
    op.create_index(op.f("ix_voucher_lines_voucher_id"), "voucher_lines", ["voucher_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_voucher_lines_voucher_id"), table_name="voucher_lines")
    op.drop_index(op.f("ix_voucher_lines_account_code"), table_name="voucher_lines")
    op.drop_table("voucher_lines")

    op.drop_index(op.f("ix_vouchers_voucher_number"), table_name="vouchers")
    op.drop_index(op.f("ix_vouchers_voucher_date"), table_name="vouchers")
    op.drop_index(op.f("ix_vouchers_status"), table_name="vouchers")
    op.drop_index(op.f("ix_vouchers_presenter_email"), table_name="vouchers")
    op.drop_index(op.f("ix_vouchers_assigned_approver_email"), table_name="vouchers")
    op.drop_index(op.f("ix_vouchers_approved_by_email"), table_name="vouchers")
    op.drop_table("vouchers")
