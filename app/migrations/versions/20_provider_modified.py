"""22_provider_modified

Revision ID: 3ab1dd2a5789
Revises: 03a8e7383225
Create Date: 2024-06-07 11:46:19.172117

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3ab1dd2a5789'
down_revision: Union[str, None] = '03a8e7383225'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('provider', sa.Column('api_endpoint', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('provider', 'api_endpoint')
    # ### end Alembic commands ###
