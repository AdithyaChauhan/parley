"""statuses: 24-hour text and photo statuses, and who viewed them (T39)

Expand only (D31): two new tables. The old code never touches them, so it runs
fine on these tables during a rolling deploy.

Revision ID: d2f6b8a1c3e5
Revises: c7e1a9d4f2b6
Create Date: 2026-11-28 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd2f6b8a1c3e5'
down_revision: Union[str, Sequence[str], None] = 'c7e1a9d4f2b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'statuses',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('body', sa.Text(), server_default='', nullable=False),
        sa.Column('color', sa.Integer(), server_default='0', nullable=False),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("kind IN ('text', 'image')", name='statuses_kind_valid'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('statuses_user_expires', 'statuses', ['user_id', 'expires_at'])
    op.create_table(
        'status_views',
        sa.Column('status_id', sa.Uuid(), nullable=False),
        sa.Column('viewer_id', sa.Uuid(), nullable=False),
        sa.Column('viewed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['status_id'], ['statuses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['viewer_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('status_id', 'viewer_id'),
    )
    op.create_index('status_views_status', 'status_views', ['status_id', sa.text('viewed_at DESC')])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('status_views_status', table_name='status_views')
    op.drop_table('status_views')
    op.drop_index('statuses_user_expires', table_name='statuses')
    op.drop_table('statuses')
