"""add deposits table

Revision ID: 79e081e1324f
Revises: 7e9037f13ef1
Create Date: 2025-09-21 00:19:31.448499
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '79e081e1324f'
down_revision: Union[str, Sequence[str], None] = '7e9037f13ef1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ✅ Enum values for currencies
currency_enum = postgresql.ENUM(
    'USDT', 'BTC', 'ETH', 'USD', 'EUR', 'GBP', 'BNB', 'SOL', 'ADA', 'XRP', 'DOGE',
    name='currencyenum',
    create_type=False
)


def upgrade() -> None:
    """Upgrade schema."""

    # --- ensure enum exists ---
    currency_enum.create(op.get_bind(), checkfirst=True)

    # --- deposits table ---
    op.create_table(
        'deposits',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete="CASCADE"), nullable=False),
        sa.Column('provider', sa.String, nullable=False),  # okx, paystack, flutterwave
        sa.Column('amount', sa.Numeric(18, 8), nullable=False),
        sa.Column('currency', sa.Enum(
            'USDT', 'BTC', 'ETH', 'USD', 'EUR', 'GBP', 'BNB', 'SOL', 'ADA', 'XRP', 'DOGE',
            name='currencyenum'
        ), nullable=False),
        sa.Column('status', sa.String, default="pending"),
        sa.Column('tx_ref', sa.String, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # --- other existing changes from your file ---
    op.alter_column('payments', 'status',
        existing_type=postgresql.ENUM('pending', 'success', 'failed', name='paymentstatus'),
        type_=sa.String(),
        existing_nullable=True
    )
    op.alter_column('users', 'is_admin',
        existing_type=sa.BOOLEAN(),
        nullable=True,
        existing_server_default=sa.text('false')
    )
    op.alter_column('users', 'kyc_verified_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True
    )


def downgrade() -> None:
    """Downgrade schema."""

    # --- drop deposits table ---
    op.drop_table('deposits')

    # --- revert user/payment changes ---
    op.alter_column('users', 'kyc_verified_at',
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True
    )
    op.alter_column('users', 'is_admin',
        existing_type=sa.BOOLEAN(),
        nullable=False,
        existing_server_default=sa.text('false')
    )
    op.alter_column('payments', 'status',
        existing_type=sa.String(),
        type_=postgresql.ENUM('pending', 'success', 'failed', name='paymentstatus'),
        existing_nullable=True
    )

    # --- drop enum safely ---
    currency_enum.drop(op.get_bind(), checkfirst=True)
