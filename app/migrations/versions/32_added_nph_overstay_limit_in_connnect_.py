"""32_added_nph_overstay_limit_in_connnect_parking_lot

Revision ID: c68e1590c3bf
Revises: 888182f00c3f
Create Date: 2024-09-12 18:43:28.810502

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c68e1590c3bf'
down_revision: Union[str, None] = '888182f00c3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('connect_parkinglot', sa.Column('nph_overstay_limit_in_minutes', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('connect_parkinglot', 'nph_overstay_limit_in_minutes')
    # ### end Alembic commands ###
