"""Add sales and purchase_sale_assignments tables

Revision ID: 001
Created: 2025-12-31

This migration adds support for tracking stock sales with FIFO cost basis assignment.
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# Revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Apply the migration."""

    # Create sales table
    op.create_table(
        'sales',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(length=10), nullable=False),
        sa.Column('sale_date', sa.Date(), nullable=False),
        sa.Column('shares_sold', sa.Float(), nullable=False),
        sa.Column('price_at_sale', sa.Float(), nullable=False),
        sa.Column('total_proceeds', sa.Float(), nullable=False),
        sa.Column('reinvestment_purchase_id', sa.Integer(), nullable=True),
        sa.Column('reinvested_amount', sa.Float(), nullable=True),
        sa.Column('cash_retained', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['reinvestment_purchase_id'], ['purchases.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes on sales table
    op.create_index('ix_sales_user_id', 'sales', ['user_id'])
    op.create_index('ix_sales_ticker', 'sales', ['ticker'])
    op.create_index('ix_sales_sale_date', 'sales', ['sale_date'])
    op.create_index('ix_sales_user_ticker', 'sales', ['user_id', 'ticker'])

    # Create purchase_sale_assignments table
    op.create_table(
        'purchase_sale_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('purchase_id', sa.Integer(), nullable=False),
        sa.Column('sale_id', sa.Integer(), nullable=False),
        sa.Column('shares_assigned', sa.Float(), nullable=False),
        sa.Column('cost_basis', sa.Float(), nullable=False),
        sa.Column('proceeds', sa.Float(), nullable=False),
        sa.Column('realized_gain_loss', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['purchase_id'], ['purchases.id'], ),
        sa.ForeignKeyConstraint(['sale_id'], ['sales.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes on purchase_sale_assignments table
    op.create_index('ix_psa_purchase_id', 'purchase_sale_assignments', ['purchase_id'])
    op.create_index('ix_psa_sale_id', 'purchase_sale_assignments', ['sale_id'])


def downgrade():
    """Revert the migration."""

    # Drop indexes first
    op.drop_index('ix_psa_sale_id', table_name='purchase_sale_assignments')
    op.drop_index('ix_psa_purchase_id', table_name='purchase_sale_assignments')
    op.drop_index('ix_sales_user_ticker', table_name='sales')
    op.drop_index('ix_sales_sale_date', table_name='sales')
    op.drop_index('ix_sales_ticker', table_name='sales')
    op.drop_index('ix_sales_user_id', table_name='sales')

    # Drop tables
    op.drop_table('purchase_sale_assignments')
    op.drop_table('sales')
