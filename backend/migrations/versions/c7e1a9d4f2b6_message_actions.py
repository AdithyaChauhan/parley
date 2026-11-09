"""message actions: reactions, edit and delete (T37)

Expand only (D31): new columns, a new table and a wider check. The old code
never writes the new kinds, so it runs fine on these tables during a rolling deploy.

Revision ID: c7e1a9d4f2b6
Revises: b4d8f2a6c1e3
Create Date: 2026-11-09 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e1a9d4f2b6'
down_revision: Union[str, Sequence[str], None] = 'b4d8f2a6c1e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('messages', sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('messages', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('messages', sa.Column('state_seq', sa.Integer(), server_default='0', nullable=False))
    op.create_table(
        'message_reactions',
        sa.Column('message_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('emoji', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('message_id', 'user_id'),
    )
    # A deleted file's upload stays until the store has really dropped it.
    op.add_column('uploads', sa.Column('erase_pending', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.drop_constraint('messages_kind_valid', 'messages', type_='check')
    op.create_check_constraint(
        'messages_kind_valid', 'messages', "kind IN ('text', 'system', 'file', 'reaction', 'edit', 'delete')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('messages_kind_valid', 'messages', type_='check')
    op.execute("DELETE FROM messages WHERE kind IN ('reaction', 'edit', 'delete')")
    op.create_check_constraint('messages_kind_valid', 'messages', "kind IN ('text', 'system', 'file')")
    op.drop_column('uploads', 'erase_pending')
    op.drop_table('message_reactions')
    op.drop_column('messages', 'state_seq')
    op.drop_column('messages', 'deleted_at')
    op.drop_column('messages', 'edited_at')
