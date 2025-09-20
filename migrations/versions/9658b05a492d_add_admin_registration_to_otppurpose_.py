"""Add ADMIN_REGISTRATION and ADMIN_LOGIN to otppurpose enum

Revision ID: 9658b05a492d
Revises: b1a96df63030
Create Date: 2025-09-19 18:45:36.460537

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9658b05a492d'
down_revision: Union[str, Sequence[str], None] = 'b1a96df63030'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add ADMIN_REGISTRATION and ADMIN_LOGIN to otppurpose enum"""
    op.execute("ALTER TYPE otppurpose ADD VALUE IF NOT EXISTS 'ADMIN_REGISTRATION';")
    op.execute("ALTER TYPE otppurpose ADD VALUE IF NOT EXISTS 'ADMIN_LOGIN';")


def downgrade() -> None:
    """Downgrade schema (not easily supported for enum changes)."""
    # ⚠️ PostgreSQL does not support removing enum values directly.
    # If you need to rollback, you would have to:
    #   1. Create a new enum type without ADMIN_* values
    #   2. Update dependent columns to use that new type
    #   3. Drop the old type
    # Leaving this empty to avoid destructive operations.
    pass
