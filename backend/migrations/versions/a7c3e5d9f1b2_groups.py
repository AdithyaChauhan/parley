"""groups: member roles and stretches, system messages (T35)

Expand only (D31): every new column has a default or may be empty, so the old
code still works on the new tables during a rolling deploy, and existing direct
chats are untouched (they get role "member", from #1, no end, kind "text").
Adding a column with a fixed default doesn't rewrite the table (PostgreSQL 11+).

Revision ID: a7c3e5d9f1b2
Revises: 23d2ac221d8c
Create Date: 2026-11-08 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a7c3e5d9f1b2'
down_revision: Union[str, Sequence[str], None] = '23d2ac221d8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('chat_members', sa.Column('role', sa.String(), server_default='member', nullable=False))
    op.add_column('chat_members', sa.Column('from_seq', sa.Integer(), server_default='1', nullable=False))
    op.add_column('chat_members', sa.Column('until_seq', sa.Integer(), nullable=True))
    op.create_check_constraint('chat_members_role_valid', 'chat_members', "role IN ('admin', 'member')")

    op.add_column('messages', sa.Column('kind', sa.String(), server_default='text', nullable=False))
    op.add_column('messages', sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_check_constraint('messages_kind_valid', 'messages', "kind IN ('text', 'system')")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('messages_kind_valid', 'messages', type_='check')
    op.drop_column('messages', 'data')
    op.drop_column('messages', 'kind')
    op.drop_constraint('chat_members_role_valid', 'chat_members', type_='check')
    op.drop_column('chat_members', 'until_seq')
    op.drop_column('chat_members', 'from_seq')
    op.drop_column('chat_members', 'role')
