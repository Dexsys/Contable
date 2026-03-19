"""accounts and ledger

Revision ID: 202603180002
Revises: 202603180001
Create Date: 2026-03-18 00:30:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202603180002"
down_revision = "202603180001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("is_postable", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_accounts_category"), "accounts", ["category"], unique=False)
    op.create_index(op.f("ix_accounts_code"), "accounts", ["code"], unique=True)
    op.create_index(op.f("ix_accounts_parent_id"), "accounts", ["parent_id"], unique=False)

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("reference", sa.String(length=120), nullable=True),
        sa.Column("debit", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("credit", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=True),
        sa.Column("raw_account_code", sa.String(length=50), nullable=True),
        sa.Column("raw_account_name", sa.String(length=255), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("source_sheet", sa.String(length=120), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ledger_entries_account_id"), "ledger_entries", ["account_id"], unique=False)
    op.create_index(op.f("ix_ledger_entries_entry_date"), "ledger_entries", ["entry_date"], unique=False)
    op.create_index(op.f("ix_ledger_entries_raw_account_code"), "ledger_entries", ["raw_account_code"], unique=False)
    op.create_index(op.f("ix_ledger_entries_reference"), "ledger_entries", ["reference"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_ledger_entries_reference"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_raw_account_code"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_entry_date"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_account_id"), table_name="ledger_entries")
    op.drop_table("ledger_entries")

    op.drop_index(op.f("ix_accounts_parent_id"), table_name="accounts")
    op.drop_index(op.f("ix_accounts_code"), table_name="accounts")
    op.drop_index(op.f("ix_accounts_category"), table_name="accounts")
    op.drop_table("accounts")
