"""files: the uploads table and messages of kind "file" (T36)

Expand only (D31): a new table, a new index and a wider check. The old code
never writes kind "file", so it runs fine on these tables during a rolling deploy.

Revision ID: b4d8f2a6c1e3
Revises: a7c3e5d9f1b2
Create Date: 2026-11-08 18:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4d8f2a6c1e3'
down_revision: Union[str, Sequence[str], None] = 'a7c3e5d9f1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'uploads',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('chat_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('key', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('message_id', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key'),
    )
    op.create_index(
        'uploads_unsent_created', 'uploads', ['created_at'], postgresql_where=sa.text('message_id IS NULL')
    )
    # The file list reads only these, so a long chat stays fast.
    op.create_index(
        'messages_chat_file_seq', 'messages', ['chat_id', 'seq'], postgresql_where=sa.text("kind = 'file'")
    )
    op.drop_constraint('messages_kind_valid', 'messages', type_='check')
    op.create_check_constraint('messages_kind_valid', 'messages', "kind IN ('text', 'system', 'file')")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('messages_kind_valid', 'messages', type_='check')
    op.execute("DELETE FROM messages WHERE kind = 'file'")
    op.create_check_constraint('messages_kind_valid', 'messages', "kind IN ('text', 'system')")
    op.drop_index('messages_chat_file_seq', table_name='messages')
    op.drop_index('uploads_unsent_created', table_name='uploads')
    op.drop_table('uploads')
