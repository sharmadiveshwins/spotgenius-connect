"""42_remove_violation_event

Revision ID: 743705b2e360
Revises: 09b0357069cf
Create Date: 2024-11-27 13:01:50.517074

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '743705b2e360'
down_revision: Union[str, None] = '09b0357069cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("sessions", 'violation_event')


def downgrade() -> None:
    op.add_column('sessions', sa.Column('violation_event', sa.JSON()))

