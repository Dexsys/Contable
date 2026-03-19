"""term deposit and movement metadata

Revision ID: 202603180003
Revises: 202603180002
Create Date: 2026-03-18 01:15:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202603180003"
down_revision = "202603180002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "term_deposits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("opened_at", sa.Date(), nullable=False),
        sa.Column("maturity_at", sa.Date(), nullable=True),
        sa.Column("rescued_at", sa.Date(), nullable=True),
        sa.Column("principal_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("rescue_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("institution", sa.String(length=120), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_term_deposits_code"), "term_deposits", ["code"], unique=True)
    op.create_index(op.f("ix_term_deposits_maturity_at"), "term_deposits", ["maturity_at"], unique=False)
    op.create_index(op.f("ix_term_deposits_opened_at"), "term_deposits", ["opened_at"], unique=False)
    op.create_index(op.f("ix_term_deposits_rescued_at"), "term_deposits", ["rescued_at"], unique=False)
    op.create_index(op.f("ix_term_deposits_status"), "term_deposits", ["status"], unique=False)

    op.add_column("ledger_entries", sa.Column("movement_type", sa.String(length=40), nullable=False, server_default="general"))
    op.add_column("ledger_entries", sa.Column("bank_effective_date", sa.Date(), nullable=True))
    op.add_column("ledger_entries", sa.Column("term_deposit_id", sa.Integer(), nullable=True))

    op.create_index(op.f("ix_ledger_entries_bank_effective_date"), "ledger_entries", ["bank_effective_date"], unique=False)
    op.create_index(op.f("ix_ledger_entries_movement_type"), "ledger_entries", ["movement_type"], unique=False)
    op.create_index(op.f("ix_ledger_entries_term_deposit_id"), "ledger_entries", ["term_deposit_id"], unique=False)
    op.create_foreign_key(None, "ledger_entries", "term_deposits", ["term_deposit_id"], ["id"])


def downgrade():
    op.drop_constraint(None, "ledger_entries", type_="foreignkey")
    op.drop_index(op.f("ix_ledger_entries_term_deposit_id"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_movement_type"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_bank_effective_date"), table_name="ledger_entries")
    op.drop_column("ledger_entries", "term_deposit_id")
    op.drop_column("ledger_entries", "bank_effective_date")
    op.drop_column("ledger_entries", "movement_type")

    op.drop_index(op.f("ix_term_deposits_status"), table_name="term_deposits")
    op.drop_index(op.f("ix_term_deposits_rescued_at"), table_name="term_deposits")
    op.drop_index(op.f("ix_term_deposits_opened_at"), table_name="term_deposits")
    op.drop_index(op.f("ix_term_deposits_maturity_at"), table_name="term_deposits")
    op.drop_index(op.f("ix_term_deposits_code"), table_name="term_deposits")
    op.drop_table("term_deposits")
