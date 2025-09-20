"""sync OTPPurpose enum with DB

Revision ID: b1a96df63030
Revises: 01d1fd4cde8e
Create Date: 2025-09-17 18:00:17.707690
"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1a96df63030"
down_revision: Union[str, Sequence[str], None] = "01d1fd4cde8e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: sync OTPPurpose enum values with Python Enum."""
    # Ensure all enum values exist in Postgres
    op.execute("ALTER TYPE otppurpose ADD VALUE IF NOT EXISTS 'REGISTRATION'")
    op.execute("ALTER TYPE otppurpose ADD VALUE IF NOT EXISTS 'LOGIN'")
    op.execute("ALTER TYPE otppurpose ADD VALUE IF NOT EXISTS 'TRANSFER'")
    op.execute("ALTER TYPE otppurpose ADD VALUE IF NOT EXISTS 'WITHDRAWAL'")
    op.execute("ALTER TYPE otppurpose ADD VALUE IF NOT EXISTS 'PASSWORD_RESET'")
    op.execute("ALTER TYPE otppurpose ADD VALUE IF NOT EXISTS 'KYC_VERIFICATION'")
    op.execute("ALTER TYPE otppurpose ADD VALUE IF NOT EXISTS 'ADMIN_REGISTRATION'")
    op.execute("ALTER TYPE otppurpose ADD VALUE IF NOT EXISTS 'ADMIN_LOGIN'")


def downgrade() -> None:
    """Downgrade schema: recreate enum without extra values (safe fallback)."""
    # ⚠️ Postgres doesn’t allow direct removal of enum values.
    # Workaround: recreate enum with only the base values and reassign.
    op.execute("ALTER TABLE otps ALTER COLUMN purpose TYPE text")
    op.execute("DROP TYPE otppurpose")

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

    op.execute("ALTER TABLE otps ALTER COLUMN purpose TYPE otppurpose USING purpose::otppurpose")
