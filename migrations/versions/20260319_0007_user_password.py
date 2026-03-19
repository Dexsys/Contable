"""user password hash

Revision ID: 202603190007
Revises: 202603190006
Create Date: 2026-03-19 12:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202603190007"
down_revision = "202603190006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("password_hash", sa.String(length=256), nullable=True))


def downgrade():
    op.drop_column("users", "password_hash")
