"""entry receipt image

Revision ID: 202603180004
Revises: 202603180003
Create Date: 2026-03-18 02:15:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202603180004"
down_revision = "202603180003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ledger_entries", sa.Column("receipt_image_path", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_ledger_entries_receipt_image_path"), "ledger_entries", ["receipt_image_path"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_ledger_entries_receipt_image_path"), table_name="ledger_entries")
    op.drop_column("ledger_entries", "receipt_image_path")
