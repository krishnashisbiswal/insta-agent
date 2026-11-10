"""initial_saas_schema

Revision ID: 2288a3789e0c
Revises: 
Create Date: 2026-11-10 14:53:59.344975

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2288a3789e0c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Audit Logs Table
    op.create_table(
        'audit_logs',
        sa.Column('audit_id', sa.String(length=64), nullable=False),
        sa.Column('org_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.String(length=64), nullable=True),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('resource_type', sa.String(length=64), nullable=False),
        sa.Column('resource_id', sa.String(length=64), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('timestamp', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.org_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('audit_id')
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)

    # 2. Instagram Accounts - Batch Migration
    with op.batch_alter_table('instagram_accounts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('encrypted_refresh_token', sa.Text(), nullable=True, server_default=''))
        batch_op.add_column(sa.Column('token_expires_at', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('scopes_json', sa.Text(), nullable=True, server_default='["instagram_basic","instagram_content_publish"]'))
        batch_op.add_column(sa.Column('reauth_required', sa.Boolean(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('consecutive_publish_errors', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('last_published_at', sa.Float(), nullable=True))

    # 3. Organizations - Batch Migration
    with op.batch_alter_table('organizations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('monthly_post_quota', sa.Integer(), nullable=True, server_default='60'))
        batch_op.add_column(sa.Column('posts_this_month', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('quota_reset_at', sa.Float(), nullable=True, server_default='0.0'))

    # 4. Publishing Jobs - Batch Migration
    with op.batch_alter_table('publishing_jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('error_category', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('history_json', sa.Text(), nullable=True, server_default='[]'))
        batch_op.add_column(sa.Column('claimed_by', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('claimed_at', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('lease_expires_at', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('retry_count', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('max_retries', sa.Integer(), nullable=True, server_default='3'))
        batch_op.add_column(sa.Column('scheduled_at', sa.Float(), nullable=True))
        batch_op.create_index('idx_lease', ['state', 'lease_expires_at'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('publishing_jobs', schema=None) as batch_op:
        batch_op.drop_index('idx_lease')
        batch_op.drop_column('scheduled_at')
        batch_op.drop_column('max_retries')
        batch_op.drop_column('retry_count')
        batch_op.drop_column('lease_expires_at')
        batch_op.drop_column('claimed_at')
        batch_op.drop_column('claimed_by')
        batch_op.drop_column('history_json')
        batch_op.drop_column('error_category')

    with op.batch_alter_table('organizations', schema=None) as batch_op:
        batch_op.drop_column('quota_reset_at')
        batch_op.drop_column('posts_this_month')
        batch_op.drop_column('monthly_post_quota')

    with op.batch_alter_table('instagram_accounts', schema=None) as batch_op:
        batch_op.drop_column('last_published_at')
        batch_op.drop_column('consecutive_publish_errors')
        batch_op.drop_column('reauth_required')
        batch_op.drop_column('scopes_json')
        batch_op.drop_column('token_expires_at')
        batch_op.drop_column('encrypted_refresh_token')

    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_table('audit_logs')
