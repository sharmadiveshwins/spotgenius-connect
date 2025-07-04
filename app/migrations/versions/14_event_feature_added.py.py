"""14_event_feature_added

Revision ID: 234c935d91c6
Revises: f6d94b1578ed
Create Date: 2024-06-05 14:20:09.773492

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '234c935d91c6'
down_revision: Union[str, None] = 'f6d94b1578ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('event_feature',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('fk_event_types', sa.Integer(), nullable=False),
    sa.Column('fk_feature', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['fk_event_types'], ['event_types.id'], ),
    sa.ForeignKeyConstraint(['fk_feature'], ['feature.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('event_feature')
    # ### end Alembic commands ###
