"""Add bank statements model

Revision ID: b9efb8aaeb37
Revises: 202603190008
Create Date: 2026-03-20 09:36:53.010942

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = 'b9efb8aaeb37'
down_revision = '202603190008'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'bank_statements' not in inspector.get_table_names():
        op.create_table(
            'bank_statements',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('year', sa.Integer(), nullable=False),
            sa.Column('month', sa.Integer(), nullable=False),
            sa.Column('filename', sa.String(length=255), nullable=False),
            sa.Column('original_filename', sa.String(length=255), nullable=False),
            sa.Column('file_type', sa.String(length=10), nullable=False),
            sa.Column('file_size_bytes', sa.Integer(), nullable=False),
            sa.Column('uploaded_by_email', sa.String(length=255), nullable=False),
            sa.Column('uploaded_at', sa.DateTime(), nullable=False),
            sa.Column('description', sa.String(length=500), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )

    existing_indexes = {idx['name'] for idx in inspector.get_indexes('bank_statements')}
    if op.f('ix_bank_statements_month') not in existing_indexes:
        op.create_index(op.f('ix_bank_statements_month'), 'bank_statements', ['month'], unique=False)
    if op.f('ix_bank_statements_uploaded_at') not in existing_indexes:
        op.create_index(op.f('ix_bank_statements_uploaded_at'), 'bank_statements', ['uploaded_at'], unique=False)
    if op.f('ix_bank_statements_uploaded_by_email') not in existing_indexes:
        op.create_index(op.f('ix_bank_statements_uploaded_by_email'), 'bank_statements', ['uploaded_by_email'], unique=False)
    if op.f('ix_bank_statements_year') not in existing_indexes:
        op.create_index(op.f('ix_bank_statements_year'), 'bank_statements', ['year'], unique=False)

    # Nota: se omiten cambios no relacionados (FK en ledger_entries e índice users.email)
    # para evitar fallos en entornos que ya tienen esos objetos creados.


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'bank_statements' in inspector.get_table_names():
        existing_indexes = {idx['name'] for idx in inspector.get_indexes('bank_statements')}
        if op.f('ix_bank_statements_year') in existing_indexes:
            op.drop_index(op.f('ix_bank_statements_year'), table_name='bank_statements')
        if op.f('ix_bank_statements_uploaded_by_email') in existing_indexes:
            op.drop_index(op.f('ix_bank_statements_uploaded_by_email'), table_name='bank_statements')
        if op.f('ix_bank_statements_uploaded_at') in existing_indexes:
            op.drop_index(op.f('ix_bank_statements_uploaded_at'), table_name='bank_statements')
        if op.f('ix_bank_statements_month') in existing_indexes:
            op.drop_index(op.f('ix_bank_statements_month'), table_name='bank_statements')
        op.drop_table('bank_statements')
