"""add admin fields to User and extend OTPPurpose enum

Revision ID: 01d1fd4cde8e
Revises: 51cc28a98646
Create Date: 2025-09-17 17:01:53.117835
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '01d1fd4cde8e'
down_revision: Union[str, Sequence[str], None] = '51cc28a98646'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enum definitions
old_otp_purpose = postgresql.ENUM(
    "registration", "login", "transfer", "withdrawal", "password_reset",
    name="otppurpose"
)
new_otp_purpose = postgresql.ENUM(
    "registration", "login", "transfer", "withdrawal", "password_reset",
    "admin_registration", "admin_login", "admin_action",
    name="otppurpose"
)


def upgrade() -> None:
    """Upgrade schema."""

    # --- users table changes ---
    op.add_column(
        'users',
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column('users', sa.Column('kyc_status', sa.String(), nullable=True))
    op.add_column('users', sa.Column('kyc_verified_at', sa.DateTime(timezone=True), nullable=True))

    # --- OTP enum changes ---
    # Rename old enum
    op.execute("ALTER TYPE otppurpose RENAME TO otppurpose_old;")
    # Create new enum
    new_otp_purpose.create(op.get_bind(), checkfirst=False)
    # Alter column to use new enum
    op.execute(
        "ALTER TABLE otps ALTER COLUMN purpose TYPE otppurpose USING purpose::text::otppurpose;"
    )
    # Drop old enum
    op.execute("DROP TYPE otppurpose_old;")


def downgrade() -> None:
    """Downgrade schema."""

    # --- users table revert ---
    op.drop_column('users', 'kyc_verified_at')
    op.drop_column('users', 'kyc_status')
    op.drop_column('users', 'is_admin')

    # --- OTP enum rollback ---
    old_otp_purpose.create(op.get_bind(), checkfirst=False)
    op.execute(
        "ALTER TABLE otps ALTER COLUMN purpose TYPE otppurpose USING purpose::text::otppurpose;"
    )
    new_otp_purpose.drop(op.get_bind(), checkfirst=False)
