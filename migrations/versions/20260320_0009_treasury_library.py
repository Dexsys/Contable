"""Add treasury documents library

Revision ID: 202603200009
Revises: b9efb8aaeb37
Create Date: 2026-03-20 18:05:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202603200009"
down_revision = "b9efb8aaeb37"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "treasury_documents" not in inspector.get_table_names():
        op.create_table(
            "treasury_documents",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.String(length=1000), nullable=True),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("original_filename", sa.String(length=255), nullable=False),
            sa.Column("file_type", sa.String(length=20), nullable=False),
            sa.Column("file_size_bytes", sa.Integer(), nullable=False),
            sa.Column("uploaded_by_email", sa.String(length=255), nullable=False),
            sa.Column("uploaded_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("treasury_documents")}
    if "ix_treasury_documents_file_type" not in existing_indexes:
        op.create_index("ix_treasury_documents_file_type", "treasury_documents", ["file_type"], unique=False)
    if "ix_treasury_documents_uploaded_at" not in existing_indexes:
        op.create_index("ix_treasury_documents_uploaded_at", "treasury_documents", ["uploaded_at"], unique=False)
    if "ix_treasury_documents_uploaded_by_email" not in existing_indexes:
        op.create_index("ix_treasury_documents_uploaded_by_email", "treasury_documents", ["uploaded_by_email"], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "treasury_documents" in inspector.get_table_names():
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("treasury_documents")}
        if "ix_treasury_documents_uploaded_by_email" in existing_indexes:
            op.drop_index("ix_treasury_documents_uploaded_by_email", table_name="treasury_documents")
        if "ix_treasury_documents_uploaded_at" in existing_indexes:
            op.drop_index("ix_treasury_documents_uploaded_at", table_name="treasury_documents")
        if "ix_treasury_documents_file_type" in existing_indexes:
            op.drop_index("ix_treasury_documents_file_type", table_name="treasury_documents")
        op.drop_table("treasury_documents")
