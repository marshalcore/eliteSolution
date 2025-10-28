# alembic/versions/c468bfab220e_add_user_pins_table.py - REPLACE THIS FILE
"""add_user_pins_table

Revision ID: c468bfab220e
Revises: 11ac201aa8fe
Create Date: 2025-10-24 08:10:16.240857

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c468bfab220e'
down_revision: Union[str, Sequence[str], None] = '11ac201aa8fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - SAFELY ADD PIN TABLE ONLY"""
    
    # SAFELY create user_pins table without affecting existing tables
    op.create_table('user_pins',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('pin_hash', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('failed_attempts', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', name='uq_user_pins_user_id')
    )
    
    # Create indexes for better performance
    op.create_index(op.f('ix_user_pins_id'), 'user_pins', ['id'], unique=False)
    op.create_index(op.f('ix_user_pins_user_id'), 'user_pins', ['user_id'], unique=True)
    
    # ✅ PRESERVE ALL EXISTING TABLES AND DATA
    # DO NOT DROP: trading_bots, trades, deposits, etc.
    # DO NOT DROP: users_language_preference index


def downgrade() -> None:
    """Downgrade schema - SAFELY REMOVE ONLY PIN TABLE"""
    
    # Drop indexes first
    op.drop_index(op.f('ix_user_pins_user_id'), table_name='user_pins')
    op.drop_index(op.f('ix_user_pins_id'), table_name='user_pins')
    
    # Drop the user_pins table only
    op.drop_table('user_pins')
    
    # ✅ PRESERVE ALL EXISTING TABLES AND DATA
    # DO NOT RECREATE: trading_bots, trades, deposits, etc.
    # DO NOT RECREATE: users_language_preference index (it stays)