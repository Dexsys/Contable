"""user roles

Revision ID: 202603190006
Revises: 202603180005
Create Date: 2026-03-19 09:30:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202603190006"
down_revision = "202603180005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("role", sa.String(length=20), nullable=False, server_default="visita"))
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)

    op.execute("UPDATE users SET role='tesorero' WHERE lower(email)='lcorales@colbun.cl'")
    op.execute("UPDATE users SET role='admin' WHERE lower(email)='dexsys@gmail.com'")



def downgrade():
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_column("users", "role")
