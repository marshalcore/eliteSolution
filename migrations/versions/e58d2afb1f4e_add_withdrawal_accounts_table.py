"""add_withdrawal_accounts_table

Revision ID: e58d2afb1f4e
Revises: c468bfab220e
Create Date: 2025-10-26 06:53:34.383465

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e58d2afb1f4e'
down_revision: Union[str, Sequence[str], None] = 'c468bfab220e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - SAFELY ADD WITHDRAWAL ACCOUNTS TABLE AND PIN_RESET ENUM"""
    
    # ✅ FIXED: Consistent column names with model
    op.create_table('withdrawal_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('account_type', sa.String(length=50), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('account_name', sa.String(length=255), nullable=True),
        sa.Column('account_number', sa.String(length=255), nullable=True),
        sa.Column('bank_code', sa.String(length=50), nullable=True),
        sa.Column('bank_name', sa.String(length=255), nullable=True),
        sa.Column('wallet_address', sa.String(length=255), nullable=True),
        sa.Column('wallet_network', sa.String(length=50), nullable=True),
        sa.Column('cryptocurrency', sa.String(length=50), nullable=True),
        sa.Column('phone_number', sa.String(length=50), nullable=True),
        sa.Column('mobile_network', sa.String(length=50), nullable=True),
        sa.Column('is_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_default', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('account_metadata', sa.JSON(), nullable=True),  # ✅ FIXED: Changed from 'metadata' to 'account_metadata'
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    
    # Create indexes for better performance
    op.create_index(op.f('ix_withdrawal_accounts_id'), 'withdrawal_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_withdrawal_accounts_user_id'), 'withdrawal_accounts', ['user_id'], unique=False)
    op.create_index(op.f('ix_withdrawal_accounts_account_type'), 'withdrawal_accounts', ['account_type'], unique=False)
    op.create_index(op.f('ix_withdrawal_accounts_is_default'), 'withdrawal_accounts', ['is_default'], unique=False)
    
    # ✅ NEW: Add PIN_RESET to OTPPurpose enum
    op.execute("ALTER TYPE otppurpose ADD VALUE IF NOT EXISTS 'pin_reset'")


def downgrade() -> None:
    """Downgrade schema - SAFELY REMOVE ONLY WITHDRAWAL ACCOUNTS TABLE"""
    
    # Drop indexes first
    op.drop_index(op.f('ix_withdrawal_accounts_is_default'), table_name='withdrawal_accounts')
    op.drop_index(op.f('ix_withdrawal_accounts_account_type'), table_name='withdrawal_accounts')
    op.drop_index(op.f('ix_withdrawal_accounts_user_id'), table_name='withdrawal_accounts')
    op.drop_index(op.f('ix_withdrawal_accounts_id'), table_name='withdrawal_accounts')
    
    # Drop the withdrawal_accounts table only
    op.drop_table('withdrawal_accounts')
    
    # ✅ NEW: Remove PIN_RESET from OTPPurpose enum (optional - usually we don't remove enum values in downgrade)
    # Note: Removing enum values can be complex, so this is commented out for safety
    # op.execute("ALTER TYPE otppurpose DROP VALUE 'pin_reset'")