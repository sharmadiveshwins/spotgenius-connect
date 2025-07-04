"""25_alter_task_and_push_payment

Revision ID: 7486d664aa2a
Revises: 9b3085c42e3d
Create Date: 2024-07-03 16:42:23.868669

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7486d664aa2a'
down_revision: Union[str, None] = '9b3085c42e3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('push_payment', sa.Column('spot_id', sa.String(), nullable=True))
    op.alter_column('push_payment', 'plate_number',
                    existing_type=sa.VARCHAR(),
                    nullable=True)
    op.alter_column('task', 'parking_spot_id',
                    existing_type=sa.INTEGER(),
                    type_=sa.String(),
                    existing_nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('task', 'parking_spot_id',
                    existing_type=sa.String(),
                    type_=sa.INTEGER(),
                    existing_nullable=True)
    op.alter_column('push_payment', 'plate_number',
                    existing_type=sa.VARCHAR(),
                    nullable=False)
    op.drop_column('push_payment', 'spot_id')
    # ### end Alembic commands ###
