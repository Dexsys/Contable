"""Add ledger entry multiple attachments

Revision ID: 202603200010
Revises: 202603200009
Create Date: 2026-03-20 19:05:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202603200010"
down_revision = "202603200009"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "ledger_entry_attachments" not in inspector.get_table_names():
        op.create_table(
            "ledger_entry_attachments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("entry_id", sa.Integer(), nullable=False),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("original_filename", sa.String(length=255), nullable=False),
            sa.Column("file_type", sa.String(length=20), nullable=False),
            sa.Column("file_size_bytes", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["entry_id"], ["ledger_entries.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("ledger_entry_attachments")}
    if "ix_ledger_entry_attachments_entry_id" not in existing_indexes:
        op.create_index("ix_ledger_entry_attachments_entry_id", "ledger_entry_attachments", ["entry_id"], unique=False)
    if "ix_ledger_entry_attachments_file_type" not in existing_indexes:
        op.create_index("ix_ledger_entry_attachments_file_type", "ledger_entry_attachments", ["file_type"], unique=False)
    if "ix_ledger_entry_attachments_created_at" not in existing_indexes:
        op.create_index("ix_ledger_entry_attachments_created_at", "ledger_entry_attachments", ["created_at"], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "ledger_entry_attachments" in inspector.get_table_names():
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("ledger_entry_attachments")}
        if "ix_ledger_entry_attachments_created_at" in existing_indexes:
            op.drop_index("ix_ledger_entry_attachments_created_at", table_name="ledger_entry_attachments")
        if "ix_ledger_entry_attachments_file_type" in existing_indexes:
            op.drop_index("ix_ledger_entry_attachments_file_type", table_name="ledger_entry_attachments")
        if "ix_ledger_entry_attachments_entry_id" in existing_indexes:
            op.drop_index("ix_ledger_entry_attachments_entry_id", table_name="ledger_entry_attachments")
        op.drop_table("ledger_entry_attachments")
