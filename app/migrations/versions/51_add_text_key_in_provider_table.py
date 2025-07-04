"""51_add_text_key_in_provider_table

Revision ID: 4ee636f7ba9d
Revises: 50cb10f605e7
Create Date: 2025-01-29 02:04:28.603447

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ee636f7ba9d'
down_revision: Union[str, None] = '50cb10f605e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('provider', sa.Column('text_key', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('provider', 'text_key')# ### end Alembic commands ###
