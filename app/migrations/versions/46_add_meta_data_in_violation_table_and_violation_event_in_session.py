"""46_add_meta_data_in_violation_table

Revision ID: 550f71c62c22
Revises: ec527598fd5d
Create Date: 2024-12-24 10:47:56.338900

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import ARRAY, JSON
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '550f71c62c22'
down_revision: Union[str, None] = 'ec527598fd5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('violation', sa.Column('meta_data', sa.JSON(), nullable=True))
    op.add_column('violation', sa.Column('violation_event', sa.JSON, nullable=True))


    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('violation', 'meta_data')
    op.drop_column('violation', 'violation_events')

    # ### end Alembic commands ###
