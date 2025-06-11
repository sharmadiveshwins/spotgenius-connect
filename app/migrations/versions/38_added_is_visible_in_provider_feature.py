"""38_added_is_visible_in_provider_feature

Revision ID: 34cdd0737de5
Revises: 15f22f33de6c
Create Date: 2024-11-12 18:37:12.541562

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34cdd0737de5'
down_revision: Union[str, None] = '15f22f33de6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('provider_types', sa.Column('is_visible', sa.Boolean(), server_default=sa.true()))


def downgrade() -> None:
    op.drop_column('provider_types', 'is_visible')
