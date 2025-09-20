"""add admin flows to otppurpose enum

Revision ID: 7e9037f13ef1
Revises: 9658b05a492d
Create Date: 2025-09-19 19:33:42.539691
"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7e9037f13ef1"
down_revision: Union[str, Sequence[str], None] = "9658b05a492d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add missing enum values if they don't already exist
    op.execute("ALTER TYPE otppurpose ADD VALUE IF NOT EXISTS 'ADMIN_REGISTRATION'")
    op.execute("ALTER TYPE otppurpose ADD VALUE IF NOT EXISTS 'ADMIN_LOGIN'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres cannot DROP enum values directly
    # Recreate enum without ADMIN_* values
    op.execute("ALTER TYPE otppurpose RENAME TO otppurpose_old")

    op.execute("""
        CREATE TYPE otppurpose AS ENUM (
            'REGISTRATION',
            'LOGIN',
            'TRANSFER',
            'WITHDRAWAL',
            'PASSWORD_RESET',
            'KYC_VERIFICATION'
        )
    """)

    op.execute("""
        ALTER TABLE otps ALTER COLUMN purpose
        TYPE otppurpose USING purpose::text::otppurpose
    """)

    op.execute("DROP TYPE otppurpose_old")
