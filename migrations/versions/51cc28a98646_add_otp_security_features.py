"""add_otp_security_features

Revision ID: 51cc28a98646
Revises: bc7532b99fdb
Create Date: 2025-09-17 14:50:25.180534
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '51cc28a98646'
down_revision: Union[str, Sequence[str], None] = 'bc7532b99fdb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    # --- Add card_holder_name to cards table ---
    result = conn.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name='cards' AND column_name='card_holder_name'")
    ).scalar()

    if not result:
        op.add_column('cards', sa.Column('card_holder_name', sa.String(), nullable=True))
        op.execute(text("UPDATE cards SET card_holder_name = 'Card Holder' WHERE card_holder_name IS NULL"))
        op.alter_column('cards', 'card_holder_name', nullable=False)

    # --- Add is_verified to users table ---
    result = conn.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='is_verified'")
    ).scalar()

    if not result:
        op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=True))
        op.execute(text("UPDATE users SET is_verified = TRUE WHERE is_verified IS NULL"))
        op.alter_column('users', 'is_verified', nullable=False, server_default=sa.text('false'))

    # --- Create enum type otppurpose if missing ---
    op.execute(text("""
        DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'otppurpose') THEN
                CREATE TYPE otppurpose AS ENUM ('registration', 'login', 'transfer', 'withdrawal', 'password_reset');
            END IF;
        END $$;
    """))

    # --- Convert otps.purpose to enum if not already ---
    result = conn.execute(
        text("SELECT data_type FROM information_schema.columns WHERE table_name='otps' AND column_name='purpose'")
    ).scalar()

    if result and result.lower() != 'user-defined':
        op.execute(text("""
            ALTER TABLE otps 
            ALTER COLUMN purpose TYPE otppurpose 
            USING purpose::otppurpose
        """))

    # --- Ensure transactions.extra_data is JSON ---
    result = conn.execute(
        text("SELECT data_type FROM information_schema.columns WHERE table_name='transactions' AND column_name='extra_data'")
    ).scalar()

    if result and result.lower() != 'json':
        op.execute(text("""
            ALTER TABLE transactions 
            ALTER COLUMN extra_data TYPE JSON 
            USING extra_data::json
        """))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()

    # --- Revert transactions.extra_data to VARCHAR ---
    result = conn.execute(
        text("SELECT data_type FROM information_schema.columns WHERE table_name='transactions' AND column_name='extra_data'")
    ).scalar()

    if result and result.lower() == 'json':
        op.execute(text("""
            ALTER TABLE transactions 
            ALTER COLUMN extra_data TYPE VARCHAR 
            USING extra_data::varchar
        """))

    # --- Revert otps.purpose to VARCHAR ---
    result = conn.execute(
        text("SELECT data_type FROM information_schema.columns WHERE table_name='otps' AND column_name='purpose'")
    ).scalar()

    if result and result.lower() == 'user-defined':
        op.execute(text("""
            ALTER TABLE otps 
            ALTER COLUMN purpose TYPE VARCHAR 
            USING purpose::varchar
        """))
        op.execute(text("DROP TYPE IF EXISTS otppurpose"))

    # --- Drop card_holder_name from cards ---
    result = conn.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name='cards' AND column_name='card_holder_name'")
    ).scalar()

    if result:
        op.drop_column('cards', 'card_holder_name')

    # --- Drop is_verified from users ---
    result = conn.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='is_verified'")
    ).scalar()

    if result:
        op.drop_column('users', 'is_verified')
