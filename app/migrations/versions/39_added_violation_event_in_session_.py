"""39_added_violation_event_in_session_table

Revision ID: a449658657ce
Revises: 34cdd0737de5
Create Date: 2024-11-15 13:24:53.403488

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a449658657ce'
down_revision: Union[str, None] = '34cdd0737de5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.add_column('sessions', sa.Column('violation_event', sa.JSON()))


def downgrade() -> None:
    op.drop_column("sessions", 'violation_event')

