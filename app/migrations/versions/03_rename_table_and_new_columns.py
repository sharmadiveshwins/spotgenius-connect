"""03_rename_table_and_new_columns

Revision ID: 1b0437e42c5d
Revises: 1fee494fd979
Create Date: 2024-04-02 00:07:49.926168

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b0437e42c5d'
down_revision: Union[str, None] = '1fee494fd979'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("session_audit", "sessions")
    op.add_column('sessions', sa.Column('not_paid_counter', sa.Integer(), default=0))
    op.add_column('connect_parkinglot', sa.Column('retry_mechanism', sa.Integer(), default=0))
    op.execute("ALTER TABLE session_log RENAME fk_session_audit TO fk_sessions")


def downgrade() -> None:
    op.rename_table("sessions", "session_audit")
    op.drop_column('sessions', 'not_paid_counter')
    op.drop_column('connect_parkinglot', 'retry_mechanism')
    op.execute("ALTER TABLE session_audit RENAME fk_sessions TO fk_session_audit")
    